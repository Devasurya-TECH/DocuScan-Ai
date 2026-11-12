from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('documents', '0004_document_representation')]

    operations = [
        migrations.CreateModel(
            name='DocumentExport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('export_format', models.CharField(choices=[('pdf', 'PDF'), ('docx', 'DOCX')], max_length=10)),
                ('reconstruction_mode', models.CharField(choices=[('original', 'Original layout'), ('clean', 'Clean layout')], max_length=20)),
                ('file', models.FileField(upload_to='exports/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='exports', to='documents.document')),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
