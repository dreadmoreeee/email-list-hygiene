import pytest

from email_list_hygiene import suggest_domain
from email_list_hygiene.typos import edit_distance


@pytest.mark.parametrize(
    "typo,fixed",
    [
        ("gmial.com", "gmail.com"),
        ("gmal.com", "gmail.com"),
        ("gmail.con", "gmail.com"),
        ("hotmial.com", "hotmail.com"),
        ("yaho.ca", "yahoo.ca"),
        ("outlok.com", "outlook.com"),
        ("simpatico.ca", "sympatico.ca"),
        ("rogers.con", "rogers.com"),
        ("bell.ne", "bell.net"),
        ("shw.ca", "shaw.ca"),
        ("GMIAL.COM", "gmail.com"),
    ],
)
def test_explicit_map(typo, fixed):
    assert suggest_domain(typo) == fixed


@pytest.mark.parametrize(
    "typo,fixed",
    [
        ("gmaill.com", "gmail.com"),      # insertion
        ("gmiail.com", "gmail.com"),      # insertion
        ("hotmaill.com", "hotmail.com"),  # insertion
        ("hotmali.com", "hotmail.com"),   # transposition
        ("outlookk.com", "outlook.com"),
        ("videotrn.ca", "videotron.ca"),
        ("videotronn.ca", "videotron.ca"),
        ("sympaticoo.ca", "sympatico.ca"),
        ("protonmial.com", "protonmail.com"),
    ],
)
def test_fuzzy_match_against_providers(typo, fixed):
    assert suggest_domain(typo) == fixed


@pytest.mark.parametrize(
    "domain",
    ["gmail.com", "shaw.ca", "bell.net", "example.com", "example.ca", "life.com",
     "rogers.ca", "gmx.com", "mail.com", "yahoo.co", "xn--bcher-kva.example", "sympatico.ca"],
)
def test_no_suggestion_for_correct_or_unrelated_domains(domain):
    assert suggest_domain(domain) is None


def test_edit_distance_basics():
    assert edit_distance("gmail.com", "gmail.com") == 0
    assert edit_distance("gmial.com", "gmail.com") == 1  # transposition counts once
    assert edit_distance("abc", "") == 3
    assert edit_distance("kitten", "sitting") == 3
