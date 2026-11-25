import pytest

from app.business import DomainIssue
from app.review.service import execute, review


def test_byte_identical_rerun_keeps_run_and_manifest(store, clean):
    first=execute(store,clean); second=execute(store,clean)
    assert first==second and len(store.list())==1


def test_different_source_starts_new_run(store, clean, dirty):
    assert execute(store,clean)['id']!=execute(store,dirty)['id']
    assert len(store.list())==2


def test_valid_approval_trims_note(store, clean):
    run=execute(store,clean)
    output=review(store,run['id'],dict(revision=0,status='APPROVED',note='  源文件已复核  '))
    assert (output['status'],output['revision'],output['note'])==('APPROVED',1,'源文件已复核')


def test_review_optimistic_lock(store, dirty):  # TRAP-26
    run=execute(store,dirty); update=dict(revision=0,status='HELD',note='请核对样例')
    review(store,run['id'],update)
    with pytest.raises(DomainIssue,match='STALE_REVIEW'): review(store,run['id'],update)


def test_dirty_batch_cannot_be_approved(store, dirty):
    run=execute(store,dirty)
    with pytest.raises(DomainIssue,match='UNRESOLVED_ISSUES'):
        review(store,run['id'],dict(revision=0,status='APPROVED',note='核对已完成'))
    assert store.load(run['id'])['revision']==0


def test_approved_batch_is_final(store, clean):
    run=execute(store,clean)
    review(store,run['id'],dict(revision=0,status='APPROVED',note='完成最终复核'))
    with pytest.raises(DomainIssue,match='RUN_FINALIZED'):
        review(store,run['id'],dict(revision=1,status='HELD',note='试图撤销签发'))
