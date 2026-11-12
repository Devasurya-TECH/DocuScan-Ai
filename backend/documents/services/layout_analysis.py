"""Deterministic layout analysis for OCR detections.

The input is the persisted EasyOCR-compatible shape: ``text``, ``confidence``
and a four-point ``bounding_box``. The returned representation remains JSON
serialisable and keeps the original detection indexes and coordinates so later
rendering services do not have to re-run OCR.
"""

import re
from statistics import median


PRICE_PATTERN = re.compile(r'^(?:[$€£₹]\s*)?(?:\d{1,3}(?:,\d{3})*|\d+)\.\d{2}[)]?$')


def _rectangle(points):
    x_values = [point[0] for point in points]
    y_values = [point[1] for point in points]
    x, y = min(x_values), min(y_values)
    right, bottom = max(x_values), max(y_values)
    return {
        'x': int(x), 'y': int(y),
        'width': max(1, int(right - x)), 'height': max(1, int(bottom - y)),
    }


def _right(rectangle):
    return rectangle['x'] + rectangle['width']


def _bottom(rectangle):
    return rectangle['y'] + rectangle['height']


def _union(rectangles):
    left, top = min(item['x'] for item in rectangles), min(item['y'] for item in rectangles)
    right, bottom = max(_right(item) for item in rectangles), max(_bottom(item) for item in rectangles)
    return {'x': left, 'y': top, 'width': right - left, 'height': bottom - top}


def _normalise_detections(detections):
    normalised = []
    for index, item in enumerate(detections):
        points = item.get('bounding_box') or []
        text = str(item.get('text') or '').strip()
        if not text or len(points) < 4:
            continue
        try:
            rect = _rectangle(points)
        except (IndexError, TypeError):
            continue
        normalised.append({
            'detection_index': index,
            'text': text,
            'confidence': round(float(item.get('confidence') or 0), 6),
            'bounding_box': [[int(point[0]), int(point[1])] for point in points],
            'position': rect,
        })
    return normalised


def _same_line(element, line, tolerance):
    rect, line_rect = element['position'], line['position']
    overlap = max(0, min(_bottom(rect), _bottom(line_rect)) - max(rect['y'], line_rect['y']))
    overlap_ratio = overlap / min(rect['height'], line_rect['height'])
    element_center = rect['y'] + rect['height'] / 2
    line_center = line_rect['y'] + line_rect['height'] / 2
    return overlap_ratio >= 0.35 or abs(element_center - line_center) <= tolerance


def group_into_lines(elements):
    """Group detections with aligned vertical extents, retaining every box."""
    if not elements:
        return []
    median_height = median(item['position']['height'] for item in elements)
    tolerance = max(7, median_height * 0.65)
    provisional = []
    for element in sorted(elements, key=lambda item: (item['position']['y'], item['position']['x'])):
        matching = [line for line in provisional if _same_line(element, line, tolerance)]
        if matching:
            line = min(matching, key=lambda item: abs(item['position']['y'] - element['position']['y']))
            line['elements'].append(element)
            line['position'] = _union([entry['position'] for entry in line['elements']])
        else:
            provisional.append({'elements': [element], 'position': dict(element['position'])})

    lines = []
    for index, line in enumerate(sorted(provisional, key=lambda item: item['position']['y'])):
        entries = sorted(line['elements'], key=lambda item: item['position']['x'])
        lines.append({
            'id': f'line_{index}',
            'text': ' '.join(item['text'] for item in entries),
            'position': _union([item['position'] for item in entries]),
            'confidence': round(sum(item['confidence'] for item in entries) / len(entries), 6),
            'detection_indexes': [item['detection_index'] for item in entries],
            'elements': entries,
        })
    return lines


def _detect_columns(lines, page_width):
    """Detect sustained left/right text bands; table rows are excluded upstream."""
    midpoint = page_width / 2
    left = [line for line in lines if _right(line['position']) < midpoint]
    right = [line for line in lines if line['position']['x'] > midpoint]
    if len(left) < 2 or len(right) < 2:
        return [{'id': 'column_0', 'position': {'x': 0, 'y': 0, 'width': page_width, 'height': None}}]

    left_span = max(_bottom(line['position']) for line in left) - min(line['position']['y'] for line in left)
    right_span = max(_bottom(line['position']) for line in right) - min(line['position']['y'] for line in right)
    overlap = max(0, min(max(_bottom(line['position']) for line in left), max(_bottom(line['position']) for line in right)) - max(min(line['position']['y'] for line in left), min(line['position']['y'] for line in right)))
    if not min(left_span, right_span) or overlap / min(left_span, right_span) < 0.35:
        return [{'id': 'column_0', 'position': {'x': 0, 'y': 0, 'width': page_width, 'height': None}}]
    return [
        {'id': 'column_0', 'position': {'x': 0, 'y': 0, 'width': int(midpoint), 'height': None}},
        {'id': 'column_1', 'position': {'x': int(midpoint), 'y': 0, 'width': int(page_width - midpoint), 'height': None}},
    ]


def _table_row(line):
    entries = line['elements']
    price_entries = [entry for entry in entries if PRICE_PATTERN.match(entry['text'].replace(' ', ''))]
    if not price_entries:
        return None
    price = price_entries[-1]
    description = [entry for entry in entries if entry['detection_index'] != price['detection_index'] and entry['position']['x'] < price['position']['x']]
    if not description:
        return None
    return {
        'line_id': line['id'],
        'cells': [
            {'text': ' '.join(item['text'] for item in description), 'position': _union([item['position'] for item in description])},
            {'text': price['text'], 'position': price['position']},
        ],
    }


def detect_tables(lines):
    """Find consecutive description-plus-price rows, a conservative receipt table heuristic."""
    candidates = [_table_row(line) for line in lines]
    groups, current = [], []
    median_height = median([line['position']['height'] for line in lines]) if lines else 20
    for candidate in candidates:
        if candidate is None:
            if len(current) >= 2:
                groups.append(current)
            current = []
            continue
        if current:
            previous_line = next(line for line in lines if line['id'] == current[-1]['line_id'])
            current_line = next(line for line in lines if line['id'] == candidate['line_id'])
            if current_line['position']['y'] - _bottom(previous_line['position']) > median_height * 2.25:
                if len(current) >= 2:
                    groups.append(current)
                current = []
        current.append(candidate)
    if len(current) >= 2:
        groups.append(current)

    tables = []
    for index, rows in enumerate(groups):
        rectangles = [cell['position'] for row in rows for cell in row['cells']]
        tables.append({
            'id': f'table_{index}',
            'columns': ['description', 'amount'],
            'position': _union(rectangles),
            'line_ids': [row['line_id'] for row in rows],
            'rows': rows,
        })
    return tables


def _is_heading(line, median_height):
    letters = ''.join(character for character in line['text'] if character.isalpha())
    uppercase_ratio = sum(character.isupper() for character in letters) / len(letters) if letters else 0
    return len(line['text']) <= 80 and (line['position']['height'] >= median_height * 1.35 or uppercase_ratio >= 0.8)


def _group_paragraphs(lines, table_line_ids):
    usable = [line for line in lines if line['id'] not in table_line_ids]
    if not usable:
        return [], []
    median_height = median(line['position']['height'] for line in usable)
    headings, paragraphs, current = [], [], []
    for line in usable:
        rect = line['position']
        if _is_heading(line, median_height):
            if current:
                paragraphs.append(current)
                current = []
            headings.append(line['id'])
            continue
        if current:
            previous = current[-1]['position']
            gap = rect['y'] - _bottom(previous)
            if gap > median_height * 1.9:
                paragraphs.append(current)
                current = []
        current.append(line)
    if current:
        paragraphs.append(current)
    return headings, [
        {
            'id': f'paragraph_{index}',
            'line_ids': [line['id'] for line in group],
            'text': '\n'.join(line['text'] for line in group),
            'position': _union([line['position'] for line in group]),
            'confidence': round(sum(line['confidence'] for line in group) / len(group), 6),
        }
        for index, group in enumerate(paragraphs)
    ]


def analyse_layout(detections, page_width=None, page_height=None):
    """Return a normalised, deterministic document-layout representation."""
    if not isinstance(detections, list):
        raise ValueError('detections must be a list of OCR result objects')
    elements = _normalise_detections(detections)
    if not elements:
        return {'version': 1, 'page': {'width': page_width or 0, 'height': page_height or 0}, 'elements': [], 'lines': [], 'paragraphs': [], 'tables': [], 'sections': [], 'columns': []}

    inferred_width = max(_right(item['position']) for item in elements)
    inferred_height = max(_bottom(item['position']) for item in elements)
    page_width, page_height = int(page_width or inferred_width), int(page_height or inferred_height)
    lines = group_into_lines(elements)
    tables = detect_tables(lines)
    table_line_ids = {line_id for table in tables for line_id in table['line_ids']}
    columns = _detect_columns([line for line in lines if line['id'] not in table_line_ids], page_width)
    headings, paragraphs = _group_paragraphs(lines, table_line_ids)
    header_line_ids = [line['id'] for line in lines if line['position']['y'] <= page_height * 0.12]
    footer_line_ids = [line['id'] for line in lines if _bottom(line['position']) >= page_height * 0.88]
    sections = [
        {'id': f'section_{index}', 'heading_line_id': heading_id, 'paragraph_ids': [paragraph['id'] for paragraph in paragraphs if paragraph['position']['y'] > next(line['position']['y'] for line in lines if line['id'] == heading_id)]}
        for index, heading_id in enumerate(headings)
    ]
    return {
        'version': 1,
        'page': {'width': page_width, 'height': page_height},
        'elements': elements,
        'reading_order': [line['id'] for line in lines],
        'lines': lines,
        'paragraphs': paragraphs,
        'tables': tables,
        'sections': sections,
        'columns': columns,
        'header_line_ids': header_line_ids,
        'footer_line_ids': footer_line_ids,
    }
