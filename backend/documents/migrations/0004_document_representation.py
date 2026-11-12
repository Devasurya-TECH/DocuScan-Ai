from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('documents', '0003_document_ocr_metadata')]

    operations = [
        migrations.AddField(model_name='document', name='document_type', field=models.CharField(blank=True, default='', max_length=60)),
        migrations.AddField(model_name='document', name='document_data', field=models.JSONField(blank=True, default=dict)),
    ]
