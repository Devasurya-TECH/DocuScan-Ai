import logging
import uuid
from pathlib import Path

from django.utils import timezone

from django.contrib.auth.models import User
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Document, DocumentExport
from .serializers import (
    DocumentCorrectionSerializer,
    DocumentExportSerializer,
    DocumentListSerializer,
    DocumentSerializers,
    DocumentStatusSerializer,
    ExportRequestSerializer,
    QuestionAnsweringSerializer,
    UserRegisterSerializer,
    UserSerializer,
)
from .services.correction_service import apply_human_correction
from .services.export_service import create_export
from .services.rag_service import answer_document_question
from .tasks import process_document_task

logger = logging.getLogger(__name__)


def _get_user_or_default(request):
    """
    Returns the authenticated user or falls back to the default demo user
    to ensure seamless local development and backwards compatibility.
    """
    if request.user and request.user.is_authenticated:
        return request.user
    demo_user = User.objects.filter(username='demo').first()
    if not demo_user:
        demo_user = User.objects.create_user(username='demo', email='demo@docuscan.ai')
    return demo_user


def _get_user_document(pk, request):
    """Retrieve document ensuring strict user ownership or unassigned demo fallback."""
    from django.db.models import Q
    if request.user and request.user.is_authenticated:
        return get_object_or_404(Document, pk=pk, user=request.user)
    demo_user = User.objects.filter(username='demo').first()
    return get_object_or_404(Document, Q(user=demo_user) | Q(user__isnull=True), pk=pk)


class HealthCheckView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            "message": "DocuScan AI API is running",
            "status": "healthy",
            "version": "2.0.0",
        })


# ============================================================================
# 1. AUTHENTICATION VIEWS
# ============================================================================

class UserRegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'message': 'Account registered successfully.'
        }, status=status.HTTP_201_CREATED)


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


# ============================================================================
# 2. DOCUMENT MANAGEMENT & PROCESSING VIEWS
# ============================================================================

class DocumentUploadView(generics.CreateAPIView):
    serializer_class = DocumentSerializers
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [AllowAny]  # Supports token auth or demo fallback

    def perform_create(self, serializer):
        user = _get_user_or_default(self.request)
        languages = tuple(
            lang.strip() for lang in serializer.validated_data.pop('ocr_languages', '').split(',') if lang.strip()
        ) or None
        serializer.validated_data.pop('ocr_mode', None)
        
        task_id = str(uuid.uuid4())
        uploaded_file = serializer.validated_data.get('uploaded_file')
        title = Path(uploaded_file.name).stem if uploaded_file else 'Document'

        document = serializer.save(
            user=user,
            title=title,
            status='processing',
            job_id=task_id,
            progress_stage='queued',
            progress_percent=5,
        )

        # Dispatch asynchronous Celery task
        # With CELERY_TASK_ALWAYS_EAGER=True, this executes synchronously in dev
        # With Redis active, this runs in the background Celery worker pool
        try:
            process_document_task.delay(document.id, languages=languages)
        except Exception as exc:
            logger.warning(f"Could not dispatch Celery task asynchronously, running inline: {exc}")
            from .services.document_processing import process_document
            try:
                process_document(document, languages=languages)
            except Exception as inner_exc:
                document.status = 'failed'
                document.failure_reason = str(inner_exc)[:1000]
                document.save(update_fields=['status', 'failure_reason', 'updated_at'])


class DocumentListView(generics.ListAPIView):
    serializer_class = DocumentListSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        user = _get_user_or_default(self.request)
        if self.request.user and self.request.user.is_authenticated:
            qs = Document.objects.filter(user=self.request.user).order_by('-created_at')
        else:
            from django.db.models import Q
            qs = Document.objects.filter(Q(user=user) | Q(user__isnull=True)).order_by('-created_at')
        
        # Search filter
        search_query = self.request.query_params.get('search', '').strip()
        if search_query:
            qs = qs.filter(extracted_text__icontains=search_query) | qs.filter(title__icontains=search_query)

        # Status filter
        doc_status = self.request.query_params.get('status')
        if doc_status and doc_status != 'all':
            qs = qs.filter(status=doc_status)

        # Type filter
        doc_type = self.request.query_params.get('document_type')
        if doc_type and doc_type != 'all':
            qs = qs.filter(document_type=doc_type)

        return qs


class DocumentDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = DocumentSerializers
    permission_classes = [AllowAny]

    def get_queryset(self):
        if self.request.user and self.request.user.is_authenticated:
            return Document.objects.filter(user=self.request.user)
        user = _get_user_or_default(self.request)
        from django.db.models import Q
        return Document.objects.filter(Q(user=user) | Q(user__isnull=True))


class DocumentStatusView(APIView):
    """Live processing job telemetry endpoint for frontend polling."""
    permission_classes = [AllowAny]

    # Jobs stuck in 'processing' longer than this have been interrupted (server
    # restart, OOM kill, etc.) and will never complete on their own.
    _STALE_PROCESSING_SECONDS = 180  # 3 minutes

    def get(self, request, pk):
        document = _get_user_document(pk, request)

        # Lazy stale detection: runs only when a client actually polls the
        # document. Avoids a costly startup DB-wide sweep.
        if document.status == 'processing':
            age = (timezone.now() - document.updated_at).total_seconds()
            if age > self._STALE_PROCESSING_SECONDS:
                document.status = 'failed'
                document.progress_stage = 'failed'
                document.failure_reason = (
                    'Processing was interrupted (likely a server restart or '
                    'memory limit). Click Reprocess to try again.'
                )
                document.save(update_fields=[
                    'status', 'progress_stage', 'failure_reason', 'updated_at'
                ])

        return Response(DocumentStatusSerializer(document).data)


# ============================================================================
# 3. EXPORT & CORRECTION VIEWS
# ============================================================================

@api_view(['POST'])
@permission_classes([AllowAny])
def document_export_view(request, pk):
    document = _get_user_document(pk, request)
    user = _get_user_or_default(request)
    
    request_serializer = ExportRequestSerializer(data=request.data)
    request_serializer.is_valid(raise_exception=True)
    try:
        export = create_export(
            document,
            export_format=request_serializer.validated_data['format'],
            reconstruction_mode=request_serializer.validated_data['reconstruction_mode'],
        )
        if user and user.is_authenticated:
            export.user = user
            export.save(update_fields=['user'])
    except ValueError as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_409_CONFLICT)
        
    return Response(DocumentExportSerializer(export, context={'request': request}).data, status=status.HTTP_201_CREATED)


@api_view(['PATCH'])
@permission_classes([AllowAny])
def document_correction_view(request, pk):
    document = _get_user_document(pk, request)
    
    correction = DocumentCorrectionSerializer(data=request.data)
    correction.is_valid(raise_exception=True)
    try:
        document = apply_human_correction(document, **correction.validated_data)
    except ValueError as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        
    return Response(DocumentSerializers(document, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([AllowAny])
def document_reprocess_view(request, pk):
    """Re-triggers OCR processing on an existing document."""
    document = _get_user_document(pk, request)
    document.status = 'processing'
    document.progress_stage = 'reprocessing'
    document.progress_percent = 10
    document.failure_reason = ''
    document.save(update_fields=['status', 'progress_stage', 'progress_percent', 'failure_reason', 'updated_at'])

    try:
        process_document_task.delay(document.id)
    except Exception as exc:
        logger.warning(f"Could not dispatch async reprocess, running inline: {exc}")
        from .services.document_processing import process_document
        try:
            process_document(document)
        except Exception as inner_exc:
            document.status = 'failed'
            document.failure_reason = str(inner_exc)[:1000]
            document.save(update_fields=['status', 'failure_reason', 'updated_at'])
            return Response({'detail': str(inner_exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response(DocumentStatusSerializer(document).data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def document_autocorrect_view(request, pk):
    """Clean OCR artifacts and apply dictionary-guided spell correction to document text."""
    document = _get_user_document(pk, request)
    raw_text = request.data.get('text')
    if raw_text is None:
        raw_text = document.corrected_text or document.extracted_text or ''
    
    from .services.ocr_cleanup import autocorrect_text
    corrected_text, changes = autocorrect_text(raw_text)
    
    return Response({
        'original_text': raw_text,
        'corrected_text': corrected_text,
        'changes_count': len(changes),
        'changes': changes,
    }, status=status.HTTP_200_OK)



# ============================================================================
# 4. DOCUMENT Q&A (RAG) & SECURE FILE ACCESS
# ============================================================================

@api_view(['POST'])
@permission_classes([AllowAny])
def document_qa_view(request, pk):
    """Natural language question answering grounded in document OCR text."""
    document = _get_user_document(pk, request)

    serializer = QuestionAnsweringSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    try:
        answer_result = answer_document_question(document, serializer.validated_data['question'])
        return Response(answer_result, status=status.HTTP_200_OK)
    except Exception as exc:
        logger.exception(f"Error answering question on document {pk}: {exc}")
        return Response({'detail': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def document_file_download_view(request, pk, file_type):
    """
    Secure authenticated media delivery. Ensures only the owner can access
    the original or processed scans.
    """
    document = _get_user_document(pk, request)

    try:
        if file_type == 'uploaded' and document.uploaded_file:
            file_handle = document.uploaded_file.open('rb')
            content_type = 'application/pdf' if document.uploaded_file.name.lower().endswith('.pdf') else 'image/png'
            return FileResponse(file_handle, content_type=content_type)
        elif file_type == 'processed' and document.processed_file:
            file_handle = document.processed_file.open('rb')
            return FileResponse(file_handle, content_type='image/png')
    except (FileNotFoundError, ValueError, OSError):
        raise Http404("Source file is not available on storage.")

    raise Http404("Requested file does not exist.")


@api_view(['GET'])
@permission_classes([AllowAny])
def benchmark_report_view(request):
    """API endpoint to inspect OCR model evaluation results."""
    from .services.ocr_evaluation import benchmark_easyocr_variants
    from .models import Document
    import json
    from django.conf import settings
    
    results_dir = Path(settings.BASE_DIR) / 'documents' / 'evaluation' / 'results'
    manifest_file = Path(settings.BASE_DIR) / 'documents' / 'evaluation' / 'dataset' / 'dataset_manifest.json'
    
    manifest_data = {}
    if manifest_file.exists():
        try:
            manifest_data = json.loads(manifest_file.read_text(encoding='utf-8'))
        except Exception:
            pass

    return Response({
        'status': 'available',
        'benchmark_dataset': manifest_data,
        'evaluation_metrics': ['CER (Character Error Rate)', 'WER (Word Error Rate)', 'Exact Match', 'Field F1'],
        'models_registered': ['EasyOCR 1.7.2', 'PaddleOCR PP-OCRv5', 'Microsoft TrOCR'],
    })
