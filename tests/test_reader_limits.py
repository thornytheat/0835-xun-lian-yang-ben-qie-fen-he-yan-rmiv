import io

from app.config import MAX_FILE
from app.intake.schema import HEADER
from conftest import csv_data


def test_oversize_stream(client):
    response=client.post('/api/runs',data={'file':(io.BytesIO(b'x'*(MAX_FILE+1)),'big.csv')})
    assert response.status_code==413 and response.json['code']=='FILE_TOO_LARGE'


def test_record_limit(client):
    sample=csv_data([['']*len(HEADER)]*2001)
    response=client.post('/api/runs',data={'file':(io.BytesIO(sample),'rows.csv')})
    assert response.status_code==422 and response.json['code']=='ROW_LIMIT'


def test_invalid_encoding(client):
    response=client.post('/api/runs',data={'file':(io.BytesIO(b'\xff'),'bad.csv')})
    assert response.status_code==422 and response.json['code']=='ENCODING_INVALID'
