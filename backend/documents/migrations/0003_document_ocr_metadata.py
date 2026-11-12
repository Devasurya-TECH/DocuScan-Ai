from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('documents', '0002_document_processing_fields')]

    operations = [
        migrations.AddField(model_name='document', name='ocr_engine', field=models.CharField(blank=True, default='', max_length=40)),
        migrations.AddField(model_name='document', name='processing_strategy', field=models.CharField(blank=True, default='', max_length=80)),
        migrations.AddField(model_name='document', name='quality_metrics', field=models.JSONField(blank=True, default=dict)),
        migrations.AddField(model_name='document', name='boundary_detected', field=models.BooleanField(default=False)),
        migrations.AddField(model_name='document', name='processing_duration', field=models.FloatField(blank=True, null=True)),
        migrations.AddField(model_name='document', name='failure_reason', field=models.TextField(blank=True, default='')),
        migrations.AddField(model_name='document', name='corrected_text', field=models.TextField(blank=True, null=True)),
        migrations.AddField(model_name='document', name='updated_at', field=models.DateTimeField(auto_now=True)),
    ]
