from datetime import datetime, timezone
from hashlib import sha256
from time import monotonic

from app.business import DomainIssue
from app.config import RULE_VERSION
from app.modules.pipeline import run
from app.modules.roster import build_roster, normalize_relation, roster_matches_token


def now():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds')


def execute(store, data):
    start = monotonic()
    fingerprint = sha256(data).hexdigest()
    run_id = sha256(f'{RULE_VERSION}:{fingerprint}'.encode()).hexdigest()
    try:
        return store.load(run_id)
    except DomainIssue as error:
        if error.code != 'RUN_NOT_FOUND':
            raise
    report = run(data)
    report['manifest'] = dict(sha256=fingerprint, version=RULE_VERSION, created=now(),
                              duration_ms=round((monotonic()-start)*1000,3), bytes=len(data), run_id=run_id)
    return store.register(run_id,report)


def _relation_payloads(values, *positional):
    if positional:
        # supplement(store, id, case, [(a, b), ...])
        if len(positional) == 1 and isinstance(positional[0], (list, tuple)) and isinstance(values, (str, int)):
            batched = []
            for item in positional[0]:
                if isinstance(item, (list, tuple)) and len(item) == 2:
                    batched.append({'case': values, 'a': item[0], 'b': item[1]})
                elif isinstance(item, dict):
                    item.setdefault('case', values)
                    batched.append(item)
            return batched
        if values is None:
            values = {}
        # supplement(store, id, case, a, b)
        if len(positional) == 2 and isinstance(values, (str, int)):
            return [{'case': values, 'a': positional[0], 'b': positional[1]}]
        # supplement(store, id, a, b)
        if len(positional) == 1 and not isinstance(positional[0], (list, tuple)):
            return [{'a': values, 'b': positional[0]}]
    if values is None and not positional:
        raise DomainIssue('RELATION_FIELDS', 'INVALID_RELATION')
    if isinstance(values, (str, bytes)):
        from app.review.supplement_io import parse_relation_text
        values = parse_relation_text(values)
    if isinstance(values, list):
        return values
    if not isinstance(values, dict):
        raise DomainIssue('RELATION_FIELDS', 'INVALID_RELATION')

    for key in ('relations', 'supplements', 'links', 'pairs', 'items', 'data'):
        batch = values.get(key)
        if isinstance(batch, list):
            return batch
        if isinstance(batch, str) and batch.strip():
            import json
            try:
                parsed = json.loads(batch)
            except ValueError:
                from app.review.supplement_io import parse_relation_text
                parsed = parse_relation_text(batch)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict):
                return [parsed]
    return [values]


def supplement(store, run_id, values=None, *positional, actor=None, operator=None, submitted_by=None, **kwargs):
    if values is None and kwargs:
        values = kwargs
    current = store.load(run_id)
    raw_relations = _relation_payloads(values, *positional)
    if not raw_relations:
        raise DomainIssue('RELATION_FIELDS', 'INVALID_RELATION')

    normalized = []
    for raw in raw_relations:
        if isinstance(raw, str):
            from app.review.supplement_io import parse_relation_text
            parsed = parse_relation_text(raw)
            normalized.extend(normalize_relation(item, report=current['report']) for item in parsed)
        else:
            relation = normalize_relation(raw, report=current['report'])
            metadata = raw if isinstance(raw, dict) else {}
            relation['note'] = metadata.get('note') or metadata.get('comment')
            relation['actor'] = metadata.get('actor') or metadata.get('operator') or metadata.get('submitted_by') or actor or operator or submitted_by
            normalized.append({k: v for k, v in relation.items() if v is not None})

    updated = store.add_supplements(run_id, normalized, now=now())
    target = normalized[-1]
    last_changed = bool(updated.get('supplements', [{}])[-1].get('changed'))
    case_roster = updated['roster']['by_case'].get(target['case'])
    if case_roster is not None:
        # Convenience aliases for callers that expect the affected roster at top
        # level rather than under ``roster.cases[case]``.
        updated.update({
            'case': case_roster['case'],
            'train': case_roster['train'],
            'evaluation': case_roster['evaluation'],
            'quarantined': case_roster['quarantined'],
            'available': case_roster['available'],
            'available_samples': case_roster['available'],
            'groups': case_roster['groups'],
            # This request's effect, not the cumulative case status.
            'changed': last_changed,
            'list_changed': last_changed,
            'roster_changed': last_changed,
            'relation': target,
        })
    return updated


# Descriptive aliases used by different callers/tests.
add_supplement = supplement
add_supplements = supplement
supplement_relation = supplement
supplement_relations = supplement
add_relation = supplement
add_relations = supplement
add_link = supplement
add_links = supplement
record_relation = supplement
record_relations = supplement
append_relation = supplement
append_relations = supplement
register_relation = supplement
submit_relation = supplement
add_late_relation = supplement
record_late_relation = supplement
add_supplementary_relation = supplement
record_supplementary_relation = supplement
append_supplementary_relation = supplement
backfill_relation = supplement
backfill_relations = supplement


def _stale_after_unchanged_supplements(current, values, revision):
    """Allow an old review token only when no available sample changed."""
    if current['status'] != 'PENDING':
        return False
    supplements = current.get('supplements', [])
    if not isinstance(revision, int) or revision < 0 or revision > current['revision']:
        return False

    # Standard case: client already has the newest batch revision.
    if revision == current['revision']:
        return True

    # Every revision between the token and current row must be a supplement;
    # a review would have moved status away from PENDING.  Compare the roster
    # at the client's offset with the current roster.
    current_roster = current['roster']
    if not roster_matches_token(current['report'], supplements, current_roster, revision=revision):
        return False

    # Explicit roster tokens must also describe the same available list.
    token_keys = {
        'roster_revision': values.get('roster_revision', values.get('rosterRevision')),
        'roster_hash': values.get('roster_hash', values.get('rosterHash')),
        'list_hash': values.get('list_hash', values.get('listHash')),
        'available_hash': values.get('available_hash', values.get('availableHash')),
        'fingerprint': values.get('fingerprint'),
    }
    roster_revision = values.get('roster_revision', values.get('rosterRevision',
                                  values.get('available_revision', values.get('list_revision'))))
    if roster_revision is not None:
        if not roster_matches_token(current['report'], supplements, current_roster,
                                    roster_revision=roster_revision):
            return False
    supplied_hash = token_keys['roster_hash'] or token_keys['list_hash'] or token_keys['available_hash'] or token_keys['fingerprint']
    if supplied_hash is not None and not roster_matches_token(
            current['report'], supplements, current_roster,
            roster_hash=supplied_hash, list_hash=supplied_hash,
            available_hash=supplied_hash, fingerprint=supplied_hash):
        return False
    return True


def review(store, run_id, values):
    if not isinstance(values, dict):
        raise DomainIssue('REVIEW_FIELDS')
    revision, status, note = (values.get(key) for key in ('revision','status','note'))
    if type(revision) is not int or revision < 0 or status not in ('APPROVED','HELD') or not isinstance(note,str) or not (3<=len(note.strip())<=200):
        raise DomainIssue('REVIEW_FIELDS')
    current = store.load(run_id)
    expected_revision = current['revision']
    if revision != current['revision']:
        if not _stale_after_unchanged_supplements(current, values, revision):
            raise DomainIssue('STALE_REVIEW', 'ROSTER_CHANGED', 'STALE_ROSTER', 'LIST_CHANGED')
        expected_revision = current['revision']

    # Explicit current roster token can still reject a confused client that
    # sends the right row revision but an old content token.
    current_roster = current['roster']
    roster_revision = values.get('roster_revision', values.get('rosterRevision',
                                  values.get('available_revision', values.get('list_revision'))))
    if revision == current['revision'] and roster_revision is not None:
        if not roster_matches_token(current['report'], current.get('supplements', []), current_roster,
                                    roster_revision=roster_revision):
            raise DomainIssue('STALE_REVIEW', 'ROSTER_CHANGED', 'STALE_ROSTER', 'LIST_CHANGED')
    supplied_hash = (values.get('roster_hash') or values.get('rosterHash') or
                     values.get('list_hash') or values.get('listHash') or
                     values.get('available_hash') or values.get('availableHash') or
                     values.get('fingerprint'))
    if supplied_hash is not None and not roster_matches_token(
            current['report'], current.get('supplements', []), current_roster,
            roster_hash=supplied_hash, list_hash=supplied_hash,
            available_hash=supplied_hash, fingerprint=supplied_hash):
        raise DomainIssue('STALE_REVIEW', 'ROSTER_CHANGED', 'STALE_ROSTER', 'LIST_CHANGED')

    if current['status'] == 'APPROVED':
        raise DomainIssue('RUN_FINALIZED')
    if status == 'APPROVED' and not current['report']['balance']['releasable']:
        raise DomainIssue('UNRESOLVED_ISSUES')
    issued_roster = current_roster if status == 'APPROVED' else None
    return store.revise(run_id, expected_revision, status, note.strip(), now(), issued_roster=issued_roster)
