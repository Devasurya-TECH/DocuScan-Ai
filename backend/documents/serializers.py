from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Document, DocumentExport
from .services.file_security import validate_file_security, sanitize_filename


class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'password_confirm')

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password': 'Passwords do not match.'})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password']
        )
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'date_joined')
        read_only_fields = fields


DOCUMENT_DETAIL_FIELDS = (
    'id',
    'title',
    'uploaded_file',
    'processed_file',
    'status',
    'job_id',
    'progress_stage',
    'progress_percent',
    'extracted_text',
    'corrected_text',
    'ocr_results',
    'average_confidence',
    'ocr_engine',
    'processing_strategy',
    'quality_metrics',
    'boundary_detected',
    'processing_duration',
    'failure_reason',
    'document_type',
    'document_data',
    'is_multipage',
    'page_count',
    'pages_data',
    'tags',
    'qa_history',
    'created_at',
    'updated_at',
    'ocr_languages',
    'ocr_mode',
)


class DocumentSerializers(serializers.ModelSerializer):
    """Full document representation for upload response and detail view."""
    ocr_languages = serializers.CharField(write_only=True, required=False, allow_blank=True)
    ocr_mode = serializers.CharField(write_only=True, required=False, allow_blank=True)
    filename = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = DOCUMENT_DETAIL_FIELDS + ('filename',)
        read_only_fields = [
            'id',
            'status',
            'job_id',
            'progress_stage',
            'progress_percent',
            'extracted_text',
            'created_at',
            'updated_at',
            'processed_file',
            'ocr_results',
            'average_confidence',
            'ocr_engine',
            'processing_strategy',
            'quality_metrics',
            'boundary_detected',
            'processing_duration',
            'failure_reason',
            'document_type',
            'document_data',
            'is_multipage',
            'page_count',
            'pages_data',
            'qa_history',
        ]

    def get_filename(self, obj):
        if obj.uploaded_file:
            from pathlib import Path
            return Path(obj.uploaded_file.name).name
        return obj.title or f'Document_{obj.id}'

    def validate_uploaded_file(self, value):
        validate_file_security(value)
        return value

    def validate_ocr_languages(self, value):
        allowed = {'en', 'hi', 'ta', 'bn', 'te', 'kn', 'ml', 'gu', 'pa', 'mr', 'ur', 'ar'}
        requested = [item.strip() for item in value.split(',') if item.strip()]
        if any(item not in allowed for item in requested):
            raise serializers.ValidationError('Unsupported OCR language selection.')
        return ','.join(requested)


class DocumentListSerializer(serializers.ModelSerializer):
    """Compact response for document library and history."""
    filename = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = (
            'id', 'title', 'filename', 'uploaded_file', 'processed_file', 'status',
            'progress_stage', 'progress_percent', 'extracted_text',
            'average_confidence', 'ocr_engine', 'processing_strategy',
            'boundary_detected', 'processing_duration', 'created_at', 'updated_at',
            'document_type', 'is_multipage', 'page_count', 'tags',
        )
        read_only_fields = fields

    def get_filename(self, obj):
        if obj.uploaded_file:
            from pathlib import Path
            return Path(obj.uploaded_file.name).name
        return obj.title or f'Document_{obj.id}'


class DocumentStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ('id', 'status', 'job_id', 'progress_stage', 'progress_percent', 'failure_reason', 'updated_at')
        read_only_fields = fields


class DocumentExportSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentExport
        fields = ('id', 'export_format', 'reconstruction_mode', 'file', 'created_at')
        read_only_fields = fields


class ExportRequestSerializer(serializers.Serializer):
    format = serializers.ChoiceField(choices=('pdf', 'docx', 'txt'))
    reconstruction_mode = serializers.ChoiceField(choices=('original', 'clean'))


class DocumentCorrectionSerializer(serializers.Serializer):
    corrected_text = serializers.CharField(required=False, allow_blank=True, max_length=100000)
    verified_fields = serializers.DictField(required=False)


class QuestionAnsweringSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=500, required=True)
