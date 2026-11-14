import numpy as np
import json
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings

from .models import Document, DocumentExport
from .services.image_enhancement import assess_quality, build_ocr_variants, correct_small_skew
from .services.layout_analysis import analyse_layout, reading_order
from .services.document_understanding import understand_document
from .services.document_representation import build_document_representation, validate_representation
from .services.reconstruction_service import reconstruct_original_layout
from .services.reconstruction_service import reconstruct_clean_layout
from .services.document_processing import select_ocr_candidate
from .services.ocr.model_registry import get_engine
from .services.ocr.ocr_router import resolve_engine
from .services.ocr.result_normalizer import normalize_detection
from .services.ocr_evaluation import error_rate, evaluate_ocr
from .services.script_detection import annotate_detection_languages
from .services.capture_analysis import find_safe_document_boundary


class OcrEvaluationTests(SimpleTestCase):
    def test_error_rates_use_known_reference_text(self):
        detections = [{'text': 'hello', 'confidence': 0.9}, {'text': 'world', 'confidence': 0.8}]
        report = evaluate_ocr('Hello world', detections, 0.2)
        self.assertEqual(report['character_error_rate'], 0)
        self.assertEqual(report['word_error_rate'], 0)
        self.assertEqual(report['detection_count'], 2)

    def test_word_error_rate_detects_incorrect_word(self):
        self.assertEqual(error_rate('one two', 'one three', 'word'), 0.5)


class OCRArchitectureTests(SimpleTestCase):
    def test_normalizes_engine_output_into_the_document_schema(self):
        detection = normalize_detection(
            engine='example', model_name='example-v1', text='TOTAL 12.50', confidence=1.3,
            bounding_box=[[1, 2], [30, 2], [30, 15], [1, 15]], language='en',
        )
        self.assertEqual(detection['engine'], 'example')
        self.assertEqual(detection['confidence'], 1.0)
        self.assertEqual(detection['region_type'], 'printed_text')
        self.assertEqual(detection['bounding_box'][0], [1, 2])

    def test_unavailable_optional_engine_uses_default_fallback(self):
        engine, warnings = resolve_engine('paddleocr')
        self.assertEqual(engine.name, 'doctr')
        self.assertTrue(warnings)

    def test_registry_rejects_unknown_engine(self):
        with self.assertRaises(ValueError):
            get_engine('not-an-engine')

    def test_detects_devanagari_script_from_returned_text(self):
        detections = [{'text': 'नमस्ते भारत', 'language': 'en'}]
        metadata = annotate_detection_languages(detections)
        self.assertEqual(metadata['primary_script'], 'devanagari')
        self.assertEqual(detections[0]['language'], 'hi')


class ImageEnhancementTests(SimpleTestCase):
    def setUp(self):
        self.image = np.full((120, 240, 3), 180, dtype=np.uint8)
        self.image[40:80, 50:190] = 30

    def test_variants_are_independently_generated(self):
        variants = build_ocr_variants(self.image, ('color', 'clahe', 'otsu_threshold'))
        self.assertEqual(set(variants), {'color', 'clahe', 'otsu_threshold'})
        self.assertEqual(variants['color'].shape[2], self.image.shape[2])
        self.assertGreaterEqual(max(variants['color'].shape[:2]), 1200)
        self.assertEqual(len(variants['clahe'].shape), 2)

    def test_quality_metrics_and_small_skew_are_safe(self):
        metrics = assess_quality(self.image)
        corrected, angle = correct_small_skew(self.image)
        self.assertIn('blur_variance', metrics)
        self.assertEqual(corrected.shape, self.image.shape)
        self.assertLessEqual(abs(angle), 15)

    def test_accuracy_variants_include_deskewed_and_colour_preserving_options(self):
        variants = build_ocr_variants(self.image, ('color', 'enhanced_color', 'deskewed_clahe'))
        self.assertEqual(set(variants), {'color', 'enhanced_color', 'deskewed_clahe'})
        self.assertGreaterEqual(max(variants['color'].shape[:2]), 1200)

    def test_full_frame_boundary_is_not_used_for_perspective_warp(self):
        image = np.full((200, 300, 3), 255, dtype=np.uint8)
        # A border that touches the image edge resembles an already-cropped scan.
        image[0:2, :] = 0
        image[-2:, :] = 0
        image[:, 0:2] = 0
        image[:, -2:] = 0
        corners, metadata = find_safe_document_boundary(image)
        self.assertIsNone(corners)
        self.assertIn(metadata['mode'], {'full_frame_document', 'full_frame_or_no_boundary'})


class CandidateSelectionTests(SimpleTestCase):
    def test_uses_recovery_only_after_a_weak_first_pass(self):
        image = np.zeros((40, 80, 3), dtype=np.uint8)
        weak = [
            {'text': 'T0TAL', 'confidence': 0.32, 'bounding_box': []},
        ]
        recovered = [
            {'text': 'TOTAL AMOUNT 114.63', 'confidence': 0.92, 'bounding_box': []},
        ]
        with patch(
            'documents.services.document_processing.build_ocr_variants',
            side_effect=[
                {'color': image},
                {'enhanced_color': image, 'deskewed_clahe': image},
            ],
        ), patch(
            'documents.services.document_processing.run_ocr',
            side_effect=[(weak, 0.1), (recovered, 0.1), (weak, 0.1)],
        ):
            selected, candidates = select_ocr_candidate(image)
        self.assertEqual(selected['strategy'], 'enhanced_color')
        self.assertEqual([candidate['strategy'] for candidate in candidates], ['color', 'enhanced_color', 'deskewed_clahe'])


class LayoutAnalysisTests(SimpleTestCase):
    @staticmethod
    def detection(text, x, y, width, height=16, confidence=0.9):
        return {
            'text': text,
            'confidence': confidence,
            'bounding_box': [[x, y], [x + width, y], [x + width, y + height], [x, y + height]],
        }

    def test_orders_words_into_lines_and_preserves_coordinates(self):
        results = [
            self.detection('world', 80, 20, 40),
            self.detection('Hello', 20, 20, 45),
            self.detection('Next', 20, 60, 35),
        ]
        layout = analyse_layout(results, 200, 100)
        self.assertEqual([line['text'] for line in layout['lines']], ['Hello world', 'Next'])
        self.assertEqual(layout['elements'][0]['bounding_box'], results[0]['bounding_box'])
        self.assertEqual(layout['reading_order'], ['line_0', 'line_1'])

    def test_detects_consecutive_description_and_price_rows(self):
        results = [
            self.detection('Lumber', 20, 20, 55), self.detection('$4.99', 180, 20, 45),
            self.detection('Screws', 20, 48, 55), self.detection('$23.38', 170, 48, 55),
        ]
        layout = analyse_layout(results, 250, 100)
        self.assertEqual(len(layout['tables']), 1)
        self.assertEqual(layout['tables'][0]['rows'][0]['cells'][0]['text'], 'Lumber')
        self.assertEqual(layout['tables'][0]['rows'][1]['cells'][1]['text'], '$23.38')

    def test_reads_two_columns_down_before_moving_right(self):
        lines = [
            {'id': 'left_1', 'position': {'x': 15, 'y': 10, 'width': 50, 'height': 16}},
            {'id': 'right_1', 'position': {'x': 150, 'y': 12, 'width': 55, 'height': 16}},
            {'id': 'left_2', 'position': {'x': 15, 'y': 40, 'width': 50, 'height': 16}},
            {'id': 'right_2', 'position': {'x': 150, 'y': 42, 'width': 55, 'height': 16}},
        ]
        columns = [
            {'position': {'x': 0, 'y': 0, 'width': 125, 'height': None}},
            {'position': {'x': 125, 'y': 0, 'width': 125, 'height': None}},
        ]
        self.assertEqual(reading_order(lines, columns), ['left_1', 'left_2', 'right_1', 'right_2'])


class DocumentUnderstandingTests(LayoutAnalysisTests):
    def test_extracts_supported_receipt_fields_and_never_invents_missing_values(self):
        results = [
            self.detection('ACE HARDWARE', 20, 10, 120, 24, 0.98),
            self.detection('RECEIPT', 20, 42, 70),
            self.detection('Date: 24 MAY 2024', 20, 66, 140, 0.91),
            self.detection('SUBTOTAL $105.89', 20, 110, 145, 0.9),
            self.detection('TAX $8.74', 20, 135, 90, 0.88),
            self.detection('TOTAL $114.63', 20, 160, 110, 0.96),
        ]
        understood = understand_document(analyse_layout(results, 250, 210))
        self.assertEqual(understood['document_type']['type'], 'receipt')
        self.assertEqual(understood['fields']['vendor']['value'], 'ACE HARDWARE')
        self.assertEqual(understood['fields']['total']['value'], 114.63)
        self.assertEqual(understood['fields']['currency']['value'], '$')
        self.assertIsNone(understood['fields']['invoice_number']['value'])

    def test_keeps_unknown_currency_and_incomplete_date_under_review(self):
        results = [
            self.detection('RECEIPT', 20, 10, 70),
            self.detection('Date: MAY 2024', 20, 35, 120),
            self.detection('TOTAL: S114.63', 20, 60, 120, confidence=0.7),
        ]
        understood = understand_document(analyse_layout(results, 200, 100))
        self.assertEqual(understood['fields']['total']['value'], 114.63)
        self.assertIsNone(understood['fields']['currency']['value'])
        self.assertIsNone(understood['fields']['date']['value'])


class DocumentRepresentationTests(LayoutAnalysisTests):
    def test_creates_valid_editable_representation_from_ocr_coordinates(self):
        results = [
            self.detection('ACME STORE', 20, 10, 110, 24, 0.98),
            self.detection('RECEIPT', 20, 42, 70),
            self.detection('TOTAL $12.50', 20, 80, 110, 0.95),
        ]
        representation = build_document_representation(results, 200, 120)
        self.assertEqual(representation['version'], 1)
        self.assertEqual(representation['document_type']['type'], 'receipt')
        self.assertEqual(representation['page'], {'width': 200, 'height': 120})
        self.assertTrue(any(block['type'] == 'heading' for block in representation['blocks']))
        summary = next(block for block in representation['blocks'] if block['type'] == 'summary')
        self.assertEqual(summary['fields']['total']['value'], 12.5)
        self.assertIs(validate_representation(representation), representation)

    def test_original_reconstruction_keeps_editable_text_and_normalized_positions(self):
        results = [
            self.detection('ACME STORE', 20, 10, 110, 24, 0.98),
            self.detection('TOTAL $12.50', 20, 80, 110, 0.95),
        ]
        reconstruction = reconstruct_original_layout(build_document_representation(results, 200, 120))
        heading = next(block for block in reconstruction['blocks'] if block['type'] == 'heading')
        self.assertEqual(reconstruction['mode'], 'original')
        self.assertTrue(heading['editable'])
        self.assertEqual(heading['text'], 'ACME STORE')
        self.assertEqual(heading['position']['x'], 0.1)
        self.assertIn('source_position', heading)

    def test_clean_reconstruction_uses_semantic_content_not_source_coordinates(self):
        results = [
            self.detection('ACME STORE', 20, 10, 110, 24, 0.98),
            self.detection('RECEIPT', 20, 42, 70),
            self.detection('TOTAL $12.50', 20, 80, 110, 0.95),
        ]
        reconstruction = reconstruct_clean_layout(build_document_representation(results, 200, 120))
        self.assertEqual(reconstruction['mode'], 'clean')
        self.assertEqual(reconstruction['title'], 'ACME STORE')
        self.assertEqual(reconstruction['financial_summary']['total']['value'], 12.5)
        self.assertNotIn('position', reconstruction['content'][0])


class ExportEndpointTests(TestCase):
    @staticmethod
    def detection(text, x, y, width, height=16, confidence=0.9):
        return {
            'text': text,
            'confidence': confidence,
            'bounding_box': [[x, y], [x + width, y], [x + width, y + height], [x, y + height]],
        }

    def setUp(self):
        super().setUp()
        self.media_directory = TemporaryDirectory()
        self.media_settings = override_settings(MEDIA_ROOT=self.media_directory.name)
        self.media_settings.enable()
        results = [
            self.detection('ACME STORE', 20, 10, 110, 24, 0.98),
            self.detection('RECEIPT', 20, 42, 70),
            self.detection('TOTAL $12.50', 20, 80, 110, 0.95),
        ]
        self.document = Document.objects.create(
            uploaded_file='documents/export-test.png',
            status='completed',
            document_data=build_document_representation(results, 200, 120),
        )

    def tearDown(self):
        self.media_settings.disable()
        self.media_directory.cleanup()
        super().tearDown()

    def test_creates_clean_pdf_export(self):
        response = self.client.post(
            f'/api/documents/{self.document.id}/export/',
            {'format': 'pdf', 'reconstruction_mode': 'clean'},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        export = DocumentExport.objects.get(pk=response.json()['id'])
        self.assertEqual(export.export_format, 'pdf')
        self.assertTrue(export.file.storage.exists(export.file.name))

    def test_creates_editable_original_docx_export(self):
        response = self.client.post(
            f'/api/documents/{self.document.id}/export/',
            {'format': 'docx', 'reconstruction_mode': 'original'},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        export = DocumentExport.objects.get(pk=response.json()['id'])
        self.assertEqual(export.reconstruction_mode, 'original')
        self.assertTrue(export.file.storage.exists(export.file.name))

    def test_creates_txt_export(self):
        response = self.client.post(
            f'/api/documents/{self.document.id}/export/',
            {'format': 'txt', 'reconstruction_mode': 'clean'},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        export = DocumentExport.objects.get(pk=response.json()['id'])
        self.assertEqual(export.export_format, 'txt')
        self.assertTrue(export.file.storage.exists(export.file.name))



class HumanCorrectionTests(TestCase):
    def setUp(self):
        self.document = Document.objects.create(
            uploaded_file='documents/correction-test.png',
            status='completed',
            extracted_text='TOTAL $12.50',
            document_data={
                'version': 1,
                'blocks': [{'type': 'summary', 'fields': {}, 'items': [], 'review_flags': []}],
            },
        )

    def test_saves_corrected_text_and_verified_financial_field(self):
        response = self.client.patch(
            f'/api/documents/{self.document.id}/corrections/',
            data=json.dumps({
                'corrected_text': 'TOTAL $12.60',
                'verified_fields': {'total': 12.60},
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.document.refresh_from_db()
        self.assertEqual(self.document.corrected_text, 'TOTAL $12.60')
        total = self.document.document_data['blocks'][0]['fields']['total']
        self.assertEqual(total['value'], 12.60)
        self.assertTrue(total['verified_by_user'])


class FrontendServingTests(TestCase):
    def test_django_serves_the_built_react_application_at_root(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<div id="root"></div>', html=False)


class UserAuthAndSecurityTests(TestCase):
    def test_user_registration_and_jwt_login(self):
        # Register user
        reg_response = self.client.post(
            '/api/auth/register/',
            {
                'username': 'alice',
                'email': 'alice@example.com',
                'password': 'Password123!',
                'password_confirm': 'Password123!',
            },
            content_type='application/json',
        )
        self.assertEqual(reg_response.status_code, 201)
        self.assertIn('access', reg_response.json())
        token = reg_response.json()['access']

        # Get profile with Bearer token
        profile_response = self.client.get(
            '/api/auth/me/',
            HTTP_AUTHORIZATION=f'Bearer {token}'
        )
        self.assertEqual(profile_response.status_code, 200)
        self.assertEqual(profile_response.json()['username'], 'alice')

    def test_tenant_isolation_prevents_unauthorized_access(self):
        from django.contrib.auth.models import User
        user_alice = User.objects.create_user(username='alice_tenant', password='Password123!')
        user_bob = User.objects.create_user(username='bob_tenant', password='Password123!')

        doc_alice = Document.objects.create(
            user=user_alice,
            title='Alice Doc',
            uploaded_file='documents/alice.png',
            status='completed',
            extracted_text='Confidential Alice Data',
            document_data={'version': 1, 'blocks': []}
        )

        # Bob logs in
        login_res = self.client.post(
            '/api/auth/token/',
            {'username': 'bob_tenant', 'password': 'Password123!'},
            content_type='application/json'
        )
        bob_token = login_res.json()['access']

        # Bob tries to access Alice's document -> Must return 404
        bob_res = self.client.get(
            f'/api/documents/{doc_alice.id}/',
            HTTP_AUTHORIZATION=f'Bearer {bob_token}'
        )
        self.assertEqual(bob_res.status_code, 404)

        # Bob lists documents -> Should not see Alice's document
        bob_list = self.client.get(
            '/api/documents/',
            HTTP_AUTHORIZATION=f'Bearer {bob_token}'
        )
        self.assertEqual(bob_list.status_code, 200)
        bob_results = bob_list.json().get('results', bob_list.json())
        self.assertEqual(len(bob_results), 0)


class DocumentQuestionAnsweringTests(TestCase):
    def test_rag_answers_grounded_questions_from_document_facts(self):
        document = Document.objects.create(
            title='Receipt Acme',
            uploaded_file='documents/acme.png',
            status='completed',
            extracted_text='ACME STORE\nDate: 24 May 2024\nTOTAL $114.63',
            document_data={
                'version': 1,
                'fields': {
                    'vendor': {'value': 'ACME STORE', 'confidence': 0.98},
                    'date': {'value': '24 May 2024', 'confidence': 0.95},
                    'total': {'value': 114.63, 'confidence': 0.96},
                    'currency': {'value': '$', 'confidence': 0.95},
                },
                'blocks': [
                    {'type': 'heading', 'text': 'ACME STORE', 'source_position': {'x': 10, 'y': 10, 'width': 80, 'height': 20}},
                    {'type': 'text', 'text': 'TOTAL $114.63', 'source_position': {'x': 10, 'y': 80, 'width': 60, 'height': 15}},
                ]
            }
        )

        # Ask about total
        res_total = self.client.post(
            f'/api/documents/{document.id}/ask/',
            {'question': 'What is the total amount?'},
            content_type='application/json'
        )
        self.assertEqual(res_total.status_code, 200)
        self.assertTrue(res_total.json()['grounded'])
        self.assertIn('114.63', res_total.json()['answer'])

        # Ask about vendor
        res_vendor = self.client.post(
            f'/api/documents/{document.id}/ask/',
            {'question': 'Who is the merchant or vendor?'},
            content_type='application/json'
        )
        self.assertEqual(res_vendor.status_code, 200)
        self.assertTrue(res_vendor.json()['grounded'])
        self.assertIn('ACME STORE', res_vendor.json()['answer'])


class TrOCRSegmentationAndMultiPageTests(SimpleTestCase):
    def test_trocr_engine_availability_and_line_segmentation(self):
        from .services.ocr.trocr import TrOCREngine
        engine = TrOCREngine()
        # Verify engine metadata
        self.assertEqual(engine.name, 'trocr')
        self.assertEqual(engine.model_name, 'microsoft/trocr-base-handwritten')
        self.assertTrue(engine.is_available())

        # Create a synthetic image with 2 horizontal text lines
        synthetic = np.full((120, 240, 3), 255, dtype=np.uint8)
        # Line 1: black horizontal bar simulating a word
        synthetic[25:35, 30:180] = 0
        # Line 2: black horizontal bar simulating second line
        synthetic[75:85, 30:190] = 0

        boxes = engine._segment_handwritten_lines(synthetic)
        self.assertGreaterEqual(len(boxes), 1)
        # All boxes should have positive width and height
        for x, y, w, h in boxes:
            self.assertGreater(w, 0)
            self.assertGreater(h, 0)


class DocTREngineAndReprocessTests(TestCase):
    def test_doctr_engine_registered_and_available(self):
        from .services.ocr.doctr_engine import DocTREngine
        from .services.ocr.model_registry import get_engine
        engine = get_engine('doctr')
        self.assertIsInstance(engine, DocTREngine)
        self.assertEqual(engine.name, 'doctr')
        self.assertEqual(engine.model_name, 'db_mobilenet_v3_large+crnn_mobilenet_v3_large')
        self.assertTrue(engine.is_available())

    def test_document_reprocess_endpoint(self):
        doc = Document.objects.create(
            uploaded_file='documents/reprocess-test.png',
            status='failed',
            failure_reason='Network timeout during scan',
        )
        with patch('documents.tasks.process_document_task.delay') as mock_task:
            response = self.client.post(f'/api/documents/{doc.id}/reprocess/')
            self.assertEqual(response.status_code, 200)
            mock_task.assert_called_once_with(doc.id)
            doc.refresh_from_db()
            self.assertEqual(doc.status, 'processing')
            self.assertEqual(doc.progress_stage, 'reprocessing')
            self.assertEqual(doc.failure_reason, '')

    def test_document_autocorrect_endpoint(self):
        doc = Document.objects.create(
            uploaded_file='documents/autocorrect-test.png',
            status='completed',
            extracted_text='Brain st scan with reciept and amout $45.00',
        )
        response = self.client.post(
            f'/api/documents/{doc.id}/autocorrect/',
            {'text': doc.extracted_text},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('Brain', data['corrected_text'])
        self.assertNotIn('Brain st', data['corrected_text'])
        self.assertIn('receipt', data['corrected_text'].lower())
        self.assertIn('amount', data['corrected_text'].lower())
        self.assertGreaterEqual(data['changes_count'], 2)


class HealthAndDeploymentTests(TestCase):
    def test_root_health_endpoint_returns_200(self):
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('status'), 'healthy')
        self.assertEqual(data.get('service'), 'docuscan-api')

    def test_root_health_without_trailing_slash_returns_200(self):
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get('status'), 'healthy')

    def test_api_health_endpoint_returns_200(self):
        response = self.client.get('/api/health/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get('status'), 'healthy')

    def test_api_health_without_trailing_slash_returns_200(self):
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get('status'), 'healthy')

    def test_health_check_does_not_load_ocr_model(self):
        from .services.ocr.doctr_engine import DocTREngine
        DocTREngine.reset_model()
        self.assertFalse(DocTREngine.is_model_loaded())

        # Call health check
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 200)

        # Confirm model remains unloaded
        self.assertFalse(DocTREngine.is_model_loaded())


class LazyOCRInitializationTests(TestCase):
    def setUp(self):
        from .services.ocr.doctr_engine import DocTREngine
        DocTREngine.reset_model()

    def tearDown(self):
        from .services.ocr.doctr_engine import DocTREngine
        DocTREngine.reset_model()

    def test_is_available_does_not_load_model(self):
        from .services.ocr.doctr_engine import DocTREngine
        engine = DocTREngine()
        self.assertFalse(DocTREngine.is_model_loaded())
        self.assertTrue(engine.is_available())
        self.assertFalse(DocTREngine.is_model_loaded())

    def test_lazy_initialization_and_thread_safety(self):
        from .services.ocr.doctr_engine import DocTREngine
        import threading

        engine = DocTREngine()
        self.assertFalse(DocTREngine.is_model_loaded())
        self.assertIsInstance(DocTREngine._lock, type(threading.Lock()))

        # Mock ocr_predictor to test thread-safe lazy caching without downloading 100MB weights in unit test
        with patch('doctr.models.ocr_predictor', return_value='mock_predictor') as mock_pred:
            predictor1 = engine._load_model()
            self.assertEqual(predictor1, 'mock_predictor')
            self.assertTrue(DocTREngine.is_model_loaded())
            mock_pred.assert_called_once()

            # Second call should use cached predictor without re-invoking constructor
            predictor2 = engine._load_model()
            self.assertEqual(predictor2, 'mock_predictor')
            self.assertEqual(mock_pred.call_count, 1)

    def test_initialization_failure_raises_ocr_unavailable(self):
        from .services.ocr.doctr_engine import DocTREngine
        from .services.ocr.base import OCRUnavailable

        engine = DocTREngine()
        with patch('doctr.models.ocr_predictor', side_effect=RuntimeError('Out of memory')):
            with self.assertRaises(OCRUnavailable):
                engine._load_model()
            self.assertFalse(DocTREngine.is_model_loaded())




