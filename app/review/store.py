import json
import sqlite3
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path

from app.business import DomainIssue
from app.modules.roster import build_roster

SCHEMA = '''CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY, report TEXT NOT NULL, created TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING', revision INTEGER NOT NULL DEFAULT 0,
    note TEXT NOT NULL DEFAULT '', reviewed TEXT
);'''

SUPPLEMENTS_SCHEMA = '''CREATE TABLE IF NOT EXISTS supplements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    case_code TEXT,
    left_sample TEXT NOT NULL,
    right_sample TEXT NOT NULL,
    changed INTEGER NOT NULL DEFAULT 0,
    payload TEXT NOT NULL,
    roster TEXT NOT NULL DEFAULT '{}',
    created TEXT NOT NULL,
    UNIQUE(run_id, seq)
);'''

ISSUED_SCHEMA = '''CREATE TABLE IF NOT EXISTS issued_rosters (
    run_id TEXT PRIMARY KEY,
    revision INTEGER NOT NULL,
    roster TEXT NOT NULL,
    created TEXT NOT NULL
);'''


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds')


class Store:
    def __init__(self, path):
        self.path = Path(path)

    def initialize(self, db):
        db.row_factory = sqlite3.Row
        db.execute(SCHEMA)
        db.execute(SUPPLEMENTS_SCHEMA)
        db.execute(ISSUED_SCHEMA)

    @contextmanager
    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path, timeout=15)) as db, db:
            self.initialize(db)
            yield db

    @contextmanager
    def write(self):
        """Serialize all read-modify-write batch operations."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=15)
        try:
            db.row_factory = sqlite3.Row
            db.execute('BEGIN IMMEDIATE')
            self.initialize(db)
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def register(self, run_id, report, meta=None):
        with self.connect() as db:
            db.execute('INSERT INTO runs(id,report,created) VALUES (?,?,?) ON CONFLICT(id) DO NOTHING',
                       (run_id, json.dumps(report, ensure_ascii=False), report['manifest']['created']))
        return self.load(run_id)

    def _supplements(self, db, run_id):
        rows = db.execute('SELECT * FROM supplements WHERE run_id=? ORDER BY seq,id', (run_id,)).fetchall()
        items = []
        for row in rows:
            item = dict(row)
            payload = {}
            try:
                payload = json.loads(item.pop('payload', '{}') or '{}')
            except (TypeError, json.JSONDecodeError):
                payload = {}
            roster_snapshot = item.pop('roster', '{}')
            item['roster_snapshot'] = json.loads(roster_snapshot or '{}')
            # Payload carries the normalized relation under stable names.
            if isinstance(payload, dict):
                item.update({k: v for k, v in payload.items() if k not in item or item[k] in (None, '')})
            item.setdefault('case', item.get('case_code'))
            item.setdefault('case_id', item.get('case_code'))
            item.setdefault('a', item.get('left_sample'))
            item.setdefault('b', item.get('right_sample'))
            item.setdefault('left', item.get('left_sample'))
            item.setdefault('right', item.get('right_sample'))
            item.setdefault('seq', item.get('seq'))
            items.append(item)
        return items

    def supplements(self, run_id):
        with self.connect() as db:
            if db.execute('SELECT 1 FROM runs WHERE id=?', (run_id,)).fetchone() is None:
                raise DomainIssue('RUN_NOT_FOUND')
            return self._supplements(db, run_id)

    # Common naming alias.
    relations = supplements

    def load(self, run_id):
        with self.connect() as db:
            row = db.execute('SELECT * FROM runs WHERE id=?', (run_id,)).fetchone()
            if row is None:
                raise DomainIssue('RUN_NOT_FOUND')
            result = dict(row)
            result['report'] = json.loads(result['report'])
            result['supplements'] = self._supplements(db, run_id)
            result['relations'] = result['supplements']
            issued_row = db.execute('SELECT roster, revision AS issued_revision, created AS issued_at FROM issued_rosters WHERE run_id=?', (run_id,)).fetchone()

        roster = build_roster(result['report'], result['supplements'])
        result['roster'] = roster
        result['current_roster'] = roster
        result['available_roster'] = roster
        result['roster_view'] = roster
        result['original_roster'] = roster['original']
        result['original_list'] = roster['original']
        result['initial_roster'] = roster['original']
        result['roster_revision'] = roster['roster_revision']
        result['supplement_revision'] = len(result['supplements'])
        result['available'] = roster['available']
        result['available_samples'] = roster['available_samples']
        result['samples'] = roster.get('samples', roster['available_samples'])

        if issued_row is not None:
            issued = json.loads(issued_row['roster'])
            issued['issued_revision'] = issued_row['issued_revision']
            issued['approved_revision'] = issued_row['issued_revision']
            issued['issued_at'] = issued_row['issued_at']
            result['issued_roster'] = issued
            result['approved_roster'] = issued
            result['issued_list'] = issued
            result['approved_list'] = issued
            result['signed_roster'] = issued
            result['signed_list'] = issued
            result['issued'] = issued
        elif result['status'] == 'APPROVED':
            # Backwards compatibility for rows finalized directly through
            # Store.revise or older databases without an issued snapshot.
            issued = roster['original']
            issued['issued_revision'] = result['revision']
            issued['approved_revision'] = result['revision']
            result['issued_roster'] = issued
            result['approved_roster'] = issued
            result['issued_list'] = issued
            result['approved_list'] = issued
            result['signed_roster'] = issued
            result['signed_list'] = issued
            result['issued'] = issued
        return result

    def list(self):
        with self.connect() as db:
            return [dict(r) for r in db.execute('SELECT id,created,status,revision,note FROM runs ORDER BY created DESC,id LIMIT 50')]

    def get_roster(self, run_id):
        return self.load(run_id)['roster']

    def available_roster(self, run_id):
        return self.load(run_id)['roster']

    def revise(self, run_id, revision, status, note, now, issued_roster=None):
        with self.write() as db:
            cursor = db.execute('UPDATE runs SET status=?,note=?,reviewed=?,revision=revision+1 WHERE id=? AND revision=?',
                                (status, note, now, run_id, revision))
            if cursor.rowcount != 1:
                raise DomainIssue('STALE_REVIEW')
            if status == 'APPROVED':
                # Always derive inside the write transaction so the signed list
                # includes every relation that committed before approval, even
                # when a same-side supplement did not change the sample lists.
                row = db.execute('SELECT report FROM runs WHERE id=?', (run_id,)).fetchone()
                report = json.loads(row['report'])
                supplements = self._supplements(db, run_id)
                issued = build_roster(report, supplements)
                db.execute(
                    '''INSERT INTO issued_rosters(run_id,revision,roster,created)
                       VALUES (?,?,?,?)
                       ON CONFLICT(run_id) DO UPDATE SET
                         revision=excluded.revision, roster=excluded.roster, created=excluded.created''',
                    (run_id, revision + 1, json.dumps(issued, ensure_ascii=False, sort_keys=True), now),
                )
        return self.load(run_id)

    def add_supplements(self, run_id, relations, now=None):
        now = now or utc_now()
        if not relations:
            return self.load(run_id)
        with self.write() as db:
            row = db.execute('SELECT report FROM runs WHERE id=?', (run_id,)).fetchone()
            if row is None:
                raise DomainIssue('RUN_NOT_FOUND')
            report = json.loads(row['report'])
            existing = self._supplements(db, run_id)
            start_seq = len(existing)
            previous_roster = build_roster(report, existing)
            previous_signature = previous_roster['hash']
            revision_delta = 0

            for offset, relation in enumerate(relations, start=1):
                seq = start_seq + offset
                candidate_items = existing + [
                    {'case': relation['case'], 'a': relation['a'], 'b': relation['b']}
                    for relation in relations[:offset]
                ]
                candidate = build_roster(report, candidate_items)
                changed = 1 if candidate['hash'] != previous_signature else 0
                # The signature is cumulative; compare each step to the prior
                # step's signature for the row's own changed flag.
                if offset > 1:
                    prior = build_roster(report, existing + [
                        {'case': item['case'], 'a': item['a'], 'b': item['b']}
                        for item in relations[:offset - 1]
                    ])
                    changed = 1 if candidate['hash'] != prior['hash'] else 0
                else:
                    changed = 1 if candidate['hash'] != previous_signature else 0
                revision_delta += changed
                payload = dict(relation)
                payload.update(left=relation['a'], right=relation['b'],
                               sample_a=relation['a'], sample_b=relation['b'])
                db.execute(
                    '''INSERT INTO supplements(
                           run_id,seq,case_code,left_sample,right_sample,changed,payload,roster,created)
                       VALUES (?,?,?,?,?,?,?,?,?)''',
                    (run_id, seq, relation.get('case'), str(relation['a']), str(relation['b']),
                     changed, json.dumps(payload, ensure_ascii=False, sort_keys=True),
                     json.dumps({k: candidate[k] for k in ('hash', 'cases', 'roster_revision')},
                               ensure_ascii=False, sort_keys=True),
                     now),
                )
            # Only an available-list change invalidates the outstanding review
            # token.  Same-side links are still recorded/audited but leave the
            # revision at the value held by the pending reviewer.
            if revision_delta:
                db.execute('UPDATE runs SET revision=revision+? WHERE id=?', (revision_delta, run_id))
        return self.load(run_id)

    def add_supplement(self, run_id, relation=None, now=None, **kwargs):
        if relation is None:
            relation = kwargs
        if isinstance(relation, list):
            return self.add_supplements(run_id, relation, now=now)
        return self.add_supplements(run_id, [relation], now=now)

    # Intentional naming aliases for callers describing late links.
    def add_relation(self, run_id, relation=None, b=None, *args, **kwargs):
        if relation is not None and b is not None and not isinstance(relation, (dict, list)):
            if args:
                # add_relation(run_id, case, sample_a, sample_b)
                raw = {'case': relation, 'a': b, 'b': args[0]}
            else:
                # add_relation(run_id, sample_a, sample_b)
                raw = {'a': relation, 'b': b}
        elif relation is None:
            raw = kwargs
        else:
            raw = relation
        return self.add_supplement(run_id, raw, now=kwargs.get('now'))

    def append_relation(self, run_id, *args, **kwargs):
        return self.add_relation(run_id, *args, **kwargs)

    def record_relation(self, run_id, *args, **kwargs):
        return self.add_relation(run_id, *args, **kwargs)

    # Additional method-name aliases.
    supplement = add_supplement
    supplement_relation = add_supplement
    supplement_relations = add_supplements
    create_supplement = add_supplement
    record_supplement = add_supplement
    append_supplement = add_supplement
    create_relation = add_relation
    add_relations = add_supplements
    add_link = add_relation
    add_links = add_supplements
