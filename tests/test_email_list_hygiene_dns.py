"""DNS behaviour with injected resolvers only: no network."""

import dns.exception
import dns.name
import dns.resolver
import pytest

from email_list_hygiene import DnsChecker, DnsResult, Options, clean_rows
from email_list_hygiene import dns_check


class FakeRR:
    def __init__(self, exchange):
        self.exchange = dns.name.from_text(exchange)


class FakeResolver:
    """Maps (domain, rdtype) to a list of MX exchanges / anything, or an exception."""

    def __init__(self, table):
        self.table = table
        self.calls = []

    def resolve(self, domain, rdtype, **kwargs):
        self.calls.append((domain, rdtype))
        outcome = self.table.get((domain, rdtype), dns.resolver.NoAnswer())
        if isinstance(outcome, Exception):
            raise outcome
        return [FakeRR(x) for x in outcome]


def check(table, domain="example.org"):
    return DnsChecker(timeout=1, resolver=FakeResolver(table))(domain)


def test_mx_present():
    res = check({("example.org", "MX"): ["mx1.example.org.", "mx2.example.org."]})
    assert res.status == dns_check.OK_MX and res.deliverable


def test_null_mx_is_reported():
    res = check({("example.org", "MX"): ["."]})
    assert res.status == dns_check.NULL_MX and not res.deliverable


def test_a_record_fallback():
    res = check({("example.org", "A"): ["x"]})
    assert res.status == dns_check.OK_ADDRESS and res.deliverable


def test_aaaa_fallback():
    assert check({("example.org", "AAAA"): ["x"]}).status == dns_check.OK_ADDRESS


def test_no_records_at_all():
    assert check({}).status == dns_check.NO_RECORDS


def test_nxdomain():
    assert check({("example.org", "MX"): dns.resolver.NXDOMAIN()}).status == dns_check.NXDOMAIN


def test_nxdomain_on_address_stage():
    table = {("example.org", "A"): dns.resolver.NXDOMAIN()}
    assert check(table).status == dns_check.NXDOMAIN


def test_timeout_is_an_error_not_a_verdict():
    res = check({("example.org", "MX"): dns.exception.Timeout()})
    assert res.status == dns_check.ERROR and res.detail == "timeout"


def test_no_nameservers_is_an_error():
    res = check({("example.org", "MX"): dns.resolver.NoNameservers()})
    assert res.status == dns_check.ERROR


def test_lookup_domains_calls_once_per_unique_domain():
    seen = []

    def lookup(domain):
        seen.append(domain)
        return DnsResult(dns_check.OK_MX)

    out = dns_check.lookup_domains(["a.example", "b.example", "a.example"], lookup, workers=3)
    assert sorted(seen) == ["a.example", "b.example"]
    assert set(out) == {"a.example", "b.example"}


def test_lookup_domains_survives_a_crashing_resolver():
    def lookup(domain):
        raise RuntimeError("boom")

    out = dns_check.lookup_domains(["a.example"], lookup, workers=1)
    assert out["a.example"].status == dns_check.ERROR


# --- integration with the pipeline -----------------------------------------


def fake_lookup(table, calls):
    def lookup(domain):
        calls.append(domain)
        return table.get(domain, DnsResult(dns_check.OK_MX))

    return lookup


def test_pipeline_rejects_dead_domains_and_checks_each_domain_once():
    calls = []
    table = {
        "gone.example": DnsResult(dns_check.NXDOMAIN),
        "nomail.example": DnsResult(dns_check.NULL_MX),
        "empty.example": DnsResult(dns_check.NO_RECORDS),
        "slow.example": DnsResult(dns_check.ERROR, "timeout"),
    }
    rows = [[a] for a in [
        "a@example.com", "b@example.com", "c@gone.example", "d@nomail.example",
        "e@empty.example", "f@slow.example", "g@GONE.example",
    ]]
    res = clean_rows(["email"], rows, Options(), dns_lookup=fake_lookup(table, calls))
    assert sorted(calls) == ["empty.example", "example.com", "gone.example",
                             "nomail.example", "slow.example"]
    assert [r.reasons for r in res.rows] == [
        [], [], ["dns_nxdomain"], ["dns_null_mx"], ["dns_no_mx_or_a"], [], ["dns_nxdomain"],
    ]
    assert res.rows[5].kept and res.rows[5].flags == ["dns_lookup_failed"]
    assert res.summary["dns"]["unique_domains_checked"] == 5


def test_dns_skipped_for_rows_already_rejected():
    calls = []
    rows = [["info@mailinator.com"], ["not-an-email"], ["a@example.com"], ["a@example.com"]]
    clean_rows(["email"], rows, Options(), dns_lookup=fake_lookup({}, calls))
    assert calls == ["example.com"]


def test_no_dns_option_makes_no_lookup(monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("resolver must not be built")

    monkeypatch.setattr(dns_check, "DnsChecker", boom)
    res = clean_rows(["email"], [["a@example.com"]], Options(check_dns=False))
    assert res.rows[0].kept
    assert res.summary["dns"] == {
        "enabled": False, "unique_domains_checked": 0, "results": {}, "domains": {},
    }
