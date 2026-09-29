"""email_list_hygiene: clean a mailing list CSV before a campaign.

No message is ever sent and no SMTP probing is done.
"""

from .core import CASL_NOTE, CleanResult, Options, RowResult, clean_rows
from .dns_check import DnsChecker, DnsResult
from .report import clean_file, read_csv, render_markdown, write_outputs
from .syntax import validate_email
from .typos import suggest_domain

__version__ = "0.1.0"

__all__ = [
    "CASL_NOTE",
    "CleanResult",
    "DnsChecker",
    "DnsResult",
    "Options",
    "RowResult",
    "clean_file",
    "clean_rows",
    "read_csv",
    "render_markdown",
    "suggest_domain",
    "validate_email",
    "write_outputs",
]
