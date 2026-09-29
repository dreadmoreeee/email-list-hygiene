"""Consent / opt-in column detection and value interpretation.

CASL note: this is a filter, not legal advice. See the README.
"""

import re

OPTED_IN = "opted_in"
OPTED_OUT = "opted_out"
UNKNOWN = "unknown"

_YES = frozenset(
    """
    yes y true t 1 oui o on x checked optedin optin subscribed express
    expressconsent consented granted accepted agree agreed
    """.split()
)
_NO = frozenset(
    """
    no n false f 0 non off optedout optout unsubscribed withdrawn revoked
    declined refused denied none
    """.split()
)
_HINTS = ("consent", "optin", "subscribed", "subscription", "acceptsmarketing", "newsletter")
_SKIP_TOKENS = frozenset(
    "date time at timestamp ts source ip when text url version note notes channel".split()
)


def classify_value(value):
    """Return OPTED_IN, OPTED_OUT or UNKNOWN (empty or unrecognised)."""
    key = re.sub(r"[\s_-]+", "", value.strip().lower())
    if key in _YES:
        return OPTED_IN
    if key in _NO:
        return OPTED_OUT
    return UNKNOWN


def _tokens(name):
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name.strip())
    return [t for t in re.split(r"[^a-z0-9]+", spaced.lower()) if t]


def detect_consent_column(header):
    """Index of the first column that looks like a consent flag, or None.

    Columns that look like dates, sources or inverted flags (``unsubscribed``,
    ``opt_out``) are ignored; name such a column explicitly if you need it.
    """
    for index, name in enumerate(header):
        tokens = _tokens(name)
        squashed = "".join(tokens)
        if any(t in _SKIP_TOKENS for t in tokens):
            continue
        if "unsub" in squashed or "optout" in squashed:
            continue
        if any(hint in squashed for hint in _HINTS):
            return index
    return None


def detect_email_column(header):
    """Index of the column holding the address, or None."""
    squashed = ["".join(_tokens(name)) for name in header]
    for wanted in ("email", "emailaddress", "mail", "courriel", "adressecourriel"):
        if wanted in squashed:
            return squashed.index(wanted)
    for index, name in enumerate(squashed):
        if "email" in name or "courriel" in name:
            return index
    return None
