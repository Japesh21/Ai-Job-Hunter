import pytest
from utils.helpers import clean_text, parse_salary, parse_date, slugify, truncate


def test_clean_text_strips_html():
    assert clean_text("<b>Hello</b> <i>World</i>") == "Hello World"


def test_clean_text_collapses_whitespace():
    assert clean_text("  too   many   spaces  ") == "too many spaces"


def test_parse_salary_range():
    lo, hi = parse_salary("$80,000 - $120,000")
    assert lo == 80000
    assert hi == 120000


def test_parse_salary_hourly_converts():
    lo, hi = parse_salary("$25 - $35/hr")
    assert lo == 25 * 2080
    assert hi == 35 * 2080


def test_parse_salary_empty():
    assert parse_salary("") == (None, None)


def test_parse_date_iso():
    result = parse_date("2024-05-15")
    assert result is not None
    assert "2024-05-15" in result


def test_parse_date_invalid():
    assert parse_date("not a date") is None


def test_slugify():
    assert slugify("Senior Data Scientist!") == "senior-data-scientist"


def test_truncate():
    text = "word " * 200
    result = truncate(text, max_len=50)
    assert len(result) <= 55
