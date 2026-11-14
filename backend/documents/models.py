import uuid
from django.db import models
from django.contrib.auth.models import User


class Document(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='documents',
        null=True,
        blank=True
    )
    
    STATUS_CHOICES = [
        ('uploaded', 'Uploaded'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    title = models.CharField(max_length=255, blank=True, default='')
    uploaded_file = models.FileField(upload_to='documents/')
    processed_file = models.FileField(upload_to='processed_documents/', blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploaded')
    
    # Asynchronous job tracking
    job_id = models.CharField(max_length=64, blank=True, default='')
    progress_stage = models.CharField(max_length=64, blank=True, default='')
    progress_percent = models.IntegerField(default=0)
    
    # OCR Outputs
    extracted_text = models.TextField(blank=True, null=True)
    corrected_text = models.TextField(blank=True, null=True)
    ocr_results = models.JSONField(default=list, blank=True)
    average_confidence = models.FloatField(blank=True, null=True)
    ocr_engine = models.CharField(max_length=40, blank=True, default='')
    processing_strategy = models.CharField(max_length=80, blank=True, default='')
    quality_metrics = models.JSONField(default=dict, blank=True)
    boundary_detected = models.BooleanField(default=False)
    processing_duration = models.FloatField(blank=True, null=True)
    failure_reason = models.TextField(blank=True, default='')
    
    # Intelligence & Layout
    document_type = models.CharField(max_length=60, blank=True, default='')
    document_data = models.JSONField(default=dict, blank=True)
    
    # Multi-page PDF capability
    is_multipage = models.BooleanField(default=False)
    page_count = models.IntegerField(default=1)
    pages_data = models.JSONField(default=list, blank=True)
    
    # Organization, Search & Q&A
    tags = models.JSONField(default=list, blank=True)
    qa_history = models.JSONField(default=list, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['document_type']),
        ]

    def __str__(self):
        name = self.title or f'Document {self.id}'
        return f'{name} ({self.status})'


class DocumentExport(models.Model):
    FORMAT_CHOICES = [('pdf', 'PDF'), ('docx', 'DOCX'), ('txt', 'TXT')]
    MODE_CHOICES = [('original', 'Original layout'), ('clean', 'Clean layout')]

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='exports')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='exports', null=True, blank=True)
    export_format = models.CharField(max_length=10, choices=FORMAT_CHOICES)
    reconstruction_mode = models.CharField(max_length=20, choices=MODE_CHOICES)
    file = models.FileField(upload_to='exports/')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['document', '-created_at']),
        ]

    def __str__(self):
        return f'{self.document_id} {self.reconstruction_mode} {self.export_format}'
