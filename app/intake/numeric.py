import re
import unicodedata

from app.business import DomainIssue

MISSING = {'', '-', 'N/A', 'NULL', '未知'}


def quantity(value):
    text = unicodedata.normalize('NFKC', value).strip()
    if text.upper() in MISSING:
        raise DomainIssue('MISSING_NUMBER')
    if not re.fullmatch(r'(?:[0-9]{1,12}|[0-9]{1,3}(?:,[0-9]{3}){1,3})', text):
        raise DomainIssue('INVALID_NUMBER')
    return int(text.replace(',', ''))
