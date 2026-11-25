import io

import pytest


@pytest.mark.parametrize('stage',['intake','prepare','calculate','policy','balance'])
def test_stage_has_http_entry_and_no_database_write(client,stage):
    response=client.post('/api/stages/'+stage,data={'sample':'dirty'})
    assert response.status_code==200 and response.json['intake']['rejected']==5
    assert client.get('/api/runs').json=={'items':[]}


def test_upload_uses_input_content(client,clean):
    a=client.post('/api/runs',data={'file':(io.BytesIO(clean),'input.csv')})
    b=client.post('/api/runs',data={'sample':'clean'})
    assert a.status_code==200 and a.json['id']==b.json['id']


def test_unknown_stage_and_sample(client):
    assert client.post('/api/stages/unknown',data={'sample':'clean'}).status_code==404
    assert client.post('/api/runs',data={'sample':'unknown'}).status_code==404


def test_bad_upload_leaves_history_empty(client):
    result=client.post('/api/runs',data={'file':(io.BytesIO(b'wrong,header\n'),'bad.csv')})
    assert result.status_code==422 and result.json['code']=='HEADER_MISMATCH'
    assert client.get('/api/runs').json['items']==[]
