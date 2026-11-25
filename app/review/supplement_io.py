"""Parsing helpers for relation supplements submitted as CSV or text."""
from __future__ import annotations

import csv
import io
import json


ALIASES = {
    'case': ('case', 'case_id', 'caseid', 'case_code', 'group', 'group_id'),
    'a': ('a', 'left', 'source', 'from', 'sample_a', 'samplea', 'left_sample', 'sample', 'sample_id'),
    'b': ('b', 'right', 'target', 'to', 'sample_b', 'sampleb', 'right_sample', 'related',
          'related_sample', 'other', 'entity', 'duplicate'),
}


def _decode(value):
    if isinstance(value, bytes):
        return value.decode('utf-8-sig')
    return str(value)


def parse_relation_text(value):
    text = _decode(value).strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except (TypeError, ValueError):
        parsed = None
    if parsed is not None:
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            for key in ('relations', 'supplements', 'links', 'pairs'):
                if isinstance(parsed.get(key), list):
                    return parsed[key]
            return [parsed]

    reader = csv.reader(io.StringIO(text, newline=''))
    rows = [row for row in reader if any(cell.strip() for cell in row)]
    if not rows:
        return []
    header = [cell.strip() for cell in rows[0]]
    lowered = [cell.lower() for cell in header]
    has_header = any(any(alias in lowered for alias in names) for names in ALIASES.values()) or 'kind' in lowered

    relations = []
    if has_header:
        dict_reader = csv.DictReader(io.StringIO(text, newline=''))
        for row in dict_reader:
            normalized_header = {str(key).strip().lower(): value for key, value in row.items() if key is not None}
            if normalized_header.get('kind') and normalized_header.get('kind') != 'duplicate':
                continue
            item = {}
            for target, names in ALIASES.items():
                for name in names:
                    if name in normalized_header and normalized_header[name] not in (None, ''):
                        item[target] = normalized_header[name].strip()
                        break
            # Standard domain CSV puts the related sample in ``entity`` for
            # duplicate rows; that alias is already handled above.
            if item.get('a') and item.get('b'):
                relations.append(item)
    else:
        for row in rows:
            cells = [cell.strip() for cell in row if cell is not None]
            if len(cells) == 2:
                relations.append({'a': cells[0], 'b': cells[1]})
            elif len(cells) >= 3:
                relations.append({'case': cells[0], 'a': cells[1], 'b': cells[2]})
    return relations


def parse_relation_file(uploaded):
    raw = uploaded.read()
    return parse_relation_text(raw)
