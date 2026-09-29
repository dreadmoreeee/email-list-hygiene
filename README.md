# email-list-hygiene

Clean a mailing list CSV **before** a campaign. It checks syntax, duplicates, role accounts, disposable domains, provider typos, DNS and consent, then writes a cleaned CSV, a rejected CSV with reasons, and a summary. It never sends anything and never talks SMTP.

Python 3.10+, one dependency ([dnspython](https://www.dnspython.org/)), MIT licensed.

## Install and run

```
pip install .                      # or run from the folder without installing
email-list-hygiene list.csv -o hygiene-out
python -m email_list_hygiene list.csv --no-dns --gmail-canonical
```

Outputs, next to each other in `-o` (default `hygiene-out/`):

- `<name>.cleaned.csv` - original columns, kept rows only. The email column holds the normalized address.
- `<name>.rejected.csv` - original columns plus `reason` (several codes joined by `;`) and `suggestion`.
- `<name>.summary.md` and/or `.summary.json` (`--summary-format md|json|both`) - counts per reason, flags, typo suggestions, DNS results.

## What it checks

| Check | Behaviour |
| --- | --- |
| Syntax | Practical subset of RFC 5322: dot-atom local part only. **No quoted strings, comments or non-ASCII local parts.** Limits: 64 local, 254 total, 63 per label. |
| IDN | Unicode domains are converted to punycode with the stdlib `idna` codec (IDNA 2003 rules, not IDNA 2008). |
| Normalize | Trim, lowercase the domain. The local part keeps its case. |
| Duplicates | Exact match after normalization, local part compared case-insensitively. First row wins, even if that row is itself rejected (so an earlier opt-out is never overridden). `--gmail-canonical` also folds Gmail dots, `+tags` and `googlemail.com`. |
| Role accounts | `info@`, `sales@`, `admin@`, `support@`, `noreply@`, `contact@`, ... Flagged by default, `--reject-roles` rejects. |
| Disposable | Rejected by default (`--keep-disposable` only flags). Bundled list, see below. |
| Typos | `gmial.com`, `hotmial.com`, `yaho.ca`, ... explicit map plus edit distance against big providers (Gmail, Yahoo, Outlook, Hotmail, iCloud, sympatico.ca, videotron.ca, shaw.ca, rogers.com, bell.net, ...). The suggestion goes in the summary. **Never applied unless you pass `--fix-typos`**; `--reject-typos` rejects instead. |
| DNS | Domain needs an MX, or an A/AAAA fallback. A null MX (RFC 7505) is rejected. One lookup per unique domain, 2 workers, 5 s timeout, `--no-dns` to skip. Only domains of rows that survived every other check are looked up. A timeout or SERVFAIL is *flagged*, not rejected. |
| Consent | If a column named like `consent`, `opt_in`, `subscribed`, `marketing_consent` is found (override with `--consent-column`, disable with `--no-consent-filter`), only opted-in rows are kept. `yes/true/1/oui/opted in/subscribed` are yes; anything empty or unrecognised is rejected as `consent_unknown`. Date, source and inverted columns (`unsubscribed`, `opt_out`) are not auto-detected. |

**CASL note.** The consent filter only trusts the column you provide. It cannot tell whether consent is express, implied, still valid or documented. This is not legal advice; check Canada's Anti-Spam Legislation (CASL) and your own records before sending.

## Why there is no SMTP probing

The tool will never issue `RCPT TO` or `VRFY`, and this is on purpose:

- **Unreliable.** Catch-all servers accept everything, greylisting and rate limits return temporary errors, and many providers answer the same for real and fake mailboxes.
- **Can get your IP blocklisted.** Repeated connection attempts that never deliver mail look like a directory harvest attack.
- **Abusive.** It uses other people's mail servers to guess whether an account exists.

DNS only tells you that a domain can receive mail at all, nothing about a mailbox.

## Bundled disposable list

`email_list_hygiene/disposable_domains.txt` is a small curated subset (about 40 common services) of names found in the public "disposable-email-domains" project (CC0 / MIT), typed out by hand and dated 2026-09-29. It is not a copy and not exhaustive. The source and date are in the file's header comment. Nothing is downloaded at runtime.

## Python API

```python
from email_list_hygiene import Options, clean_rows, clean_file

result = clean_rows(header, rows, Options(gmail_canonical=True, check_dns=False))
for row in result.rejected:
    print(row.line, row.email, row.reasons)
print(result.summary["reasons"])
```

Pass `dns_lookup=callable` (domain -> `DnsResult`) to use your own resolver. See `examples/api_example.py`. `examples/ci-example.yml` is a CI sample (it lives in `examples/` on purpose).

## Tests

```
python -m pytest -q -p no:cacheprovider --import-mode=importlib email-list-hygiene
```

DNS is mocked with injected resolvers; the tests need no network.

## Measured result

`examples/sample_list.csv` is a synthetic list of 60 invented addresses (duplicates, Gmail variants, role accounts, syntax errors, an IDN domain in punycode form, provider typos, disposable domains, a consent column). Run with real DNS on 2026-09-29:

```
python -m email_list_hygiene examples/sample_list.csv -o examples/output --gmail-canonical --summary-format both
```

```
rows: 60  kept: 7  rejected: 53
  consent_unknown: 2
  disposable_domain: 3
  dns_null_mx: 18
  dns_nxdomain: 8
  domain_empty: 1
  domain_empty_label: 1
  domain_invalid_chars: 1
  domain_no_dot: 1
  duplicate: 4
  duplicate_gmail_variant: 4
  local_bad_dots: 3
  local_empty: 1
  local_invalid_chars: 1
  missing_at: 1
  multiple_at: 1
  not_opted_in: 3
```

Flags on kept or rejected rows: 7 `role_account`, 4 `typo_domain` (gmial.com, hotmial.com, yaho.ca, outlok.com, each with a suggestion), 1 `dns_lookup_failed`.

9 unique domains were looked up, once each:

| Domain | Real DNS result |
| --- | --- |
| example.com | null MX (`0 .`): accepts no mail |
| example.org | null MX (`0 .`): accepts no mail |
| example.ca | NXDOMAIN |
| xn--bcher-kva.example | NXDOMAIN (the `.example` TLD does not exist) |
| gmail.com | MX (Google) |
| yaho.ca | MX (a Yahoo host) |
| hotmial.com, outlok.com | MX to the same host (`mail.h-email.net`) |
| gmial.com | SERVFAIL (`NoNameservers`): flagged, row kept |

What it shows: with real DNS, the `example.*` demo domains are (correctly) undeliverable, so 26 rows are rejected by DNS and only 7 remain. The same list with `--no-dns` keeps 33 and rejects 27. Typo domains such as hotmial.com and outlok.com **do** have MX records, so DNS alone would have passed them; the typo check is what catches them. Disposable domains were rejected before DNS, so they were not queried.

pytest: `137 passed in 0.41s`

Marvin Palencia, founder of [DeMark Studio](https://demarkstudio.ca), Miramichi, New Brunswick, Canada. Portfolio: [marvin.demarkstudio.ca](https://marvin.demarkstudio.ca)

MIT License.
