"""Literal quoted-word and phrase semantics shared with PostgreSQL."""

import re

import pytest

from backend.application.job_processing.search import parse_search_query, search_regex


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Intern", True),
        ("Summer INTERN, Engineering", True),
        ("internet", False),
        ("internal", False),
        ("internship", False),
        ("preintern", False),
        ("intern_developer", False),
    ],
)
def test_exact_intern_word(text, expected):
    assert bool(re.search(search_regex('"intern"'), text, re.I)) is expected


@pytest.mark.parametrize("term", ["C++", "[test]", "100%", "a_b", "data engineer"])
def test_exact_terms_and_phrases_are_literal(term):
    assert re.search(search_regex(f'"{term}"'), f"Use {term} today.", re.I)
    assert not re.search(search_regex(f'"{term}"'), f"before{term}after", re.I)


@pytest.mark.parametrize("query", ['"intern', 'intern"', '""', '" "'])
def test_incomplete_or_empty_quotes_do_not_become_empty_regex(query):
    term, exact = parse_search_query(query)
    assert term == query and not exact
