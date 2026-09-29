"""Use email_list_hygiene as a library (works without pip install)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from email_list_hygiene import DnsResult, Options, clean_rows

header = ["email", "name", "consent"]
rows = [
    ["tamsin.vale@example.com", "Tamsin", "yes"],
    ["TAMSIN.VALE@example.com", "Tamsin again", "yes"],
    ["zq-demo-orrin.fell@gmial.com", "Orrin", "yes"],
    ["info@example.org", "Front desk", "no"],
]


def offline_lookup(domain):
    # Swap this for the default (DnsChecker) to query real DNS.
    return DnsResult("ok_mx")


result = clean_rows(header, rows, Options(gmail_canonical=True), dns_lookup=offline_lookup)
for row in result.rows:
    print(row.line, row.normalized, "KEPT" if row.kept else "REJECTED", row.reasons, row.flags, row.suggestion)
print(result.summary["reasons"])
