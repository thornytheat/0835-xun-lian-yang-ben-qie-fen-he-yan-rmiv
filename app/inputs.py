from flask import request

from app.business import DomainIssue
from app.config import MAX_FILE, ROOT

SAMPLES = {'dirty': 'incoming.csv', 'clean': 'ready.csv'}


def read_input():
    sample = request.form.get('sample')
    if sample is not None:
        if sample not in SAMPLES:
            raise DomainIssue('SAMPLE_UNKNOWN')
        return (ROOT/'sample_data'/SAMPLES[sample]).read_bytes()
    uploaded = request.files.get('file')
    if uploaded is None or not uploaded.filename:
        raise DomainIssue('FILE_REQUIRED')
    value = uploaded.stream.read(MAX_FILE+1)
    if len(value)>MAX_FILE:
        raise DomainIssue('FILE_TOO_LARGE')
    return value
