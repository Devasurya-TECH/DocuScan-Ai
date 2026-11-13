from rest_framework import serializers
from PIL import Image,UnidentifiedImageError
from .models import Document, DocumentExport

DOCUMENT_DETAIL_FIELDS = (
    'id',
    'uploaded_file',
    'processed_file',
    'status',
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
    'created_at',
    'updated_at',
    'ocr_languages',
)


class DocumentSerializers(serializers.ModelSerializer):
    """Full document representation for an upload response and detail view."""
    ocr_languages = serializers.CharField(write_only=True, required=False, allow_blank=True)
    class Meta:
        model = Document
        fields = DOCUMENT_DETAIL_FIELDS
        read_only_fields = [
            'id',
            'status',
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
        ]
    def validate_uploaded_file(self,value):
        if value.size > 10*1024 * 1024:
            raise serializers.ValidationError(
                'Maximum file size is 10mb'
            )
        try:
            image=Image.open(value)
            image.verify()

            if image.format not in ['JPEG','PNG']:
                raise serializers.ValidationError(
                    'Only JPG and PNG are Supported'
                )
        except(UnidentifiedImageError,OSError):
            raise serializers.ValidationError(
                'Invalid Image File.'
            )
        value.seek(0)
        return value

    def validate_ocr_languages(self, value):
        allowed = {'en', 'hi', 'ta', 'bn', 'te', 'kn', 'ml', 'gu', 'pa', 'mr', 'ur', 'ar'}
        requested = [item.strip() for item in value.split(',') if item.strip()]
        if any(item not in allowed for item in requested):
            raise serializers.ValidationError('Unsupported OCR language selection.')
        return ','.join(requested)


class DocumentListSerializer(serializers.ModelSerializer):
    """Compact response for document history; OCR boxes stay on detail only."""
    class Meta:
        model = Document
        fields = (
            'id', 'uploaded_file', 'processed_file', 'status', 'extracted_text',
            'average_confidence', 'ocr_engine', 'processing_strategy',
            'boundary_detected', 'processing_duration', 'created_at', 'updated_at',
            'document_type',
        )
        read_only_fields = fields


class DocumentExportSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentExport
        fields = ('id', 'export_format', 'reconstruction_mode', 'file', 'created_at')
        read_only_fields = fields


class ExportRequestSerializer(serializers.Serializer):
    format = serializers.ChoiceField(choices=('pdf', 'docx'))
    reconstruction_mode = serializers.ChoiceField(choices=('original', 'clean'))


class DocumentCorrectionSerializer(serializers.Serializer):
    corrected_text = serializers.CharField(required=False, allow_blank=True, max_length=100000)
    verified_fields = serializers.DictField(required=False)
