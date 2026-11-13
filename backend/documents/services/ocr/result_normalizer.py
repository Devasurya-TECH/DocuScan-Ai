"""Normalize OCR adapters into the stable document-processing schema."""


def normalize_detection(
    *, engine, model_name, text, confidence, bounding_box, language,
    region_type='printed_text', warnings=None, raw_metadata=None,
):
    if not isinstance(text, str):
        raise ValueError('OCR text must be a string')
    points = [[int(point[0]), int(point[1])] for point in bounding_box]
    if len(points) < 4:
        raise ValueError('OCR detections require a four-point bounding box')
    return {
        'engine': engine,
        'model_name': model_name,
        'text': text,
        'confidence': max(0.0, min(1.0, float(confidence))),
        'bounding_box': points,
        'language': language,
        'region_type': region_type,
        'warnings': warnings or [],
        'raw_metadata': raw_metadata or {},
    }
