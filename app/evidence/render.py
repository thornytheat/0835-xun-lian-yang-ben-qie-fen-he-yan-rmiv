import json

from app.modules.roster import build_roster


def artifact(run):
    roster = run.get('roster') or build_roster(run['report'], run.get('supplements', []))
    packet = {
        'schema': 'review-evidence/1',
        'manifest': run['report']['manifest'],
        'balance': run['report']['balance'],
        'cases': run['report']['cases'],
        'intake': run['report']['intake'],
        'original': run.get('original_roster') or roster.get('original'),
        'original_roster': run.get('original_roster') or roster.get('original'),
        'roster': roster,
        'available_roster': roster,
        'supplements': run.get('supplements', []),
        'relations': run.get('supplements', []),
        'issued': run.get('issued_roster'),
        'issued_roster': run.get('issued_roster'),
        'review': {
            'status': run['status'],
            'revision': (run.get('issued_roster') or {}).get('issued_revision', run['revision']),
            'note': run['note'],
            'reviewed': run['reviewed'],
        },
    }
    return (json.dumps(packet, ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
