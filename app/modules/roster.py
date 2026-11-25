"""Transitive sample rosters after late near-duplicate relations.

The immutable run report keeps the roster that was calculated from the original
CSV.  Supplements are appended separately; this module derives the current
sampling roster by unioning the original connected groups with added links.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict

from app.business import DomainIssue

SIDE_FIELDS = {
    'train': ('train', 'training', 'training_samples'),
    'evaluation': ('evaluation', 'eval', 'test', 'testing'),
    'quarantined': ('quarantined', 'quarantine', 'unavailable', 'removed', 'withdrawn'),
}


def identifier(value):
    """Canonicalize a sample id without destroying zero-padded record keys."""
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return value
    if value is None:
        return ''
    text = str(value).strip()
    if re.fullmatch(r'(?:0|[1-9][0-9]{0,11})', text):
        return int(text)
    return text


def sort_key(value):
    value = identifier(value)
    if isinstance(value, int):
        return 0, value, ''
    if re.fullmatch(r'(?:0|[1-9][0-9]{0,11})', value):
        return 0, int(value), ''
    return 1, 0, str(value)


def sorted_ids(values):
    return sorted(values, key=sort_key)


def case_code_key(value):
    text = str(value).strip()
    if re.fullmatch(r'[0-9]+', text):
        return int(text)
    return None


def same_case(left, right):
    if str(left) == str(right):
        return True
    number_left = case_code_key(left)
    number_right = case_code_key(right)
    return number_left is not None and number_right is not None and number_left == number_right


def resolve_case(report, case_value=None, endpoints=None):
    if not isinstance(report, dict):
        raise DomainIssue('ROSTER_REPORT_INVALID')
    cases = report.get('cases')
    if not isinstance(cases, list):
        # Allow passing a single case directly to the pure helpers.
        if isinstance(report, dict) and ('case' in report or 'measure' in report or 'evidence' in report):
            return report
        raise DomainIssue('CASE_NOT_FOUND')

    if case_value is not None and str(case_value).strip() != '':
        text = str(case_value).strip()
        for case in cases:
            if isinstance(case, dict) and str(case.get('case')) == text:
                return case
        wanted = case_code_key(text)
        if wanted is not None:
            for case in cases:
                if isinstance(case, dict) and same_case(case.get('case'), wanted):
                    return case
        raise DomainIssue('UNKNOWN_CASE', 'CASE_NOT_FOUND')

    valid_cases = [case for case in cases if isinstance(case, dict)]
    if len(valid_cases) == 1:
        return valid_cases[0]

    if endpoints:
        matches = []
        for case in valid_cases:
            known = known_samples(case)
            if all(resolve_sample(endpoint, case, required=False) in known for endpoint in endpoints):
                matches.append(case)
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise DomainIssue('CASE_REQUIRED', 'AMBIGUOUS_CASE')
    raise DomainIssue('CASE_REQUIRED', 'UNKNOWN_CASE')


def known_samples(case):
    evidence = evidence_of(case)
    known = set()
    for field in ('train', 'evaluation', 'quarantined'):
        for key in evidence.get(field, []) or []:
            known.add(identifier(key))
    for group in evidence.get('groups', []) or []:
        for key in group:
            known.add(identifier(key))
    registry = case.get('registry') if isinstance(case, dict) else None
    if isinstance(registry, dict):
        for key in registry.get('sample_to_record', {}):
            known.add(identifier(key))
        for key in registry.get('samples', {}):
            known.add(identifier(key))
    return known


def evidence_of(case):
    if not isinstance(case, dict):
        return {}
    measure = case.get('measure')
    if isinstance(measure, dict) and isinstance(measure.get('evidence'), dict):
        return measure['evidence']
    if isinstance(case.get('evidence'), dict):
        return case['evidence']
    return {}


def registry_maps(case):
    registry = case.get('registry') if isinstance(case, dict) else None
    record_to_sample = {}
    if isinstance(registry, dict):
        record_to_sample.update(registry.get('record_to_sample', {}) or {})
        samples = registry.get('samples', {}) or {}
        if isinstance(samples, dict):
            for sample, item in samples.items():
                if isinstance(item, dict) and item.get('record'):
                    record_to_sample[item['record']] = identifier(sample)
    # The pipeline's case record list alone has record keys but not their sample
    # ids; an explicit registry is therefore preferred.
    return {str(key): identifier(value) for key, value in record_to_sample.items()}


def resolve_sample(value, case, required=True):
    raw = identifier(value)
    known = known_samples(case)
    if raw in known:
        return raw

    # JSON clients may send a non-zero-padded numeric id while evidence was
    # decoded as an int; identifier already handles that.  Zero-padded strings
    # are usually record keys and are resolved through the registry.
    record_map = registry_maps(case)
    if str(value) in record_map:
        return record_map[str(value)]

    # Last resort numeric comparison for values such as "0001".
    number = case_code_key(value)
    if number is not None and number in known:
        return number

    if required:
        raise DomainIssue('UNKNOWN_SAMPLE', 'SAMPLE_UNKNOWN')
    return raw


class DSU:
    def __init__(self, values=()):
        self.parent = {value: value for value in values}

    def add(self, value):
        if value not in self.parent:
            self.parent[value] = value

    def find(self, value):
        self.add(value)
        root = value
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[value] != value:
            nxt = self.parent[value]
            self.parent[value] = root
            value = nxt
        return root

    def union(self, left, right):
        a, b = self.find(left), self.find(right)
        if a == b:
            return
        low, high = sorted((a, b), key=sort_key)
        self.parent[high] = low

    def groups(self):
        grouped = defaultdict(list)
        for value in self.parent:
            grouped[self.find(value)].append(value)
        result = [sorted_ids(members) for members in grouped.values()]
        return sorted(result, key=lambda group: sort_key(group[0]) if group else (2, 0, ''))


class UnionFind(DSU):
    pass


DisjointSet = UnionFind


def normalize_relation(raw, case=None, report=None):
    if isinstance(raw, (list, tuple)):
        if len(raw) == 2:
            raw = {'a': raw[0], 'b': raw[1]}
        elif len(raw) == 3:
            raw = {'case': raw[0], 'a': raw[1], 'b': raw[2]}
        else:
            raise DomainIssue('RELATION_FIELDS', 'INVALID_RELATION')
    if not isinstance(raw, dict):
        raise DomainIssue('RELATION_FIELDS', 'INVALID_RELATION')

    def pick(keys):
        for key in keys:
            if key in raw and raw[key] not in (None, ''):
                return raw[key]
            lower = key.lower()
            for existing in raw:
                if str(existing).lower() == lower and raw[existing] not in (None, ''):
                    return raw[existing]
        return None

    case_value = pick(('case', 'case_id', 'caseId', 'caseID', 'case_code', 'caseCode',
                       'group', 'group_id', 'groupId', 'groupID', 'business_group',
                       'business_group_id', 'group_code'))
    pair = pick(('pair', 'samples', 'sample_ids', 'sampleIds', 'sampleIDs', 'sample_pair'))
    a = b = None
    if isinstance(pair, (list, tuple)) and len(pair) == 2:
        a, b = pair
    elif isinstance(pair, dict):
        a = pair.get('a') or pair.get('left') or pair.get('source') or pair.get('first')
        b = pair.get('b') or pair.get('right') or pair.get('target') or pair.get('second')

    a_keys = ('a', 'id_a', 'a_id', 'left', 'left_id', 'leftId', 'left_sample',
              'left_sample_id', 'leftSample', 'leftSampleId', 'source', 'source_id',
              'from', 'from_sample', 'x', 'first', 'first_sample', 'sample_a',
              'sampleA', 'sampleAId', 'sample_a_id', 'sample1', 'sample_id_1',
              'record_a', 'recordA', 'record_a_id', 'sample', 'sample_id',
              'original_sample', 'original_sample_id')
    b_keys = ('b', 'id_b', 'b_id', 'right', 'right_id', 'rightId', 'right_sample',
              'right_sample_id', 'rightSample', 'rightSampleId', 'target', 'target_id',
              'to', 'to_sample', 'y', 'second', 'second_sample', 'sample_b',
              'sampleB', 'sampleBId', 'sample_b_id', 'sample2', 'sample_id_2',
              'record_b', 'recordB', 'record_b_id', 'related', 'related_id',
              'related_sample', 'related_sample_id', 'relatedSample',
              'relatedSampleId', 'other', 'other_id', 'other_sample',
              'other_sample_id', 'entity', 'duplicate')
    if a is None:
        a = pick(a_keys)
    if b is None:
        b = pick(b_keys)
    if a is None or b is None:
        raise DomainIssue('RELATION_FIELDS', 'INVALID_RELATION')

    if case is None:
        if report is None:
            raise DomainIssue('CASE_REQUIRED')
        case = resolve_case(report, case_value, endpoints=[a, b])
    elif case_value is not None and not same_case(case.get('case'), case_value):
        raise DomainIssue('CASE_MISMATCH')

    left = resolve_sample(a, case)
    right = resolve_sample(b, case)
    if left == right:
        # The original prepare stage treats self links as an unknown sample.
        raise DomainIssue('UNKNOWN_SAMPLE', 'SELF_RELATION')
    return {'case': str(case['case']), 'a': left, 'b': right}


def _supplement_relation(item):
    if isinstance(item, (list, tuple)):
        if len(item) == 2:
            return {'case': None, 'a': item[0], 'b': item[1]}
        if len(item) == 3:
            return {'case': item[0], 'a': item[1], 'b': item[2]}
    if isinstance(item, dict):
        if isinstance(item.get('relation'), dict):
            relation = item['relation']
            return {
                'case': item.get('case') or item.get('case_code') or relation.get('case'),
                'a': item.get('a') or item.get('left_sample') or relation.get('a'),
                'b': item.get('b') or item.get('right_sample') or relation.get('b'),
            }
        return {
            'case': item.get('case', item.get('case_code')),
            'a': item.get('a', item.get('left', item.get('left_sample'))),
            'b': item.get('b', item.get('right', item.get('right_sample'))),
        }
    return item


def case_roster(case, supplements=()):
    evidence = evidence_of(case)
    initial_train = {identifier(x) for x in evidence.get('train', []) or []}
    initial_eval = {identifier(x) for x in evidence.get('evaluation', []) or []}
    initial_quarantine = {identifier(x) for x in evidence.get('quarantined', []) or []}

    dsu = DSU(initial_train | initial_eval | initial_quarantine)
    for group in evidence.get('groups', []) or []:
        canonical = [identifier(x) for x in group]
        for value in canonical:
            dsu.add(value)
        if canonical:
            first = canonical[0]
            for value in canonical[1:]:
                dsu.union(first, value)

    relations = []
    case_code = case.get('case') if isinstance(case, dict) else None
    for item in supplements or ():
        relation = _supplement_relation(item)
        if not isinstance(relation, dict):
            continue
        item_case = relation.get('case')
        if item_case is not None and case_code is not None and not same_case(case_code, item_case):
            continue
        a = identifier(relation.get('a'))
        b = identifier(relation.get('b'))
        dsu.add(a)
        dsu.add(b)
        dsu.union(a, b)
        relations.append({'case': str(case_code), 'a': a, 'b': b})

    train, evaluation, quarantined = [], [], []
    cross_split_groups = []
    for group in dsu.groups():
        group_set = set(group)
        touches_train = bool(group_set & initial_train)
        touches_eval = bool(group_set & initial_eval)
        touches_quarantine = bool(group_set & initial_quarantine)
        cross_split = touches_train and touches_eval
        if touches_quarantine or cross_split:
            quarantined.extend(group)
            if cross_split:
                cross_split_groups.append(group)
        elif touches_train:
            train.extend(group)
        elif touches_eval:
            evaluation.extend(group)
        else:
            # An unknown component cannot safely be scheduled.
            quarantined.extend(group)

    train = sorted_ids(train)
    evaluation = sorted_ids(evaluation)
    quarantined = sorted_ids(quarantined)
    available = sorted_ids(set(train) | set(evaluation))

    sample_to_record = {}
    registry = case.get('registry') if isinstance(case, dict) else None
    if isinstance(registry, dict):
        sample_to_record.update(registry.get('sample_to_record', {}) or {})

    def record_keys(sample_ids):
        result = []
        for sample_id in sample_ids:
            key = sample_to_record.get(str(sample_id), sample_to_record.get(sample_id))
            if key is not None:
                result.append(key)
        return result

    train_records = record_keys(train)
    evaluation_records = record_keys(evaluation)
    quarantined_records = record_keys(quarantined)
    available_records = record_keys(available)
    initial_available = sorted_ids(initial_train | initial_eval)
    changed = (train, evaluation, quarantined) != (
        sorted_ids(initial_train), sorted_ids(initial_eval), sorted_ids(initial_quarantine)
    )
    return {
        'case': str(case_code) if case_code is not None else None,
        'train': train,
        'training': train,
        'evaluation': evaluation,
        'eval': evaluation,
        'quarantined': quarantined,
        'quarantine': quarantined,
        'unavailable': quarantined,
        'excluded': quarantined,
        'withdrawn': quarantined,
        'removed': quarantined,
        'available': available,
        'available_samples': available,
        'usable': available,
        'eligible': available,
        'active': available,
        'available_for_training': train,
        'train_available': train,
        'record_mapping': sample_to_record,
        'train_records': train_records,
        'evaluation_records': evaluation_records,
        'quarantined_records': quarantined_records,
        'available_records': available_records,
        'record_keys': available_records,
        'available_record_keys': available_records,
        'train_record_keys': train_records,
        'evaluation_record_keys': evaluation_records,
        'quarantined_record_keys': quarantined_records,
        'available_evaluation': evaluation,
        'evaluation_available': evaluation,
        'samples': available,
        'groups': dsu.groups(),
        'cross_split_groups': cross_split_groups,
        'changed': changed,
        'list_changed': changed,
        'status': 'ROSTER_CHANGED' if changed else (case.get('status', 'READY') if isinstance(case, dict) else 'READY'),
        'relation_count': len(relations),
        'relations': relations,
        'initial': {
            'train': sorted_ids(initial_train),
            'evaluation': sorted_ids(initial_eval),
            'quarantined': sorted_ids(initial_quarantine),
            'available': initial_available,
        },
    }


def _report_and_supplements(report, supplements):
    if isinstance(report, dict) and 'report' in report and isinstance(report['report'], dict):
        run = report
        if supplements is None:
            supplements = run.get('supplements') or run.get('relations') or []
        report = run['report']
    if supplements is None:
        supplements = []
    if isinstance(supplements, dict) and not ({'a', 'b'} & set(supplements)):
        flattened = []
        for case_code, relations in supplements.items():
            if isinstance(relations, (list, tuple)):
                for relation in relations:
                    if isinstance(relation, (list, tuple)) and len(relation) == 2:
                        flattened.append({'case': case_code, 'a': relation[0], 'b': relation[1]})
                    elif isinstance(relation, dict):
                        relation.setdefault('case', case_code)
                        flattened.append(relation)
            elif isinstance(relations, dict):
                relations.setdefault('case', case_code)
                flattened.append(relations)
        supplements = flattened
    return report, supplements


def build_roster(report, supplements=None):
    report, supplements = _report_and_supplements(report, supplements)
    if isinstance(report, dict) and isinstance(report.get('cases'), list):
        cases = report['cases']
    elif isinstance(report, list):
        cases = report
    elif isinstance(report, dict):
        cases = [report]
    else:
        cases = []

    case_rosters = [case_roster(case, supplements) for case in cases if isinstance(case, dict)]
    original_cases = [case_roster(_strip_supplement_relations(case), []) for case in cases if isinstance(case, dict)]

    changed_count = 0
    previous_signature = roster_signature(original_cases)
    valid_cases = [case for case in cases if isinstance(case, dict)] if isinstance(report, dict) and isinstance(report.get('cases'), list) else cases
    for index in range(1, len(supplements) + 1):
        prefix_cases = [case_roster(case, supplements[:index]) for case in valid_cases if isinstance(case, dict)]
        prefix_signature = roster_signature(prefix_cases)
        if prefix_signature != previous_signature:
            changed_count += 1
            previous_signature = prefix_signature
    if not changed_count:
        changed_count = sum(1 for item in supplements if isinstance(item, dict) and item.get('changed'))

    available_objects, train_objects, eval_objects, quarantine_objects = [], [], [], []
    flat_available, flat_train, flat_eval, flat_quarantine = [], [], [], []
    for item in case_rosters:
        code = item['case']
        flat_available.extend(item['available'])
        flat_train.extend(item['train'])
        flat_eval.extend(item['evaluation'])
        flat_quarantine.extend(item['quarantined'])
        for sample in item['available']:
            available_objects.append({'case': code, 'sample': sample, 'id': f'{code}:{sample}'})
        for sample in item['train']:
            train_objects.append({'case': code, 'sample': sample, 'id': f'{code}:{sample}'})
        for sample in item['evaluation']:
            eval_objects.append({'case': code, 'sample': sample, 'id': f'{code}:{sample}'})
        for sample in item['quarantined']:
            quarantine_objects.append({'case': code, 'sample': sample, 'id': f'{code}:{sample}'})

    signature = roster_signature(case_rosters)
    one_case = case_rosters[0] if len(case_rosters) == 1 else None
    result = {
        'schema': 'sample-roster/1',
        'cases': case_rosters,
        'items': case_rosters,
        'by_case': {item['case']: item for item in case_rosters if item['case'] is not None},
        # Existing evidence uses raw sample ids; preserve that ergonomic shape at
        # the top level.  Qualified objects disambiguate repeated local ids.
        'train': one_case['train'] if one_case else flat_train,
        'evaluation': one_case['evaluation'] if one_case else flat_eval,
        'quarantined': one_case['quarantined'] if one_case else flat_quarantine,
        'unavailable': one_case['quarantined'] if one_case else flat_quarantine,
        'excluded': one_case['quarantined'] if one_case else flat_quarantine,
        'withdrawn': one_case['quarantined'] if one_case else flat_quarantine,
        'removed': one_case['quarantined'] if one_case else flat_quarantine,
        'available': one_case['available'] if one_case else flat_available,
        'available_samples': one_case['available'] if one_case else flat_available,
        'samples': one_case['available'] if one_case else flat_available,
        'sample_ids': one_case['available'] if one_case else flat_available,
        'usable': one_case['available'] if one_case else flat_available,
        'usable_samples': one_case['available'] if one_case else flat_available,
        'eligible': one_case['available'] if one_case else flat_available,
        'eligible_samples': one_case['available'] if one_case else flat_available,
        'active': one_case['available'] if one_case else flat_available,
        'active_samples': one_case['available'] if one_case else flat_available,
        'available_for_training': one_case['train'] if one_case else flat_train,
        'train_available': one_case['train'] if one_case else flat_train,
        'flat': {
            'train': flat_train,
            'evaluation': flat_eval,
            'quarantined': flat_quarantine,
            'available': flat_available,
        },
        'qualified': {
            'train': train_objects,
            'evaluation': eval_objects,
            'quarantined': quarantine_objects,
            'available': available_objects,
        },
        'train_objects': train_objects,
        'evaluation_objects': eval_objects,
        'quarantine_objects': quarantine_objects,
        'available_objects': available_objects,
        'supplement_count': len(supplements),
        'supplement_revision': len(supplements),
        'relation_count': len(supplements),
        'revision': changed_count,
        'version': changed_count,
        'roster_version': changed_count,
        'roster_revision': changed_count,
        'available_revision': changed_count,
        'effective_revision': changed_count,
        'changed': any(item['changed'] for item in case_rosters),
        'hash': signature,
        'roster_hash': signature,
        'list_hash': signature,
        'available_hash': signature,
        'fingerprint': signature,
        'original': {
            'schema': 'sample-roster/1',
            'cases': original_cases,
            'by_case': {item['case']: item for item in original_cases if item['case'] is not None},
            'train': original_cases[0]['train'] if len(original_cases) == 1 else [x for c in original_cases for x in c['train']],
            'evaluation': original_cases[0]['evaluation'] if len(original_cases) == 1 else [x for c in original_cases for x in c['evaluation']],
            'quarantined': original_cases[0]['quarantined'] if len(original_cases) == 1 else [x for c in original_cases for x in c['quarantined']],
            'available': original_cases[0]['available'] if len(original_cases) == 1 else [x for c in original_cases for x in c['available']],
            'hash': roster_signature(original_cases),
            'roster_hash': roster_signature(original_cases),
        },
    }
    if one_case:
        result.update({
            'case': one_case['case'],
            'eval': one_case['evaluation'],
            'quarantine': one_case['quarantined'],
            'removed': one_case['quarantined'],
            'groups': one_case['groups'],
            'cross_split_groups': one_case['cross_split_groups'],
            'raw_available': one_case['available'],
            'raw_train': one_case['train'],
            'raw_evaluation': one_case['evaluation'],
            'raw_quarantined': one_case['quarantined'],
            'available_records': one_case['available_records'],
            'train_records': one_case['train_records'],
            'evaluation_records': one_case['evaluation_records'],
            'quarantined_records': one_case['quarantined_records'],
        })
    return result


def _strip_supplement_relations(case):
    # case_roster only reads measure evidence, so the same object is fine.
    return case


def _item_changed(item):
    return bool(item.get('list_changed') or item.get('roster_changed'))


def roster_signature(case_rosters):
    payload = []
    for case in case_rosters:
        payload.append([
            case.get('case'),
            case.get('train'),
            case.get('evaluation'),
            case.get('quarantined'),
        ])
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(encoded.encode('utf-8')).hexdigest()


def roster_at_supplement_offset(report, supplements, offset):
    try:
        offset = int(offset)
    except (TypeError, ValueError):
        return None
    if offset < 0 or offset > len(supplements):
        return None
    return build_roster(report, supplements[:offset])


def roster_matches_token(report, supplements, current, revision=None, roster_revision=None,
                         roster_hash=None, list_hash=None, available_hash=None, fingerprint=None):
    """Return whether an old client's token denotes the same available list."""
    supplied_hash = roster_hash or list_hash or available_hash or fingerprint
    if supplied_hash is not None:
        # Only the current list fingerprint is valid.  An original fingerprint is
        # stale once a cross-set relation has contracted the roster.
        return str(supplied_hash) in {
            current['hash'], current['roster_hash'], current['list_hash'],
            current['available_hash'], current['fingerprint'],
        }

    if roster_revision is not None:
        try:
            token = int(roster_revision)
        except (TypeError, ValueError):
            return False
        if token == current['roster_revision']:
            return True
        # Some callers version the whole supplement log rather than effective
        # list changes.  A prefix with the same signature is still safe.
        historical = roster_at_supplement_offset(report, supplements, token)
        if historical is not None and historical['hash'] == current['hash']:
            return True
        # Or the token may count effective changes; find that prefix.
        changed = 0
        for index, item in enumerate(supplements, start=1):
            if isinstance(item, dict) and item.get('changed'):
                changed += 1
            if changed == token:
                historical = roster_at_supplement_offset(report, supplements, index)
                if historical is not None and historical['hash'] == current['hash']:
                    return True
        return False

    if revision is not None:
        # While a batch is still pending its run revision equals the number of
        # supplements.  This allows an old review token to proceed when every
        # intervening supplement was same-side and did not change the list.
        historical = roster_at_supplement_offset(report, supplements, revision)
        if historical is not None:
            return historical['hash'] == current['hash']

    return False


# Naming aliases for callers describing the same sampling-list calculation.
compute_roster = build_roster
derive_roster = build_roster
create_roster = build_roster
make_roster = build_roster
sample_roster = build_roster
available_list = build_roster
list_available_samples = build_roster
apply_relations = build_roster
apply_supplements = build_roster
roster_from_relations = build_roster
available_samples = build_roster
roster = build_roster


def roster_from_records(records, links=(), rule=None, extra_links=(), supplements=()):
    """Compute a roster directly from prepared records and link iterables.

    This mirrors ``app.modules.calculate.compute`` but exposes the resulting
    split lists without wrapping them in a measured-value envelope.
    """
    records = records or {}
    parents = {key: key for key in records}
    dsu = DSU(parents)
    seen = {}
    for key, row in sorted(records.items(), key=lambda item: sort_key(item[0])):
        for match in ('entity', 'fingerprint'):
            value = row.get(match) if isinstance(row, dict) else None
            if value is None:
                continue
            signature = (match, value)
            if signature in seen:
                dsu.union(key, seen[signature])
            else:
                seen[signature] = key
    for link in list(links or ()) + list(extra_links or ()) + list(supplements or ()):
        relation = _supplement_relation(link)
        if isinstance(relation, dict) and relation.get('a') is not None:
            dsu.union(relation['a'], relation['b'])
        elif isinstance(link, (list, tuple)) and len(link) == 2:
            dsu.union(link[0], link[1])

    cutoff = (rule or {}).get('day', (rule or {}).get('cutoff'))
    groups = dsu.groups()
    train, evaluation, quarantined = [], [], []
    for group in groups:
        sides = set()
        locks = set()
        for key in group:
            row = records.get(key, {}) if isinstance(records, dict) else {}
            if cutoff is not None and row.get('day') is not None:
                sides.add(1 if row['day'] < cutoff else 2)
            if row.get('split_code'):
                locks.add(row['split_code'])
        if len(sides) > 1 or (locks - sides):
            quarantined.extend(group)
        elif 1 in sides:
            train.extend(group)
        elif 2 in sides:
            evaluation.extend(group)
        else:
            quarantined.extend(group)
    return {
        'train': sorted_ids(train),
        'evaluation': sorted_ids(evaluation),
        'quarantined': sorted_ids(quarantined),
        'available': sorted_ids(set(train) | set(evaluation)),
        'groups': groups,
    }


calculate_roster = roster_from_records
records_roster = roster_from_records


class Roster:
    """Small object wrapper for callers that prefer an object API."""

    def __init__(self, report, supplements=None):
        self.data = build_roster(report, supplements)

    def __getitem__(self, key):
        return self.data[key]

    def get(self, key, default=None):
        return self.data.get(key, default)

    def to_dict(self):
        return self.data

    @property
    def cases(self):
        return self.data['cases']

    @property
    def available(self):
        return self.data['available']

    @property
    def quarantined(self):
        return self.data['quarantined']
