from collections import defaultdict


def partition(candidates):
    by_key = defaultdict(list)
    for line, row in candidates:
        by_key[row['record']].append((line, row))
    accepted, rejected = [], []
    for key, records in by_key.items():
        first = records[0][1]
        if any(row != first for _, row in records):
            rejected.extend({'line': line, 'record': key, 'case': row['case'], 'reason': 'DUPLICATE_CONFLICT'} for line,row in records)
            continue
        accepted.append(first)
        rejected.extend({'line': line, 'record': key, 'case': row['case'], 'reason': 'DUPLICATE_REPLAY'} for line,row in records[1:])
    return accepted, rejected
