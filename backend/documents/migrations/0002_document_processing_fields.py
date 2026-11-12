# Generated manually to add persisted results from the document-processing pipeline.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='processed_file',
            field=models.ImageField(blank=True, null=True, upload_to='processed_documents/'),
        ),
        migrations.AddField(
            model_name='document',
            name='ocr_results',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='document',
            name='average_confidence',
            field=models.FloatField(blank=True, null=True),
        ),
    ]
