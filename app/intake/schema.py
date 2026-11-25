import re

from app.business import DomainIssue
from app.intake.numeric import quantity
from app.spec import COLUMNS, KINDS

HEADER = ('record', 'case', 'kind', *COLUMNS, 'note')


def record(values):
    if len(values) != len(HEADER):
        raise DomainIssue('COLUMN_COUNT')
    row = dict(zip(HEADER, values))
    for key in ('record', 'case'):
        row[key] = row[key].strip()
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,35}', row[key]):
            raise DomainIssue('BAD_IDENTIFIER')
    if row['kind'] not in KINDS:
        raise DomainIssue('UNKNOWN_KIND')
    for column in COLUMNS:
        row[column] = quantity(row[column])
    if len(row['note']) > 200:
        raise DomainIssue('NOTE_TOO_LONG')
    return row
