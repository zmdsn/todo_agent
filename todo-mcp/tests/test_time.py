# tests/test_time.py
from datetime import date
from todo_mcp.utils.time import TimeParser, TimeResolution

def test_parse_year():
    parser = TimeParser(base_date=date(2026, 3, 9))
    result = parser.parse("2026")
    assert result.resolution == TimeResolution.YEAR
    assert result.year == 2026

def test_parse_quarter():
    parser = TimeParser(base_date=date(2026, 3, 9))
    result = parser.parse("Q1")
    assert result.resolution == TimeResolution.QUARTER
    assert result.year == 2026
    assert result.quarter == 1

def test_parse_month():
    parser = TimeParser(base_date=date(2026, 3, 9))
    result = parser.parse("本月")
    assert result.resolution == TimeResolution.MONTH
    assert result.year == 2026
    assert result.month == 3

def test_parse_today():
    parser = TimeParser(base_date=date(2026, 3, 9))
    result = parser.parse("今天")
    assert result.resolution == TimeResolution.DAY
    assert result.year == 2026
    assert result.month == 3
    assert result.day == 9

def test_to_file_path():
    parser = TimeParser(base_date=date(2026, 3, 9))
    result = parser.parse("本月")
    assert result.to_file_path() == "2026/Q1/03-March.md"
