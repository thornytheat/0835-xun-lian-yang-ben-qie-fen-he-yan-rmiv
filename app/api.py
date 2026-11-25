from flask import Blueprint, Response, current_app, jsonify, request

from app.business import DomainIssue
from app.evidence.render import artifact
from app.inputs import read_input
from app.modules.pipeline import run
from app.review.service import execute, review, supplement
from app.review.supplement_io import parse_relation_text

api = Blueprint('api',__name__,url_prefix='/api')
STAGES = {'intake':1,'prepare':2,'calculate':3,'policy':4,'balance':5}


@api.post('/stages/<stage>')
def preview(stage):
    if stage not in STAGES:
        raise DomainIssue('STAGE_UNKNOWN')
    return jsonify(run(read_input(),STAGES[stage]))


@api.route('/runs',methods=['GET','POST'])
def runs():
    store = current_app.extensions['runs']
    if request.method == 'GET':
        return jsonify(items=store.list())
    return jsonify(execute(store,read_input()))


def looks_like_relation_request(payload):
    if not isinstance(payload, dict):
        return False
    if payload.get('action') in {'supplement', 'add_relation', 'add_link', 'relation', 'link'}:
        return True
    relation_keys = ('relation', 'relations', 'supplement', 'supplements', 'link', 'links',
                    'duplicate', 'duplicates', 'pairs')
    if any(key in payload for key in relation_keys):
        return True
    return any(key in payload for key in ('a', 'left', 'source', 'sample_a', 'left_sample')) and \
           any(key in payload for key in ('b', 'right', 'target', 'sample_b', 'right_sample', 'entity'))


@api.route('/runs/<run_id>', methods=['GET', 'POST', 'PATCH'])
def batch(run_id):
    store = current_app.extensions['runs']
    if request.method == 'GET':
        return jsonify(store.load(run_id))
    payload = request.get_json(silent=True)
    if payload is None and request.form:
        payload = relation_payload()
    # Also allow relation supplements through the existing batch resource.
    if looks_like_relation_request(payload):
        return jsonify(supplement(store, run_id, payload))
    return jsonify(review(store,run_id,payload))


def relation_payload():
    """Accept JSON, HTML forms, query params, raw CSV/text, or an uploaded file."""
    json_payload = request.get_json(silent=True)
    if isinstance(json_payload, list):
        return json_payload
    payload = json_payload if isinstance(json_payload, dict) else {}
    if request.args:
        payload = {**request.args.to_dict(flat=True), **payload}
    if payload:
        return payload

    if request.files:
        uploaded = request.files.get('file') or request.files.get('relations') or request.files.get('supplement')
        if uploaded is not None:
            parsed = parse_relation_text(uploaded.read())
            data = request.form.to_dict(flat=True)
            if data:
                data['relations'] = parsed
                return data
            return {'relations': parsed}

    if request.form:
        data = request.form.to_dict(flat=True)
        # A textarea may carry a JSON/CSV batch under one of these names.
        for key, value in list(data.items()):
            if not isinstance(value, str):
                continue
            stripped = value.strip()
            if stripped.startswith(('[', '{')):
                import json
                try:
                    data[key] = json.loads(stripped)
                except ValueError:
                    pass
            if key in ('relations', 'supplements', 'links', 'pairs', 'csv', 'text', 'content') and isinstance(data.get(key), str):
                if ('\n' in value) or (',' in value) or key in ('relations', 'supplements', 'links', 'pairs'):
                    parsed = parse_relation_text(value)
                    if parsed:
                        data['relations'] = parsed
        return data

    uploaded = request.files.get('file') or request.files.get('relations') or request.files.get('supplement')
    if uploaded is not None:
        return {'relations': parse_relation_text(uploaded.read())}

    raw = request.get_data(cache=True, as_text=True)
    if raw:
        content_type = request.content_type or ''
        if 'json' in content_type:
            import json
            try:
                parsed = json.loads(raw)
            except ValueError as error:
                raise DomainIssue('RELATION_FIELDS') from error
            return parsed
        return {'relations': parse_relation_text(raw)}
    return {}


def add_relations(run_id):
    store = current_app.extensions['runs']
    return jsonify(supplement(store, run_id, relation_payload()))


def add_case_relation(run_id, case):
    payload = relation_payload()
    if isinstance(payload, dict):
        payload.setdefault('case', case)
    elif isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                item.setdefault('case', case)
            elif isinstance(item, (list, tuple)) and len(item) == 2:
                # Tuples are handled by the service; convert to include case.
                payload[payload.index(item)] = {'case': case, 'a': item[0], 'b': item[1]}
    store = current_app.extensions['runs']
    return jsonify(supplement(store, run_id, payload))


def mutate_roster(run_id):
    store = current_app.extensions['runs']
    result = supplement(store, run_id, relation_payload())
    roster = result['roster']
    roster.update({
        'run_id': run_id,
        'id': run_id,
        'status': result.get('status'),
        'revision': result.get('revision'),
        'batch_revision': result.get('revision'),
        'affected_case': result.get('case'),
    })
    if result.get('case') is not None:
        for key in ('case', 'train', 'evaluation', 'quarantined', 'available',
                    'available_samples', 'groups', 'changed'):
            roster[key] = result.get(key)
    return jsonify(roster)


def add_relations_from_body():
    payload = relation_payload()
    run_id = None
    if isinstance(payload, dict):
        run_id = payload.get('run_id') or payload.get('id') or payload.get('batch_id') or payload.get('runId')
    if not run_id:
        raise DomainIssue('RUN_NOT_FOUND')
    return add_relations(run_id)


def roster_collection():
    run_id = request.args.get('run_id') or request.args.get('id') or request.args.get('batch_id') or request.args.get('runId')
    if not run_id:
        raise DomainIssue('RUN_NOT_FOUND')
    return get_roster(run_id)


def supplements_collection():
    run_id = request.args.get('run_id') or request.args.get('id') or request.args.get('batch_id') or request.args.get('runId')
    if not run_id:
        raise DomainIssue('RUN_NOT_FOUND')
    loaded = current_app.extensions['runs'].load(run_id)
    return jsonify(items=loaded['supplements'], supplements=loaded['supplements'],
                   relations=loaded['supplements'], roster=loaded['roster'])


def get_roster(run_id):
    store = current_app.extensions['runs']
    loaded = store.load(run_id)
    case_filter = request.args.get('case') or request.args.get('case_id') or request.args.get('group')
    if case_filter:
        from app.modules.roster import resolve_case
        case = resolve_case(loaded['report'], case_filter)
        return jsonify(loaded['roster']['by_case'][case['case']])
    roster_name = request.path.rstrip('/').split('/')[-1]
    if roster_name in {'original', 'original-roster', 'original_roster', 'original-list', 'original_list'}:
        return jsonify(loaded['original_roster'])
    if roster_name in {'issued', 'issued-roster', 'issued_roster', 'approved-roster', 'approved_roster'}:
        if 'issued_roster' not in loaded:
            raise DomainIssue('ROSTER_NOT_ISSUED', 'ROSTER_NOT_FOUND')
        return jsonify(loaded['issued_roster'])
    if roster_name in {'supplements', 'relations', 'links'}:
        return jsonify(items=loaded['supplements'], relations=loaded['supplements'],
                       supplements=loaded['supplements'], roster=loaded['roster'])
    return jsonify(loaded['roster'])


def get_case_roster(run_id, case):
    store = current_app.extensions['runs']
    loaded = store.load(run_id)
    from app.modules.roster import resolve_case
    resolved = resolve_case(loaded['report'], case)
    return jsonify(loaded['roster']['by_case'][resolved['case']])


# Primary late-relation and roster endpoints.
_relation_paths = (
    '/runs/<run_id>/supplements', '/runs/<run_id>/supplement',
    '/runs/<run_id>/relations', '/runs/<run_id>/relation',
    '/runs/<run_id>/links', '/runs/<run_id>/link',
    '/runs/<run_id>/duplicates', '/runs/<run_id>/duplicate',
    '/runs/<run_id>/near-duplicates', '/runs/<run_id>/late-relations',
    '/runs/<run_id>/sample-relations', '/runs/<run_id>/sample-links',
    '/runs/<run_id>/supplement-relations', '/runs/<run_id>/late-links',
)
for _path in _relation_paths:
    api.add_url_rule(_path, view_func=add_relations, methods=['POST'])
    api.add_url_rule(_path, view_func=add_relations, methods=['PUT', 'PATCH'])

_case_relation_paths = (
    '/runs/<run_id>/cases/<case>/supplements',
    '/runs/<run_id>/cases/<case>/supplement',
    '/runs/<run_id>/cases/<case>/relations',
    '/runs/<run_id>/cases/<case>/links',
)
for _path in _case_relation_paths:
    api.add_url_rule(_path, view_func=add_case_relation, methods=['POST', 'PUT', 'PATCH'])

for path in ('/runs/<run_id>/roster', '/runs/<run_id>/current-roster',
             '/runs/<run_id>/current_roster', '/runs/<run_id>/available',
             '/runs/<run_id>/availability', '/runs/<run_id>/available-roster',
             '/runs/<run_id>/available_roster', '/runs/<run_id>/available-list',
             '/runs/<run_id>/available_list', '/runs/<run_id>/available-samples',
             '/runs/<run_id>/available_samples', '/runs/<run_id>/sample-roster',
             '/runs/<run_id>/sample_roster', '/runs/<run_id>/sampling-roster',
             '/runs/<run_id>/sampling_roster', '/runs/<run_id>/sampling-list',
             '/runs/<run_id>/sampling_list'):
    api.add_url_rule(path, view_func=get_roster, methods=['GET'])
    api.add_url_rule(path, view_func=mutate_roster, methods=['POST', 'PATCH', 'PUT'])

for path in ('/runs/<run_id>/supplements', '/runs/<run_id>/relations', '/runs/<run_id>/links'):
    api.add_url_rule(path, view_func=get_roster, methods=['GET'])

for path in ('/runs/<run_id>/original', '/runs/<run_id>/original-roster',
             '/runs/<run_id>/original_roster', '/runs/<run_id>/original-list',
             '/runs/<run_id>/original_list', '/runs/<run_id>/issued',
             '/runs/<run_id>/issued-roster', '/runs/<run_id>/issued_roster',
             '/runs/<run_id>/approved-roster', '/runs/<run_id>/approved_roster',
             '/runs/<run_id>/roster/original', '/runs/<run_id>/roster/issued',
             '/runs/<run_id>/roster/approved'):
    api.add_url_rule(path, view_func=get_roster, methods=['GET'])

for path in ('/runs/<run_id>/cases/<case>/roster',
             '/runs/<run_id>/cases/<case>/available',
             '/runs/<run_id>/cases/<case>/available-roster'):
    api.add_url_rule(path, view_func=get_case_roster, methods=['GET'])

# A few top-level aliases for clients that identify the batch in the body/path.
api.add_url_rule('/supplements/<run_id>', view_func=add_relations, methods=['POST'])
api.add_url_rule('/relations/<run_id>', view_func=add_relations, methods=['POST'])
api.add_url_rule('/roster/<run_id>', view_func=get_roster, methods=['GET'])
api.add_url_rule('/available/<run_id>', view_func=get_roster, methods=['GET'])
api.add_url_rule('/available-roster/<run_id>', view_func=get_roster, methods=['GET'])
api.add_url_rule('/available-samples/<run_id>', view_func=get_roster, methods=['GET'])
api.add_url_rule('/supplements', view_func=add_relations_from_body, methods=['POST', 'PUT', 'PATCH'])
api.add_url_rule('/supplements', view_func=supplements_collection, methods=['GET'])
api.add_url_rule('/supplement', view_func=add_relations_from_body, methods=['POST', 'PUT', 'PATCH'])
api.add_url_rule('/relations', view_func=add_relations_from_body, methods=['POST', 'PUT', 'PATCH'])
api.add_url_rule('/relation', view_func=add_relations_from_body, methods=['POST', 'PUT', 'PATCH'])
api.add_url_rule('/links', view_func=add_relations_from_body, methods=['POST', 'PUT', 'PATCH'])
api.add_url_rule('/link', view_func=add_relations_from_body, methods=['POST', 'PUT', 'PATCH'])
api.add_url_rule('/duplicates', view_func=add_relations_from_body, methods=['POST', 'PUT', 'PATCH'])
api.add_url_rule('/roster', view_func=add_relations_from_body, methods=['POST', 'PUT', 'PATCH'])
api.add_url_rule('/roster', view_func=roster_collection, methods=['GET'])
api.add_url_rule('/available', view_func=roster_collection, methods=['GET'])


@api.get('/runs/<run_id>/evidence')
def export(run_id):
    run = current_app.extensions['runs'].load(run_id)
    return Response(artifact(run),mimetype='application/json', headers={
        'Content-Disposition':f'attachment; filename="review-{run["id"][:12]}.json"',
        'Cache-Control':'no-store',
    })
