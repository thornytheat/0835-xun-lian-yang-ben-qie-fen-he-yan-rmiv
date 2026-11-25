from app.business import DomainIssue
from app.intake.service import inspect
from app.modules.calculate import compute
from app.modules.grouping import case_groups
from app.modules.policy import policy
from app.modules.prepare import prepare
from app.modules.reconcile import balance


def evaluate(rows, stage):
    case = {'case':rows[0]['case'],'records':[r['record'] for r in rows], 'status':'READY'}
    case['registry'] = {
        'sample_to_record': {str(r['sample']): r['record'] for r in rows if r['kind'] == 'record'},
        'record_to_sample': {r['record']: r['sample'] for r in rows if r['kind'] == 'record'},
        'samples': {
            str(r['sample']): {
                'record': r['record'], 'entity': r['entity'], 'fingerprint': r['fingerprint'],
                'day': r['day'], 'split_code': r['split_code'],
            }
            for r in rows if r['kind'] == 'record'
        },
    }
    try:
        case['prep'], payload = prepare(rows)
        if stage >= 3:
            case['measure'] = compute(payload)
        if stage >= 4:
            case.update(policy(case['measure']))
    except DomainIssue as error:
        case['status'] = error.code
    return case


def run(data, stage=5):
    intake = inspect(data)
    output = {'intake': {k:v for k,v in intake.items() if k!='rows'}}
    if stage == 1:
        return output
    cases = [evaluate(rows, stage) for _, rows in case_groups(intake['rows'])]
    output['cases'] = cases
    if stage >= 5:
        output['balance'] = balance(intake,cases)
    return output
