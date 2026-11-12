"""Run repeatable OCR benchmarks against manually verified labels."""

import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

import cv2
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from documents.services.ocr_evaluation import benchmark_easyocr_variants


DEFAULT_STRATEGIES = (
    'color',
    'clahe',
    'adaptive_threshold',
    'enhanced_color',
    'deskewed_clahe',
)
IMAGE_SUFFIXES = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tif', '.tiff')


def evaluation_root():
    return Path(settings.BASE_DIR) / 'documents' / 'evaluation'


def image_path_for(sample_id, category, dataset_root):
    image_directory = dataset_root / category / 'images'
    matches = [image_directory / f'{sample_id}{suffix}' for suffix in IMAGE_SUFFIXES]
    return next((path for path in matches if path.is_file()), None)


def mean_or_none(values):
    return round(mean(values), 6) if values else None


class Command(BaseCommand):
    help = 'Benchmark EasyOCR preprocessing strategies using verified evaluation labels.'

    def add_arguments(self, parser):
        parser.add_argument('--split', choices=('development', 'holdout', 'all'), default='development')
        parser.add_argument('--strategies', nargs='+', default=DEFAULT_STRATEGIES)
        parser.add_argument('--output', help='Optional JSON result path. Defaults to evaluation/results/.')

    def handle(self, *args, **options):
        root = evaluation_root()
        dataset_root = root / 'dataset'
        manifest_path = dataset_root / 'dataset_manifest.json'
        if not manifest_path.is_file():
            raise CommandError(f'Missing dataset manifest: {manifest_path}')

        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        requested_split = options['split']
        samples = [
            sample for sample in manifest.get('samples', [])
            if requested_split == 'all' or sample.get('split') == requested_split
        ]
        if not samples:
            raise CommandError(f'No {requested_split} samples exist in the verified dataset manifest.')

        allowed_categories = set(manifest.get('categories', []))
        records = []
        for sample in samples:
            sample_id = sample.get('id')
            category = sample.get('category')
            if not sample_id or category not in allowed_categories:
                raise CommandError(f'Invalid manifest record: {sample}')
            image_path = image_path_for(sample_id, category, dataset_root)
            truth_path = dataset_root / category / 'ground_truth' / f'{sample_id}.txt'
            if image_path is None or not truth_path.is_file():
                raise CommandError(
                    f'Missing verified pair for {category}/{sample_id}: image and .txt label are both required.'
                )
            image = cv2.imread(str(image_path))
            if image is None:
                raise CommandError(f'Unable to read image: {image_path}')
            reference_text = truth_path.read_text(encoding='utf-8')
            if not reference_text.strip():
                raise CommandError(f'Ground-truth text is empty: {truth_path}')
            for result in benchmark_easyocr_variants(image, reference_text, options['strategies']):
                records.append({'sample_id': sample_id, 'category': category, 'split': sample['split'], **result})
            self.stdout.write(f'Benchmarked {category}/{sample_id}')

        groups = defaultdict(list)
        for record in records:
            groups[(record['category'], record['strategy'])].append(record)
        summaries = [
            {
                'category': category,
                'engine': 'easyocr',
                'strategy': strategy,
                'sample_count': len(group),
                'average_character_error_rate': mean_or_none([item['character_error_rate'] for item in group]),
                'average_word_error_rate': mean_or_none([item['word_error_rate'] for item in group]),
                'average_processing_seconds': mean_or_none([item['processing_seconds'] for item in group]),
                'average_detection_count': mean_or_none([item['detection_count'] for item in group]),
                'average_confidence': mean_or_none([item['average_confidence'] for item in group if item['average_confidence'] is not None]),
            }
            for (category, strategy), group in sorted(groups.items())
        ]
        report = {
            'schema_version': 1,
            'created_at': timezone.now().isoformat(),
            'split': requested_split,
            'strategies': list(options['strategies']),
            'sample_count': len(samples),
            'records': records,
            'summaries': summaries,
        }
        output_path = Path(options['output']) if options['output'] else root / 'results' / f'benchmark_{requested_split}.json'
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
        self.stdout.write(self.style.SUCCESS(f'Wrote {len(records)} results to {output_path}'))
