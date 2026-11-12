from django.db import models

# Create your models here.
class Document(models.Model):
    id = models.BigAutoField(primary_key=True)
    STATUS_CHOICES=[
        ('uploaded', 'Uploaded'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    uploaded_file=models.ImageField(
        upload_to='documents/'
    )
    processed_file=models.ImageField(
        upload_to='processed_documents/',
        blank=True,
        null=True
    )

    status=models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='uploaded'
    )
    extracted_text=models.TextField(
        blank=True,
        null=True
    )
    ocr_results=models.JSONField(
        default=list,
        blank=True
    )
    average_confidence=models.FloatField(
        blank=True,
        null=True
    )
    ocr_engine=models.CharField(
        max_length=40,
        blank=True,
        default=''
    )
    processing_strategy=models.CharField(
        max_length=80,
        blank=True,
        default=''
    )
    quality_metrics=models.JSONField(
        default=dict,
        blank=True
    )
    boundary_detected=models.BooleanField(
        default=False
    )
    processing_duration=models.FloatField(
        blank=True,
        null=True
    )
    failure_reason=models.TextField(
        blank=True,
        default=''
    )
    corrected_text=models.TextField(
        blank=True,
        null=True
    )
    document_type=models.CharField(
        max_length=60,
        blank=True,
        default=''
    )
    document_data=models.JSONField(
        default=dict,
        blank=True
    )
    created_at=models.DateTimeField(
        auto_now_add=True
    )
    updated_at=models.DateTimeField(
        auto_now=True
    )
    def __str__(self):
        return f'Document {self.id}'


class DocumentExport(models.Model):
    FORMAT_CHOICES = [('pdf', 'PDF'), ('docx', 'DOCX')]
    MODE_CHOICES = [('original', 'Original layout'), ('clean', 'Clean layout')]

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='exports')
    export_format = models.CharField(max_length=10, choices=FORMAT_CHOICES)
    reconstruction_mode = models.CharField(max_length=20, choices=MODE_CHOICES)
    file = models.FileField(upload_to='exports/')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.document_id} {self.reconstruction_mode} {self.export_format}'
