"""Address syntax: a practical subset of RFC 5322 plus IDN domains.

Accepted: ``local@domain`` where the local part is a dot-atom (RFC 5322
``atext`` characters separated by single dots; NO quoted strings, NO
comments, NO obsolete forms, NO non-ASCII local parts) and the domain is a
sequence of LDH labels. Internationalised domain names are converted to
punycode with the stdlib ``idna`` codec (IDNA 2003 rules). Domain literals
such as ``[192.0.2.1]`` are rejected.

Limits: local part 64 characters, whole address 254, each label 63.
"""

import re

MAX_LOCAL = 64
MAX_TOTAL = 254
MAX_LABEL = 63

_ATEXT = r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+"
_LOCAL_RE = re.compile(rf"^{_ATEXT}(?:\.{_ATEXT})*$")
_LABEL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")


def _domain_to_ascii(domain):
    """Lowercase ``domain`` and convert to punycode. Return (ascii, error)."""
    domain = domain.lower()
    if not domain:
        return None, "domain_empty"
    pieces = []
    for label in domain.split("."):
        if not label:
            return None, "domain_empty_label"
        if len(label) > MAX_LABEL:
            return None, "label_too_long"
        if not label.isascii():
            try:
                label = label.encode("idna").decode("ascii")
            except UnicodeError:
                return None, "idna_invalid"
        pieces.append(label)
    ascii_domain = ".".join(pieces)
    labels = ascii_domain.split(".")
    for label in labels:
        if len(label) > MAX_LABEL:
            return None, "label_too_long"
        if not _LABEL_RE.match(label):
            return None, "domain_invalid_chars"
        if label.startswith("xn--"):
            try:
                label.encode("ascii").decode("idna")
            except UnicodeError:
                return None, "idna_invalid"
    if len(labels) < 2:
        return None, "domain_no_dot"
    if labels[-1].isdigit():
        return None, "domain_numeric_tld"
    return ascii_domain, None


def validate_email(address):
    """Validate and normalise one address.

    Returns ``(normalized, error)``. On success ``error`` is None and
    ``normalized`` is the trimmed address with the domain lowercased and
    converted to punycode (local part case is kept). On failure
    ``normalized`` is None and ``error`` is a reason code.
    """
    address = address.strip()
    if not address:
        return None, "empty_email"
    if address.count("@") == 0:
        return None, "missing_at"
    if address.count("@") > 1:
        return None, "multiple_at"
    local, domain = address.split("@")
    if not local:
        return None, "local_empty"
    if len(local) > MAX_LOCAL:
        return None, "local_too_long"
    if local.startswith(".") or local.endswith(".") or ".." in local:
        return None, "local_bad_dots"
    if not local.isascii() or not _LOCAL_RE.match(local):
        return None, "local_invalid_chars"
    ascii_domain, error = _domain_to_ascii(domain)
    if error:
        return None, error
    normalized = f"{local}@{ascii_domain}"
    if len(normalized) > MAX_TOTAL:
        return None, "address_too_long"
    return normalized, None


def split_address(normalized):
    """Split a normalised address into (local, domain)."""
    local, _, domain = normalized.partition("@")
    return local, domain
