from app.modules.pipeline import run


def find(data, code):
    return next(c for c in run(data, 2)["cases"] if c["case"]==code)


def test_case_0001(dirty):
    item = find(dirty, '0001')
    assert item.get('prep', {}).get('count', 0) == 4


def test_case_0002(dirty):
    item = find(dirty, '0002')
    assert item.get('prep', {}).get('count', 0) == 2


def test_case_0003(dirty):
    item = find(dirty, '0003')
    assert item.get('prep', {}).get('count', 0) == 0


def test_case_0004(dirty):
    item = find(dirty, '0004')
    assert item.get('prep', {}).get('count', 0) == 2


def test_preparation_does_not_calculate(dirty):
    assert 'measure' not in find(dirty,'0001')


def test_preparation_retains_source_keys(dirty):
    assert '000101' in find(dirty,'0001')['records']
