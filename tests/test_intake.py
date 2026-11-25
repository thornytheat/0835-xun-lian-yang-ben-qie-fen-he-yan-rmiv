import pytest

from app.business import DomainIssue
from app.intake.service import inspect
from app.spec import COLUMNS, KINDS
from conftest import csv_data


def line(record='0099', quantity='1', note='校核'):
    return [record,'0001',KINDS[0],quantity,*(['0']*(len(COLUMNS)-1)),note]


def test_bom_preserves_identifier():  # TRAP-02 TRAP-08
    result=inspect(b'\xef\xbb\xbf'+csv_data([line()]))
    assert result['rows'][0]['record']=='0099'


def test_quoted_newline_is_one_logical_record():  # TRAP-03
    result=inspect(csv_data([line(note='来源\n前班')]))
    assert result['input']==1 and result['rows'][0]['note']=='来源\n前班'


def test_repeated_header_is_counted(dirty):  # TRAP-04
    assert inspect(dirty)['repeated']==1


def test_extra_column_is_isolated(dirty):  # TRAP-05
    assert inspect(dirty)['reasons']['COLUMN_COUNT']==1


def test_full_width_and_grouping_are_canonical():  # TRAP-06
    assert inspect(csv_data([line(quantity='１,２３４')]))['rows'][0][COLUMNS[0]]==1234


def test_sentinel_keeps_row_out_of_total():  # TRAP-07
    assert inspect(csv_data([line(quantity='N/A')]))['reasons']=={'MISSING_NUMBER':1}


def test_duplicate_conflict_removes_both_copies():  # TRAP-14
    result=inspect(csv_data([line(quantity='1'),line(quantity='2')]))
    assert not result['rows'] and result['reasons']=={'DUPLICATE_CONFLICT':2}


def test_duplicate_replay_keeps_one_row():
    result=inspect(csv_data([line(),line()]))
    assert result['accepted']==1 and result['reasons']=={'DUPLICATE_REPLAY':1}


@pytest.mark.parametrize('value,reason',[(b'','FILE_EMPTY'),(b' \r\n','FILE_BLANK'),(csv_data([]),'HEADER_ONLY')])
def test_empty_states_have_distinct_causes(value,reason):  # TRAP-18
    with pytest.raises(DomainIssue,match=reason): inspect(value)


def test_unclosed_quote_invalidates_source():  # TRAP-16
    with pytest.raises(DomainIssue,match='CSV_MALFORMED'): inspect(csv_data([])+b'"truncated\n')
