"""Domain checks with dnspython: MX, or A/AAAA fallback (RFC 5321 5.1).

Only DNS is used. There is no SMTP conversation of any kind.
"""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

OK_MX = "ok_mx"
OK_ADDRESS = "ok_address"
NULL_MX = "null_mx"
NXDOMAIN = "nxdomain"
NO_RECORDS = "no_records"
ERROR = "error"


@dataclass(frozen=True)
class DnsResult:
    status: str
    detail: str = ""

    @property
    def deliverable(self):
        return self.status in (OK_MX, OK_ADDRESS)


class DnsChecker:
    """Callable ``domain -> DnsResult``. Pass ``resolver`` to inject a fake."""

    def __init__(self, timeout=5.0, resolver=None):
        import dns.resolver

        self.timeout = timeout
        if resolver is None:
            resolver = dns.resolver.Resolver(configure=True)
            resolver.lifetime = timeout
            resolver.timeout = min(timeout, 2.0)
        self.resolver = resolver

    def __call__(self, domain):
        import dns.exception
        import dns.resolver

        def query(rdtype):
            try:
                return self.resolver.resolve(domain, rdtype, lifetime=self.timeout)
            except dns.resolver.NXDOMAIN:
                raise
            except dns.resolver.NoAnswer:
                return None

        try:
            try:
                mx = query("MX")
            except dns.resolver.NXDOMAIN:
                return DnsResult(NXDOMAIN, "domain does not exist")
            if mx is not None:
                exchanges = [str(rr.exchange).rstrip(".") for rr in mx]
                if all(name == "" for name in exchanges):
                    return DnsResult(NULL_MX, "null MX (RFC 7505): domain accepts no mail")
                hosts = [name for name in exchanges if name]
                return DnsResult(OK_MX, ", ".join(sorted(hosts)))
            found = []
            for rdtype in ("A", "AAAA"):
                if query(rdtype) is not None:
                    found.append(rdtype)
            if found:
                return DnsResult(OK_ADDRESS, "no MX, address records: " + "/".join(found))
            return DnsResult(NO_RECORDS, "no MX, A or AAAA records")
        except dns.resolver.NXDOMAIN:
            return DnsResult(NXDOMAIN, "domain does not exist")
        except dns.exception.Timeout:
            return DnsResult(ERROR, "timeout")
        except dns.exception.DNSException as exc:
            return DnsResult(ERROR, type(exc).__name__)


def lookup_domains(domains, lookup, workers=2):
    """Look up each unique domain once. Returns ``{domain: DnsResult}``."""
    unique = list(dict.fromkeys(domains))

    def safe(domain):
        try:
            return lookup(domain)
        except Exception as exc:  # an injected or failing resolver
            return DnsResult(ERROR, type(exc).__name__)

    if workers <= 1 or len(unique) <= 1:
        results = [safe(d) for d in unique]
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(safe, unique))
    return dict(zip(unique, results))
