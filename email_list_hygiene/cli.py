"""Command line interface."""

import argparse
import sys

from .core import Options
from .report import clean_file


def build_parser():
    p = argparse.ArgumentParser(
        prog="email-list-hygiene",
        description="Clean a mailing list CSV before a campaign. Sends nothing, never probes SMTP.",
    )
    p.add_argument("input", help="input CSV (UTF-8, header row required)")
    p.add_argument("-o", "--output-dir", default="hygiene-out", help="output folder (default: hygiene-out)")
    p.add_argument("--prefix", help="output file prefix (default: input file name without extension)")
    p.add_argument("--delimiter", default=",", help="CSV delimiter (default: comma)")
    p.add_argument("--email-column", help="name of the address column (auto-detected by default)")
    p.add_argument("--consent-column", help="name of the consent column (auto-detected by default)")
    p.add_argument("--no-consent-filter", action="store_true", help="ignore any consent column")
    p.add_argument("--gmail-canonical", action="store_true",
                   help="treat Gmail dot and +tag variants (and googlemail.com) as duplicates")
    p.add_argument("--reject-roles", action="store_true", help="reject role accounts instead of flagging them")
    p.add_argument("--keep-disposable", action="store_true",
                   help="flag disposable domains instead of rejecting them")
    typo = p.add_mutually_exclusive_group()
    typo.add_argument("--reject-typos", action="store_true", help="reject probable provider typos")
    typo.add_argument("--fix-typos", action="store_true",
                      help="apply the suggested provider fix in the cleaned CSV (off by default)")
    p.add_argument("--no-dns", action="store_true", help="skip MX / A / AAAA lookups")
    p.add_argument("--dns-timeout", type=float, default=5.0, help="seconds per lookup (default: 5)")
    p.add_argument("--dns-workers", type=int, default=2, help="concurrent lookups (default: 2)")
    p.add_argument("--annotate", action="store_true",
                   help="add hygiene_flags and hygiene_suggestion columns to the cleaned CSV")
    p.add_argument("--summary-format", choices=("md", "json", "both"), default="md")
    p.add_argument("-q", "--quiet", action="store_true", help="do not print the summary")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    options = Options(
        email_column=args.email_column,
        consent_column=args.consent_column,
        filter_consent=not args.no_consent_filter,
        gmail_canonical=args.gmail_canonical,
        reject_roles=args.reject_roles,
        keep_disposable=args.keep_disposable,
        reject_typos=args.reject_typos,
        fix_typos=args.fix_typos,
        check_dns=not args.no_dns,
        dns_timeout=args.dns_timeout,
        dns_workers=max(1, args.dns_workers),
    )
    try:
        result, paths = clean_file(
            args.input,
            args.output_dir,
            options,
            delimiter=args.delimiter,
            summary_format=args.summary_format,
            annotate=args.annotate,
            prefix=args.prefix,
        )
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if not args.quiet:
        s = result.summary
        print(f"rows: {s['total_rows']}  kept: {s['kept']}  rejected: {s['rejected']}")
        for code, count in s["reasons"].items():
            print(f"  {code}: {count}")
        for path in paths.values():
            print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
