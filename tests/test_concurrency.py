from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from app.business import DomainIssue
from app.review.service import execute, review


def test_parallel_rerun_commits_single_row(store, clean):
    start=Barrier(4)
    def load():
        start.wait(3)
        return execute(store,clean)
    with ThreadPoolExecutor(max_workers=4) as threads:
        results=list(threads.map(lambda _:load(),range(4)))
    assert all(result==results[0] for result in results)
    assert len(store.list())==1


def test_parallel_review_has_one_winner(store, dirty):
    run=execute(store,dirty); start=Barrier(2)
    def attempt(note):
        start.wait(3)
        try:
            return review(store,run['id'],dict(revision=0,status='HELD',note=note))['status']
        except DomainIssue as error:
            return error.code
    with ThreadPoolExecutor(max_workers=2) as threads:
        results=list(threads.map(attempt,['来源待检查','分组待处理']))
    assert sorted(results)==['HELD','STALE_REVIEW']
    assert store.load(run['id'])['revision']==1
