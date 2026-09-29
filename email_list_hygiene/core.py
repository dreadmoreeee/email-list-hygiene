"""The cleaning pipeline. Pure functions over rows; no network unless DNS is on."""

import re
from dataclasses import dataclass, field

from . import dns_check
from .consent import (
    OPTED_IN,
    OPTED_OUT,
    classify_value,
    detect_consent_column,
    detect_email_column,
)
from .data import ROLE_LOCAL_PARTS, load_disposable_domains
from .syntax import split_address, validate_email
from .typos import suggest_domain

GMAIL_DOMAINS = frozenset({"gmail.com", "googlemail.com"})

CASL_NOTE = (
    "CASL note: this tool filters on the consent column you supply; it cannot "
    "verify that consent is valid, express or implied, or documented. This is "
    "not legal advice; check Canada's Anti-Spam Legislation (CASL) and your own "
    "records before sending."
)

REASONS = {
    "empty_email": "Empty address",
    "missing_at": "No @ sign",
    "multiple_at": "More than one @ sign",
    "local_empty": "Empty local part",
    "local_too_long": "Local part longer than 64 characters",
    "local_bad_dots": "Local part starts/ends with a dot or has consecutive dots",
    "local_invalid_chars": "Local part has characters outside the supported dot-atom subset",
    "domain_empty": "Empty domain",
    "domain_empty_label": "Domain has an empty label (leading, trailing or double dot)",
    "label_too_long": "A domain label is longer than 63 characters",
    "domain_invalid_chars": "Domain label has invalid characters or hyphens in the wrong place",
    "idna_invalid": "Domain cannot be converted to punycode",
    "domain_no_dot": "Domain has no dot (single label)",
    "domain_numeric_tld": "Top-level label is all digits",
    "address_too_long": "Address longer than 254 characters",
    "duplicate": "Duplicate of an earlier row",
    "duplicate_gmail_variant": "Gmail dot/+tag variant of an earlier row",
    "role_account": "Role account (info@, sales@, ...)",
    "disposable_domain": "Disposable email domain",
    "typo_domain": "Probable typo of a big provider domain",
    "dns_nxdomain": "Domain does not exist",
    "dns_null_mx": "Domain publishes a null MX (accepts no mail)",
    "dns_no_mx_or_a": "Domain has no MX and no A/AAAA record",
    "not_opted_in": "Consent column says not opted in",
    "consent_unknown": "Consent value empty or not recognised",
}

FLAGS = {
    "role_account": "Role account (kept)",
    "disposable_domain": "Disposable email domain (kept)",
    "typo_domain": "Probable typo of a big provider domain (kept, see suggestion)",
    "typo_fixed": "Typo fixed with --fix-typos (kept, cleaned CSV has the fixed address)",
    "dns_lookup_failed": "DNS lookup failed or timed out; address kept",
}

DNS_REASON = {
    dns_check.NXDOMAIN: "dns_nxdomain",
    dns_check.NULL_MX: "dns_null_mx",
    dns_check.NO_RECORDS: "dns_no_mx_or_a",
}


@dataclass
class Options:
    email_column: str = None  # name; auto-detected when None
    consent_column: str = None  # name; auto-detected when None
    filter_consent: bool = True  # False: ignore any consent column
    gmail_canonical: bool = False
    reject_roles: bool = False
    keep_disposable: bool = False  # flag instead of rejecting
    reject_typos: bool = False
    fix_typos: bool = False
    check_dns: bool = True
    dns_timeout: float = 5.0
    dns_workers: int = 2


@dataclass
class RowResult:
    line: int  # 1-based data row (header excluded)
    values: list
    email: str  # trimmed raw value
    normalized: str = None
    reasons: list = field(default_factory=list)
    flags: list = field(default_factory=list)
    suggestion: str = None

    @property
    def kept(self):
        return not self.reasons


@dataclass
class CleanResult:
    header: list
    email_index: int
    consent_index: int
    rows: list
    summary: dict

    @property
    def kept(self):
        return [r for r in self.rows if r.kept]

    @property
    def rejected(self):
        return [r for r in self.rows if not r.kept]


def _add(lst, item):
    if item not in lst:
        lst.append(item)


def is_role_account(local):
    base = re.sub(r"[._-]", "", local.lower().split("+")[0])
    return base in ROLE_LOCAL_PARTS


def is_disposable(domain, disposable):
    parts = domain.split(".")
    return any(".".join(parts[i:]) in disposable for i in range(len(parts) - 1))


def gmail_canonical_key(local, domain):
    """Key that ignores Gmail dots, +tags and the googlemail.com alias."""
    if domain in GMAIL_DOMAINS:
        return local.lower().split("+")[0].replace(".", "") + "@gmail.com"
    return f"{local.lower()}@{domain}"


def _resolve_column(header, name, what):
    if name is None:
        return None
    lowered = [h.strip().lower() for h in header]
    if name.strip().lower() not in lowered:
        raise ValueError(f"{what} column {name!r} not found in header {header!r}")
    return lowered.index(name.strip().lower())


def clean_rows(header, rows, options=None, dns_lookup=None):
    """Run every check over ``rows`` (lists of strings) under ``header``.

    ``dns_lookup`` is a callable ``domain -> DnsResult``; when None and
    ``options.check_dns`` is true, a real ``DnsChecker`` is used. Only the
    unique domains of rows that survived every other check are looked up.
    """
    options = options or Options()
    email_index = _resolve_column(header, options.email_column, "email")
    if email_index is None:
        email_index = detect_email_column(header)
    if email_index is None:
        raise ValueError("no email column found; pass the column name explicitly")

    consent_index = None
    if options.filter_consent:
        consent_index = _resolve_column(header, options.consent_column, "consent")
        if consent_index is None:
            consent_index = detect_consent_column(header)

    disposable = load_disposable_domains()
    results = []
    seen_plain = set()
    seen_canonical = set()

    for line, raw in enumerate(rows, start=1):
        values = list(raw) + [""] * (len(header) - len(raw))
        res = RowResult(line=line, values=values, email=values[email_index].strip())
        results.append(res)

        normalized, error = validate_email(res.email)
        if error:
            res.reasons.append(error)
        else:
            local, domain = split_address(normalized)
            suggestion = suggest_domain(domain)
            if suggestion:
                res.suggestion = f"{local}@{suggestion}"
                if options.fix_typos:
                    _add(res.flags, "typo_fixed")
                    normalized = res.suggestion
                    domain = suggestion
                elif options.reject_typos:
                    _add(res.reasons, "typo_domain")
                else:
                    _add(res.flags, "typo_domain")
            res.normalized = normalized
            if is_disposable(domain, disposable):
                _add(res.flags if options.keep_disposable else res.reasons, "disposable_domain")
            if is_role_account(local):
                _add(res.reasons if options.reject_roles else res.flags, "role_account")

            plain = f"{local.lower()}@{domain}"
            if plain in seen_plain:
                _add(res.reasons, "duplicate")
            elif options.gmail_canonical and gmail_canonical_key(local, domain) in seen_canonical:
                _add(res.reasons, "duplicate_gmail_variant")
            seen_plain.add(plain)
            if options.gmail_canonical:
                seen_canonical.add(gmail_canonical_key(local, domain))

        if consent_index is not None:
            verdict = classify_value(values[consent_index])
            if verdict == OPTED_OUT:
                _add(res.reasons, "not_opted_in")
            elif verdict != OPTED_IN:
                _add(res.reasons, "consent_unknown")

    dns_results = {}
    if options.check_dns:
        if dns_lookup is None:
            dns_lookup = dns_check.DnsChecker(timeout=options.dns_timeout)
        candidates = [split_address(r.normalized)[1] for r in results if r.kept]
        dns_results = dns_check.lookup_domains(candidates, dns_lookup, options.dns_workers)
        for res in results:
            if not res.kept:
                continue
            outcome = dns_results[split_address(res.normalized)[1]]
            if outcome.status in DNS_REASON:
                res.reasons.append(DNS_REASON[outcome.status])
            elif outcome.status == dns_check.ERROR:
                res.flags.append("dns_lookup_failed")

    summary = build_summary(header, email_index, consent_index, results, options, dns_results)
    return CleanResult(header, email_index, consent_index, results, summary)


def build_summary(header, email_index, consent_index, results, options, dns_results):
    reason_counts = {}
    flag_counts = {}
    for res in results:
        for reason in res.reasons:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
        for flag in res.flags:
            flag_counts[flag] = flag_counts.get(flag, 0) + 1
    dns_counts = {}
    for outcome in dns_results.values():
        dns_counts[outcome.status] = dns_counts.get(outcome.status, 0) + 1
    kept = sum(1 for r in results if r.kept)
    return {
        "total_rows": len(results),
        "kept": kept,
        "rejected": len(results) - kept,
        "email_column": header[email_index],
        "consent_column": header[consent_index] if consent_index is not None else None,
        "reasons": dict(sorted(reason_counts.items())),
        "flags": dict(sorted(flag_counts.items())),
        "flagged": [
            {
                "row": r.line,
                "email": r.normalized or r.email,
                "flags": r.flags,
                "suggestion": r.suggestion,
            }
            for r in results
            if r.flags or (r.suggestion and not r.kept)
        ],
        "dns": {
            "enabled": options.check_dns,
            "unique_domains_checked": len(dns_results),
            "results": dict(sorted(dns_counts.items())),
            "domains": {
                d: {"status": o.status, "detail": o.detail} for d, o in sorted(dns_results.items())
            },
        },
        "options": {
            "gmail_canonical": options.gmail_canonical,
            "reject_roles": options.reject_roles,
            "keep_disposable": options.keep_disposable,
            "reject_typos": options.reject_typos,
            "fix_typos": options.fix_typos,
        },
        "casl_note": CASL_NOTE,
    }
