import csv
import io

from app.business import DomainIssue
from app.config import MAX_FILE, MAX_ROWS
from app.intake.schema import HEADER


def records(data):
    if len(data) > MAX_FILE:
        raise DomainIssue('FILE_TOO_LARGE')
    try:
        text = data.decode('utf-8-sig')
    except UnicodeDecodeError as error:
        raise DomainIssue('ENCODING_INVALID') from error
    if not text:
        raise DomainIssue('FILE_EMPTY')
    if not text.strip():
        raise DomainIssue('FILE_BLANK')
    reader = csv.reader(io.StringIO(text, newline=''), strict=True)
    if tuple(next(reader)) != HEADER:
        raise DomainIssue('HEADER_MISMATCH')
    count = 0
    for number, row in enumerate(reader, 1):
        if number > MAX_ROWS:
            raise DomainIssue('ROW_LIMIT')
        count += 1
        yield reader.line_num, row
    if count == 0:
        raise DomainIssue('HEADER_ONLY')
