"""Static data: role accounts, big providers and known typos."""

from pathlib import Path

# Role accounts, compared after removing '.', '-' and '_' and the +tag.
ROLE_LOCAL_PARTS = frozenset(
    """
    info information sales admin administrator support noreply donotreply
    contact contactus enquiries enquiry inquiries inquiry office billing
    accounts accounting postmaster webmaster hostmaster abuse root security
    marketing service services orders order newsletter press media legal
    privacy feedback reception booking bookings helpdesk help hr jobs
    careers mailer daemon mailerdaemon subscribe unsubscribe
    """.split()
)

# Big public providers, including Canadian ones.
PROVIDERS = (
    "gmail.com",
    "googlemail.com",
    "yahoo.com",
    "yahoo.ca",
    "yahoo.fr",
    "hotmail.com",
    "hotmail.ca",
    "hotmail.fr",
    "outlook.com",
    "outlook.fr",
    "live.com",
    "live.ca",
    "msn.com",
    "icloud.com",
    "me.com",
    "aol.com",
    "proton.me",
    "protonmail.com",
    "sympatico.ca",
    "videotron.ca",
    "shaw.ca",
    "rogers.com",
    "bell.net",
    "telus.net",
    "cogeco.ca",
    "eastlink.ca",
    "bellaliant.net",
)

# Real domains that sit one edit away from a provider: never flag these.
KNOWN_LEGIT_NEIGHBOURS = frozenset(
    {"rogers.ca", "gmx.com", "gmx.net", "gmx.ca", "mail.com", "yahoo.co", "live.fr", "me.ca"}
)

# Explicit typo -> correct domain. Covers short domains where fuzzy
# matching would be too risky.
TYPO_MAP = {
    "gmial.com": "gmail.com",
    "gmal.com": "gmail.com",
    "gmai.com": "gmail.com",
    "gmail.co": "gmail.com",
    "gmail.con": "gmail.com",
    "gmail.cm": "gmail.com",
    "gamil.com": "gmail.com",
    "gnail.com": "gmail.com",
    "gmali.com": "gmail.com",
    "gmaill.com": "gmail.com",
    "gmail.om": "gmail.com",
    "hotmial.com": "hotmail.com",
    "hotmal.com": "hotmail.com",
    "hotmai.com": "hotmail.com",
    "hotmail.con": "hotmail.com",
    "hotnail.com": "hotmail.com",
    "hotmial.ca": "hotmail.ca",
    "hotmail.cm": "hotmail.com",
    "yaho.ca": "yahoo.ca",
    "yaho.com": "yahoo.com",
    "yahooo.com": "yahoo.com",
    "yahoo.con": "yahoo.com",
    "yhaoo.com": "yahoo.com",
    "yahoo.cm": "yahoo.com",
    "yahho.com": "yahoo.com",
    "outlok.com": "outlook.com",
    "outloo.com": "outlook.com",
    "outlook.con": "outlook.com",
    "outook.com": "outlook.com",
    "iclod.com": "icloud.com",
    "icloud.con": "icloud.com",
    "sympatico.cs": "sympatico.ca",
    "simpatico.ca": "sympatico.ca",
    "sympatico.co": "sympatico.ca",
    "sympatco.ca": "sympatico.ca",
    "videotron.cs": "videotron.ca",
    "videotrn.ca": "videotron.ca",
    "shaw.cs": "shaw.ca",
    "shw.ca": "shaw.ca",
    "sahw.ca": "shaw.ca",
    "rogers.con": "rogers.com",
    "rogers.cm": "rogers.com",
    "rodgers.com": "rogers.com",
    "bell.ne": "bell.net",
    "bel.net": "bell.net",
    "bell.nt": "bell.net",
    "telus.ne": "telus.net",
    "tellus.net": "telus.net",
}

DISPOSABLE_FILE = Path(__file__).with_name("disposable_domains.txt")


def load_disposable_domains(path=None):
    """Read the bundled disposable-domain list (comments start with '#')."""
    domains = set()
    with open(path or DISPOSABLE_FILE, encoding="ascii") as handle:
        for line in handle:
            line = line.strip().lower()
            if line and not line.startswith("#"):
                domains.add(line)
    return frozenset(domains)
