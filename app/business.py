"""业务阶段之间约定的结果结构。"""
class DomainIssue(ValueError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def by_kind(rows, kind):
    return [r for r in rows if r['kind'] == kind]


def single(rows, kind):
    found = by_kind(rows, kind)
    if len(found) != 1:
        raise DomainIssue('EXPECTED_ONE_' + kind.upper())
    return found[0]


def prepared(count, details, payload):
    return {'count': count, 'details': details}, payload


def measured(value, expected, unit, evidence, flag=None):
    return dict(value=value, expected=expected, unit=unit, evidence=evidence, flag=flag)


def decision(result, reason=None, *, tolerance=0, upper_bound=False, lower_bound=False):
    delta = result['value'] - result['expected']
    if upper_bound:
        matches = delta <= 0
    elif lower_bound:
        matches = delta >= 0
    else:
        matches = abs(delta) <= tolerance
    return dict(status=reason or ('READY' if matches else 'MISMATCH'), delta=delta)


def intervals(spans):
    merged = []
    for start, end in sorted(spans):
        if end <= start:
            continue
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return merged


def subtract(base, blocks):
    pieces = []
    for start, end in base:
        cursor = start
        for left, right in blocks:
            if right <= cursor:
                continue
            if left >= end:
                break
            if left > cursor:
                pieces.append((cursor, left))
            cursor = max(cursor, right)
        if cursor < end:
            pieces.append((cursor, end))
    return pieces


def overlap(a, b):
    i = j = total = 0
    while i < len(a) and j < len(b):
        left, right = a[i], b[j]
        total += max(0, min(left[1], right[1])-max(left[0],right[0]))
        if left[1] <= right[1]:
            i += 1
        else:
            j += 1
    return total
