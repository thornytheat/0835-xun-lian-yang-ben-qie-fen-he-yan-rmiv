BOUNDARIES = [('0004', 2, {'day': 4}, 'MISMATCH', 0), ('0001', 1, {'split_code': 2}, 'CROSS_CUTOFF_LEAKAGE', 2), ('0002', 3, {'entity': 1}, 'UNKNOWN_SAMPLE', None)]

"""改变来源样例的业务边界，核对复核状态和具体数值。"""
from io import StringIO
from csv import DictReader, reader, writer

from app.modules.pipeline import run


def altered(data, group, number=None, patch=None):
    from csv import Error
    text = data.decode('utf-8-sig')
    source = reader(StringIO(text, newline=''), strict=True)
    header = next(source)
    rows = []
    while True:
        try:
            rows.append(dict(zip(header, next(source))))
        except StopIteration:
            break
        except Error:
            break
    rows = [row for row in rows if row.get('case') == group and row.get('record') != 'record']
    rows = list({row['record']: row for row in rows}.values())
    target = next(row for row in rows if row['record'] == f"{group}{number:02d}")
    for key, value in (patch or {}).items():
        target[key] = str(value)
    output = StringIO(newline='')
    sink = writer(output)
    sink.writerow(header)
    for row in rows:
        sink.writerow([row[field] for field in header])
    return output.getvalue().encode()

def inspect(data, group):
    report = run(data)
    return next(case for case in report['cases'] if case['case'] == group), report


def test_boundary_one(dirty):
    group, number, patch, status, value = BOUNDARIES[0]
    case, _ = inspect(altered(dirty, group, number, patch), group)
    assert case['status'] == status
    if value is not None:
        assert case['measure']['value'] == value


def test_boundary_two(dirty):
    group, number, patch, status, value = BOUNDARIES[1]
    case, _ = inspect(altered(dirty, group, number, patch), group)
    assert case['status'] == status
    if value is not None:
        assert case['measure']['value'] == value


def test_boundary_three(dirty):
    group, number, patch, status, value = BOUNDARIES[2]
    case, _ = inspect(altered(dirty, group, number, patch), group)
    assert case['status'] == status
    if value is not None:
        assert case['measure']['value'] == value


def test_modified_boundary_is_not_releasable(dirty):
    group, number, patch, status, _ = next(item for item in BOUNDARIES if item[3] != 'READY')
    _, report = inspect(altered(dirty, group, number, patch), group)
    assert not report['balance']['releasable']


def test_case_order_does_not_change_measures(clean):
    rows = list(reader(StringIO(clean.decode('utf-8-sig'), newline='')))
    output = StringIO(newline='')
    sink = writer(output)
    sink.writerows([rows[0], *reversed(rows[1:])])
    first, _ = inspect(clean, '0001')
    second, _ = inspect(output.getvalue().encode(), '0001')
    first_cases = {row['case']: row['measure']['value'] for row in run(clean)['cases'] if 'measure' in row}
    second_cases = {row['case']: row['measure']['value'] for row in run(output.getvalue().encode())['cases'] if 'measure' in row}
    assert first_cases == second_cases
