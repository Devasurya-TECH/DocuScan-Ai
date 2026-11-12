from rest_framework.views import APIView
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.parsers import MultiPartParser,FormParser

from .models import Document
from .serializers import DocumentExportSerializer, DocumentListSerializer, DocumentSerializers, ExportRequestSerializer
from .services.document_processing import process_document
from .services.export_service import create_export

class HealthCheckView(APIView):
    def get(self,request):
        return Response(
            {
            "message": "DocuScan AI API is running",
            "status": "healthy"
            }
        )
class DocumentUploadView(generics.CreateAPIView):
    serializer_class=DocumentSerializers
    parser_classes=[MultiPartParser, FormParser]

    def perform_create(self, serializer):
        document = serializer.save(status='processing')
        try:
            process_document(document)
        except Exception as exc:
            document.status = 'failed'
            document.failure_reason = str(exc)[:1000]
            document.save(update_fields=['status', 'failure_reason', 'updated_at'])
            raise


class DocumentListView(generics.ListAPIView):
    serializer_class = DocumentListSerializer
    queryset = Document.objects.order_by('-created_at')


class DocumentDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = DocumentSerializers
    queryset = Document.objects.all()


@api_view(['POST'])
def document_export_view(request, pk):
    document = generics.get_object_or_404(Document, pk=pk)
    request_serializer = ExportRequestSerializer(data=request.data)
    request_serializer.is_valid(raise_exception=True)
    try:
        export = create_export(
            document,
            export_format=request_serializer.validated_data['format'],
            reconstruction_mode=request_serializer.validated_data['reconstruction_mode'],
        )
    except ValueError as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_409_CONFLICT)
    return Response(DocumentExportSerializer(export, context={'request': request}).data, status=status.HTTP_201_CREATED)
