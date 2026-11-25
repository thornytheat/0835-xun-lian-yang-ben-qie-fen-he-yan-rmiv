import pytest

from app.business import DomainIssue
from app.review.service import execute, review, supplement


def case_roster(run, code='0001'):
    return run['roster']['by_case'][code]


def test_cross_cutoff_relation_quarantines_entire_transitive_group(store, clean):
    run = execute(store, clean)
    updated = supplement(store, run['id'], {'case': '0001', 'a': 2, 'b': 3})
    roster = case_roster(updated)

    assert roster['groups'] == [[1, 2, 3, 4]]
    assert roster['quarantined'] == [1, 2, 3, 4]
    assert roster['available'] == []
    assert case_roster(updated, '0002')['available'] == [1, 2]


def test_relation_through_intermediate_sample_is_transitive(store, clean):
    run = execute(store, clean)
    supplement(store, run['id'], {'case': '0001', 'a': 3, 'b': 4})
    updated = supplement(store, run['id'], {'case': '0001', 'a': 2, 'b': 4})

    assert case_roster(updated)['quarantined'] == [1, 2, 3, 4]


def test_same_side_relation_keeps_list_and_review_token_valid(store, clean):
    run = execute(store, clean)
    updated = supplement(store, run['id'], {'case': '0001', 'a': 1, 'b': 2})

    assert updated['revision'] == 0
    assert updated['changed'] is False
    assert case_roster(updated)['available'] == [1, 2, 3, 4]

    approved = review(store, run['id'], {
        'revision': 0, 'status': 'APPROVED', 'note': '同侧补录不改变名单',
    })
    assert approved['status'] == 'APPROVED'
    assert approved['revision'] == 1


def test_changed_roster_rejects_old_review_token_and_preserves_original(store, clean):
    run = execute(store, clean)
    supplement(store, run['id'], {'case': '0001', 'a': 2, 'b': 3})

    with pytest.raises(DomainIssue, match='STALE_REVIEW'):
        review(store, run['id'], {'revision': 0, 'status': 'APPROVED', 'note': '旧名单签发'})

    current = store.load(run['id'])
    approved = review(store, run['id'], {
        'revision': current['revision'], 'status': 'APPROVED', 'note': '按收缩后名单签发',
    })
    assert approved['revision'] == 2
    assert approved['issued_roster']['by_case']['0001']['quarantined'] == [1, 2, 3, 4]
    assert approved['original_roster']['by_case']['0001']['available'] == [1, 2, 3, 4]


def test_supplement_http_and_roster_lookup(client):
    run = client.post('/api/runs', data={'sample': 'clean'}).json
    response = client.post(f"/api/runs/{run['id']}/supplements", json={
        'case': '0001', 'a': 2, 'b': 3,
    })
    assert response.status_code == 200
    assert response.json['quarantined'] == [1, 2, 3, 4]

    roster = client.get(f"/api/runs/{run['id']}/roster")
    assert roster.status_code == 200
    assert roster.json['by_case']['0001']['quarantined'] == [1, 2, 3, 4]
    assert '关系补录与可用名单' in client.get('/').text
