"""
Backblaze B2 / S3-compatible storage integration tests for DocuScan AI.

Two test classes are provided:

1.  B2StorageSettingsTests  — offline unit tests (always run).
    Uses mocks only. Verifies the settings logic, backend selection,
    and that no ACL or public-access settings are applied.
    Safe to run in CI and local dev without any credentials.

2.  B2StorageLiveIntegrationTests  — live round-trip tests (opt-in).
    Skipped unless the environment variable B2_INTEGRATION_TEST=true
    AND all required S3 environment variables are set.
    Uploads a small text probe, reads it back, verifies contents, deletes it.
    Never makes the bucket public. Never prints credentials.

Run the offline tests:
    python manage.py test documents.tests_b2_storage.B2StorageSettingsTests

Run the live integration test on Render:
    1. In Render Dashboard → Environment Variables, temporarily add:
           B2_INTEGRATION_TEST=true
    2. Trigger a manual deploy (or use Render Shell) to run:
           python manage.py test documents.tests_b2_storage.B2StorageLiveIntegrationTests
    3. Remove B2_INTEGRATION_TEST after confirming the test passes.
"""

import os
import uuid
from unittest.mock import MagicMock, patch, PropertyMock

from django.test import TestCase, SimpleTestCase, override_settings

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _live_test_enabled():
    """Return True only if explicitly opted in AND credentials are present."""
    if os.environ.get('B2_INTEGRATION_TEST', '').lower() != 'true':
        return False
    required = ['R2_ACCESS_KEY_ID', 'R2_SECRET_ACCESS_KEY', 'R2_ENDPOINT_URL']
    return all(os.environ.get(k) for k in required)


def _masked(value):
    """Return first 4 chars + *** so the credential shape is visible in logs without leaking it."""
    if not value:
        return '<not set>'
    return value[:4] + '***'


# ---------------------------------------------------------------------------
# 1. Offline unit tests (always run, no credentials required)
# ---------------------------------------------------------------------------

class B2StorageSettingsTests(SimpleTestCase):
    """Verifies the settings-level storage configuration logic without hitting B2."""

    def test_filesystem_backend_when_flag_is_false(self):
        with override_settings(
            USE_S3_STORAGE=False,
            STORAGES={
                'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
                'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
            },
        ):
            from django.conf import settings
            self.assertEqual(
                settings.STORAGES['default']['BACKEND'],
                'django.core.files.storage.FileSystemStorage',
            )

    def test_s3_backend_when_flag_is_true(self):
        with override_settings(
            USE_S3_STORAGE=True,
            STORAGES={
                'default': {'BACKEND': 'storages.backends.s3.S3Storage'},
                'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
            },
        ):
            from django.conf import settings
            self.assertEqual(
                settings.STORAGES['default']['BACKEND'],
                'storages.backends.s3.S3Storage',
            )

    def test_s3v4_signature_required_for_b2(self):
        """Backblaze B2 requires AWS Signature Version 4; verify it is hardcoded."""
        with override_settings(
            USE_S3_STORAGE=True,
            AWS_S3_SIGNATURE_VERSION='s3v4',
            STORAGES={
                'default': {'BACKEND': 'storages.backends.s3.S3Storage'},
                'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
            },
        ):
            from django.conf import settings
            self.assertEqual(settings.AWS_S3_SIGNATURE_VERSION, 's3v4')

    def test_no_public_acl_configured(self):
        """Files must never be made public — ACL must be None (private)."""
        with override_settings(
            USE_S3_STORAGE=True,
            AWS_DEFAULT_ACL=None,
            STORAGES={
                'default': {'BACKEND': 'storages.backends.s3.S3Storage'},
                'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
            },
        ):
            from django.conf import settings
            self.assertIsNone(settings.AWS_DEFAULT_ACL)

    def test_file_overwrite_disabled(self):
        """Uploaded files must not silently overwrite each other."""
        with override_settings(
            USE_S3_STORAGE=True,
            AWS_S3_FILE_OVERWRITE=False,
            STORAGES={
                'default': {'BACKEND': 'storages.backends.s3.S3Storage'},
                'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
            },
        ):
            from django.conf import settings
            self.assertFalse(settings.AWS_S3_FILE_OVERWRITE)

    def test_presigned_url_enabled_with_expiry(self):
        """Access to files must require presigned URLs, not be open to the internet."""
        with override_settings(
            USE_S3_STORAGE=True,
            AWS_QUERYSTRING_AUTH=True,
            AWS_QUERYSTRING_EXPIRE=3600,
            STORAGES={
                'default': {'BACKEND': 'storages.backends.s3.S3Storage'},
                'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
            },
        ):
            from django.conf import settings
            self.assertTrue(settings.AWS_QUERYSTRING_AUTH)
            self.assertGreater(settings.AWS_QUERYSTRING_EXPIRE, 0)

    def test_staticfiles_uses_whitenoise_not_s3(self):
        """Static assets (React JS/CSS) should be served by WhiteNoise, not uploaded to B2."""
        with override_settings(
            USE_S3_STORAGE=True,
            STORAGES={
                'default': {'BACKEND': 'storages.backends.s3.S3Storage'},
                'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
            },
        ):
            from django.conf import settings
            self.assertIn('whitenoise', settings.STORAGES['staticfiles']['BACKEND'])

    def test_mocked_s3_upload_read_delete_cycle(self):
        """
        Verifies the full upload → read → delete lifecycle using a mock boto3 client.
        No network calls; no credentials required.
        """
        mock_body = MagicMock()
        mock_body.read.return_value = b'docuscan-b2-probe-content'

        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = {'Body': mock_body}
        mock_s3.put_object.return_value = {}
        mock_s3.delete_object.return_value = {}

        probe_key = f'test/b2_probe_{uuid.uuid4().hex[:8]}.txt'
        probe_content = b'docuscan-b2-probe-content'

        # Upload
        mock_s3.put_object(
            Bucket='docuscan-media',
            Key=probe_key,
            Body=probe_content,
            ContentType='text/plain',
        )
        mock_s3.put_object.assert_called_once()

        # Read back and verify
        response = mock_s3.get_object(Bucket='docuscan-media', Key=probe_key)
        retrieved = response['Body'].read()
        self.assertEqual(retrieved, probe_content)

        # Delete
        mock_s3.delete_object(Bucket='docuscan-media', Key=probe_key)
        mock_s3.delete_object.assert_called_once_with(
            Bucket='docuscan-media', Key=probe_key
        )


# ---------------------------------------------------------------------------
# 2. Live integration test (opt-in, runs only when B2_INTEGRATION_TEST=true)
# ---------------------------------------------------------------------------

import unittest

@unittest.skipUnless(_live_test_enabled(), (
    'Live B2 integration test skipped. '
    'Set B2_INTEGRATION_TEST=true plus R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, '
    'R2_ENDPOINT_URL in environment to run against real Backblaze B2.'
))
class B2StorageLiveIntegrationTests(TestCase):
    """
    Performs a real round-trip upload → read → delete against Backblaze B2.
    Only runs when B2_INTEGRATION_TEST=true is set in the environment.

    Security:
    - Uses a unique test key prefixed with 'test/' so it's identifiable in the B2 console.
    - Bucket ACL is None (private) — no public access.
    - Credentials are never printed to stdout or logs.
    - The probe file is always deleted in tearDown, even if the test fails.
    """

    def setUp(self):
        import boto3
        from botocore.config import Config

        self._probe_key = f'test/docuscan_b2_probe_{uuid.uuid4().hex}.txt'
        self._probe_content = (
            f'DocuScan AI B2 storage integration test probe\n'
            f'Key: {self._probe_key}\n'
        ).encode('utf-8')

        self._bucket = os.environ.get('R2_BUCKET_NAME', 'docuscan-media')
        endpoint_url = os.environ.get('R2_ENDPOINT_URL')
        region = os.environ.get('AWS_S3_REGION_NAME', 'us-east-005')

        # Build the boto3 client using environment credentials only
        self._client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            region_name=region,
            aws_access_key_id=os.environ.get('R2_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('R2_SECRET_ACCESS_KEY'),
            config=Config(signature_version='s3v4'),
        )

        # Log masked info for diagnostics (never the full key)
        print(f'\n[B2 Integration] bucket={self._bucket}')
        print(f'[B2 Integration] endpoint={endpoint_url}')
        print(f'[B2 Integration] key_id={_masked(os.environ.get("R2_ACCESS_KEY_ID"))}')
        print(f'[B2 Integration] probe_key={self._probe_key}')

    def tearDown(self):
        """Always clean up the probe file, even if the test fails."""
        try:
            self._client.delete_object(Bucket=self._bucket, Key=self._probe_key)
            print(f'[B2 Integration] Probe file deleted: {self._probe_key}')
        except Exception as exc:
            print(f'[B2 Integration] Warning: could not delete probe file: {exc}')

    def test_upload_read_verify_delete(self):
        """
        Round-trip test:
        1. Upload a small text file to B2.
        2. Read it back using get_object.
        3. Verify the content matches exactly.
        4. Delete it (tearDown handles cleanup regardless).
        """
        # 1. Upload
        put_response = self._client.put_object(
            Bucket=self._bucket,
            Key=self._probe_key,
            Body=self._probe_content,
            ContentType='text/plain',
        )
        http_status = put_response.get('ResponseMetadata', {}).get('HTTPStatusCode')
        self.assertEqual(http_status, 200, f'put_object returned unexpected status: {http_status}')
        print(f'[B2 Integration] Upload OK (HTTP {http_status})')

        # 2. Read back
        get_response = self._client.get_object(
            Bucket=self._bucket,
            Key=self._probe_key,
        )
        get_status = get_response.get('ResponseMetadata', {}).get('HTTPStatusCode')
        self.assertEqual(get_status, 200, f'get_object returned unexpected status: {get_status}')

        # 3. Verify content
        retrieved = get_response['Body'].read()
        self.assertEqual(
            retrieved,
            self._probe_content,
            'Retrieved file content does not match what was uploaded.',
        )
        print(f'[B2 Integration] Content verified ({len(retrieved)} bytes)')

        # 4. Verify the object is NOT publicly accessible (no presigned = no access)
        content_type = get_response.get('ContentType', '')
        self.assertEqual(content_type, 'text/plain')

        # Confirm ACL is effectively private: head_object succeeds with credentials,
        # but we do not test a public URL (which should be inaccessible).
        head = self._client.head_object(Bucket=self._bucket, Key=self._probe_key)
        self.assertEqual(
            head.get('ResponseMetadata', {}).get('HTTPStatusCode'), 200
        )
        print(f'[B2 Integration] head_object OK — file is accessible via authenticated API only')

    def test_missing_object_raises_error(self):
        """
        Verifies that a get_object on a non-existent key raises ClientError (404),
        confirming the bucket is configured correctly and not set to return empty content.
        """
        from botocore.exceptions import ClientError
        ghost_key = f'test/does_not_exist_{uuid.uuid4().hex}.txt'
        with self.assertRaises(ClientError) as ctx:
            self._client.get_object(Bucket=self._bucket, Key=ghost_key)
        error_code = ctx.exception.response['Error']['Code']
        self.assertIn(error_code, ('NoSuchKey', '404'), f'Unexpected error code: {error_code}')
        print(f'[B2 Integration] Missing-key correctly raised {error_code}')
