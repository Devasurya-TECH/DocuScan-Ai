"""Script identification from OCR output for multilingual audit metadata."""

from collections import Counter


SCRIPTS = {
    'devanagari': ((0x0900, 0x097F), 'hi'), 'tamil': ((0x0B80, 0x0BFF), 'ta'),
    'bengali': ((0x0980, 0x09FF), 'bn'), 'telugu': ((0x0C00, 0x0C7F), 'te'),
    'kannada': ((0x0C80, 0x0CFF), 'kn'), 'malayalam': ((0x0D00, 0x0D7F), 'ml'),
    'gujarati': ((0x0A80, 0x0AFF), 'gu'), 'gurmukhi': ((0x0A00, 0x0A7F), 'pa'),
    'arabic': ((0x0600, 0x06FF), 'ar'), 'cyrillic': ((0x0400, 0x052F), 'ru'),
    'latin': ((0x0041, 0x024F), 'en'),
}


def identify_scripts(detections):
    """Return transparent script distribution, based on returned OCR text."""
    counts = Counter()
    for item in detections:
        for character in str(item.get('text') or ''):
            codepoint = ord(character)
            for script, ((lower, upper), _) in SCRIPTS.items():
                if lower <= codepoint <= upper:
                    counts[script] += 1
                    break
    if not counts:
        return {'primary_script': 'unknown', 'primary_language': None, 'scripts': {}}
    primary_script, _ = counts.most_common(1)[0]
    total = sum(counts.values())
    return {'primary_script': primary_script, 'primary_language': SCRIPTS[primary_script][1], 'scripts': {script: {'characters': amount, 'ratio': round(amount / total, 4)} for script, amount in counts.most_common()}}


def annotate_detection_languages(detections):
    for item in detections:
        identified = identify_scripts([item])
        if identified['primary_language']:
            item['language'] = identified['primary_language']
    return identify_scripts(detections)
