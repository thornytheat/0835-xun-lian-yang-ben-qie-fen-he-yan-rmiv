import csv
import io
from pathlib import Path

import pytest

from app.intake.schema import HEADER
from app.main import create_app
from app.review.store import Store

ROOT = Path(__file__).resolve().parents[1]


def csv_data(records):
    stream = io.StringIO(newline='')
    csv.writer(stream).writerows([HEADER,*records])
    return stream.getvalue().encode()


@pytest.fixture
def dirty():
    return (ROOT/'sample_data'/'incoming.csv').read_bytes()


@pytest.fixture
def clean():
    return (ROOT/'sample_data'/'ready.csv').read_bytes()


@pytest.fixture
def client(tmp_path):
    return create_app(tmp_path/'runs.db').test_client()


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path/'runs.db')
