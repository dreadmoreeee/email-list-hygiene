# Email list hygiene summary

- Rows read: 60
- Kept: 7
- Rejected: 53
- Email column: `email`
- Consent column: `consent`

## Rejected, by reason

A row can have several reasons, so the counts can add up to more than the number of rejected rows.

| Reason | Rows | Meaning |
| --- | ---: | --- |
| `consent_unknown` | 2 | Consent value empty or not recognised |
| `disposable_domain` | 3 | Disposable email domain |
| `dns_null_mx` | 18 | Domain publishes a null MX (accepts no mail) |
| `dns_nxdomain` | 8 | Domain does not exist |
| `domain_empty` | 1 | Empty domain |
| `domain_empty_label` | 1 | Domain has an empty label (leading, trailing or double dot) |
| `domain_invalid_chars` | 1 | Domain label has invalid characters or hyphens in the wrong place |
| `domain_no_dot` | 1 | Domain has no dot (single label) |
| `duplicate` | 4 | Duplicate of an earlier row |
| `duplicate_gmail_variant` | 4 | Gmail dot/+tag variant of an earlier row |
| `local_bad_dots` | 3 | Local part starts/ends with a dot or has consecutive dots |
| `local_empty` | 1 | Empty local part |
| `local_invalid_chars` | 1 | Local part has characters outside the supported dot-atom subset |
| `missing_at` | 1 | No @ sign |
| `multiple_at` | 1 | More than one @ sign |
| `not_opted_in` | 3 | Consent column says not opted in |

## Flags

Flags never reject a row by themselves; the counts include rows rejected for other reasons.

| Flag | Rows | Meaning |
| --- | ---: | --- |
| `dns_lookup_failed` | 1 | DNS lookup failed or timed out; address kept |
| `role_account` | 7 | Role account (kept) |
| `typo_domain` | 4 | Probable typo of a big provider domain (kept, see suggestion) |

## Typo suggestions

| Row | Address | Suggested |
| ---: | --- | --- |
| 46 | zq-demo-garrick.ness@gmial.com | zq-demo-garrick.ness@gmail.com |
| 47 | zq-demo-petra.lund@hotmial.com | zq-demo-petra.lund@hotmail.com |
| 48 | zq-demo-alder.quist@yaho.ca | zq-demo-alder.quist@yahoo.ca |
| 49 | zq-demo-sorrel.vane@outlok.com | zq-demo-sorrel.vane@outlook.com |

## DNS

Unique domains looked up: 9

| Domain | Result | Detail |
| --- | --- | --- |
| example.ca | `nxdomain` | domain does not exist |
| example.com | `null_mx` | null MX (RFC 7505): domain accepts no mail |
| example.org | `null_mx` | null MX (RFC 7505): domain accepts no mail |
| gmail.com | `ok_mx` | alt1.gmail-smtp-in.l.google.com, alt2.gmail-smtp-in.l.google.com, alt3.gmail-smtp-in.l.google.com, alt4.gmail-smtp-in.l.google.com, gmail-smtp-in.l.google.com |
| gmial.com | `error` | NoNameservers |
| hotmial.com | `ok_mx` | mail.h-email.net |
| outlok.com | `ok_mx` | mail.h-email.net |
| xn--bcher-kva.example | `nxdomain` | domain does not exist |
| yaho.ca | `ok_mx` | e.mx.mail.yahoo.com |

## Notes

CASL note: this tool filters on the consent column you supply; it cannot verify that consent is valid, express or implied, or documented. This is not legal advice; check Canada's Anti-Spam Legislation (CASL) and your own records before sending.

No SMTP probing is performed and no message is sent.
