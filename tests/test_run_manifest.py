from datetime import datetime, timezone
from hashlib import sha256

from app.config import RULE_VERSION
from app.review.service import execute


def test_manifest_records_source_and_rule(store, dirty):
    run = execute(store, dirty)
    manifest = run['report']['manifest']
    assert manifest['run_id'] == run['id']
    assert manifest['version'] == RULE_VERSION
    assert manifest['bytes'] == len(dirty)
    assert manifest['sha256'] == sha256(dirty).hexdigest()
    assert manifest['duration_ms'] >= 0
    assert datetime.fromisoformat(manifest['created']).tzinfo == timezone.utc
