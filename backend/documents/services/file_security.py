import os
import re
import uuid
from pathlib import Path
from rest_framework import serializers

ALLOWED_SIGNATURES = {
    'jpeg': (b'\xff\xd8\xff',),
    'png': (b'\x89PNG\r\n\x1a\n',),
    'pdf': (b'%PDF-',),
    'webp': (b'RIFF',),
    'docx': (b'PK\x03\x04',),
    'doc': (b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1',),
}

MAX_FILE_SIZE = 15 * 1024 * 1024  # 15 MB


def validate_file_security(uploaded_file):
    """
    Validates file size, extension, and binary header magic bytes to prevent
    file spoofing, malicious executables, and path traversal vulnerabilities.
    """
    if uploaded_file.size > MAX_FILE_SIZE:
        raise serializers.ValidationError('File exceeds maximum allowable size of 15 MB.')

    filename = uploaded_file.name or 'upload'
    # Block path traversal in filename
    if '..' in filename or '/' in filename or '\\' in filename:
        raise serializers.ValidationError('Invalid or unsafe filename.')

    ext = Path(filename).suffix.lower()
    if ext not in ('.jpg', '.jpeg', '.png', '.webp', '.pdf', '.docx', '.doc'):
        raise serializers.ValidationError('Unsupported file type. Use JPG, JPEG, PNG, WEBP, PDF, or DOCX.')

    # Read binary header
    uploaded_file.seek(0)
    header = uploaded_file.read(32)
    uploaded_file.seek(0)

    is_valid = False
    detected_type = None

    if header.startswith(ALLOWED_SIGNATURES['pdf'][0]):
        is_valid = True
        detected_type = 'pdf'
    elif header.startswith(ALLOWED_SIGNATURES['png'][0]):
        is_valid = True
        detected_type = 'png'
    elif header.startswith(ALLOWED_SIGNATURES['jpeg'][0]):
        is_valid = True
        detected_type = 'jpeg'
    elif header.startswith(ALLOWED_SIGNATURES['webp'][0]) and header[8:12] == b'WEBP':
        is_valid = True
        detected_type = 'webp'
    elif ext == '.docx' and header.startswith(ALLOWED_SIGNATURES['docx'][0]):
        is_valid = True
        detected_type = 'docx'
    elif ext == '.doc' and header.startswith(ALLOWED_SIGNATURES['doc'][0]):
        is_valid = True
        detected_type = 'doc'

    if not is_valid:
        raise serializers.ValidationError('Invalid file signature. The file contents do not match its supported document type.')

    return detected_type


def sanitize_filename(original_name, prefix='doc'):
    """
    Generate a collision-free, path-safe storage filename.
    """
    base_name = Path(original_name).name
    stem = re.sub(r'[^a-zA-Z0-9_\-]', '_', Path(base_name).stem)[:40]
    ext = Path(base_name).suffix.lower()
    if ext not in ('.jpg', '.jpeg', '.png', '.webp', '.pdf', '.docx', '.doc'):
        ext = '.png'
    random_id = uuid.uuid4().hex[:8]
    return f'{prefix}_{stem}_{random_id}{ext}'
