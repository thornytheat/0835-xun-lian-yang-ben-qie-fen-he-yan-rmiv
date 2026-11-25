from app.modules.pipeline import run
from app.modules.reconcile import balance


def test_input_row_conservation(dirty):
    checks=run(dirty)['balance']
    assert checks['input']==checks['accepted']+checks['isolated']+checks['ignored']


def test_business_cases_conserve_input(dirty):
    report=run(dirty)
    assert len(report['cases'])==4
    assert sum(len(c['records']) for c in report['cases'])==report['balance']['accepted']


def test_clean_case_set_is_releasable(clean):
    assert run(clean)['balance']['releasable'] is True


def test_dirty_case_set_is_blocked(dirty):
    checks=run(dirty)['balance']
    assert checks['isolated']==5 and checks['pending']==2 and not checks['releasable']


def test_empty_case_set_cannot_release():
    checks=balance(dict(input=1,accepted=0,rejected=0,blank=1,repeated=0),[])
    assert checks['balanced'] and not checks['releasable']


def test_miscounted_lines_cannot_release():
    checks=balance(dict(input=9,accepted=1,rejected=0,blank=0,repeated=0),[dict(records=['a'],status='READY')])
    assert not checks['balanced'] and not checks['releasable']
