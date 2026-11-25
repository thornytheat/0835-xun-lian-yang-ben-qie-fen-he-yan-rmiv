from app.modules.pipeline import run
from domain_expectations import EVIDENCE


def find(data, code):
    return next(c for c in run(data, 3)["cases"] if c["case"]==code)


def test_case_0001(dirty):
    item = find(dirty, '0001')
    assert item.get('measure', {}).get('value') == 2


def test_case_0002(dirty):
    item = find(dirty, '0002')
    assert item.get('measure', {}).get('value') == 2


def test_case_0003(dirty):
    item = find(dirty, '0003')
    assert item.get('measure', {}).get('value') == None


def test_case_0004(dirty):
    item = find(dirty, '0004')
    assert item.get('measure', {}).get('value') == 0


def test_business_evidence_0001(dirty):
    assert find(dirty, '0001')['measure']['evidence'] == EVIDENCE['0001']


def test_business_evidence_0004(dirty):
    assert find(dirty, '0004')['measure']['evidence'] == EVIDENCE['0004']
