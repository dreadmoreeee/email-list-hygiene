"""CSV outputs, summary and CLI."""

import csv
import json

from email_list_hygiene import DnsResult, Options, clean_file
from email_list_hygiene import cli, dns_check

CSV_TEXT = (
    "email,name,consent\n"
    "Pat.Demo@Example.COM,Pat,yes\n"
    "pat.demo@example.com,Pat again,yes\n"
    "info@example.org,Front desk,yes\n"
    "broken@@example.com,Bad,yes\n"
    "quit@example.ca,Quinn,no\n"
    "zq-demo-tmp@mailinator.com,Tmp,yes\n"
    "zq-demo-sam@gmial.com,Sam,yes\n"
    "zq-demo-zz.demo@gmail.com,Zed,yes\n"
    "zq-demo-zzdemo+x@googlemail.com,Zed 2,yes\n"
)


def read(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.reader(handle))


def write_input(tmp_path, text=CSV_TEXT):
    path = tmp_path / "list.csv"
    path.write_text(text, encoding="utf-8", newline="")
    return path


def lookup(domain):
    return DnsResult(dns_check.OK_MX)


def test_cleaned_and_rejected_csv_files(tmp_path):
    src = write_input(tmp_path)
    opts = Options(gmail_canonical=True)
    result, paths = clean_file(src, tmp_path / "out", opts, dns_lookup=lookup)

    cleaned = read(paths["cleaned"])
    assert cleaned[0] == ["email", "name", "consent"]  # original columns kept
    assert [r[0] for r in cleaned[1:]] == [
        "Pat.Demo@example.com", "info@example.org", "zq-demo-sam@gmial.com", "zq-demo-zz.demo@gmail.com",
    ]
    assert cleaned[1][1:] == ["Pat", "yes"]

    rejected = read(paths["rejected"])
    assert rejected[0] == ["email", "name", "consent", "reason", "suggestion"]
    by_email = {r[0]: r for r in rejected[1:]}
    assert by_email["pat.demo@example.com"][3] == "duplicate"
    assert by_email["broken@@example.com"][3] == "multiple_at"
    assert by_email["quit@example.ca"][3] == "not_opted_in"
    assert by_email["zq-demo-tmp@mailinator.com"][3] == "disposable_domain"
    assert by_email["zq-demo-zzdemo+x@googlemail.com"][3] == "duplicate_gmail_variant"
    assert len(rejected) - 1 == result.summary["rejected"] == 5


def test_multiple_reasons_are_joined_with_semicolons(tmp_path):
    src = write_input(tmp_path, "email,consent\ninfo@mailinator.com,no\n")
    _, paths = clean_file(src, tmp_path / "o", Options(reject_roles=True), dns_lookup=lookup)
    reason = read(paths["rejected"])[1][2]
    assert reason.split(";") == ["disposable_domain", "role_account", "not_opted_in"]


def test_annotate_adds_flag_columns_to_cleaned_csv(tmp_path):
    src = write_input(tmp_path)
    _, paths = clean_file(src, tmp_path / "o", Options(), annotate=True, dns_lookup=lookup)
    rows = read(paths["cleaned"])
    assert rows[0][-2:] == ["hygiene_flags", "hygiene_suggestion"]
    typo_row = [r for r in rows if r[0] == "zq-demo-sam@gmial.com"][0]
    assert typo_row[-2:] == ["typo_domain", "zq-demo-sam@gmail.com"]


def test_reason_column_name_does_not_clobber_existing_column(tmp_path):
    src = write_input(tmp_path, "email,reason\nbad,x\n")
    _, paths = clean_file(src, tmp_path / "o", Options(check_dns=False))
    assert read(paths["rejected"])[0] == ["email", "reason", "hygiene_reason", "suggestion"]


def test_bom_and_crlf_input_are_handled(tmp_path):
    src = tmp_path / "bom.csv"
    src.write_bytes(b"\xef\xbb\xbfemail,name\r\na@example.com,A\r\n")
    _, paths = clean_file(src, tmp_path / "o", Options(check_dns=False))
    assert read(paths["cleaned"]) == [["email", "name"], ["a@example.com", "A"]]


def test_summary_json_counts(tmp_path):
    src = write_input(tmp_path)
    result, paths = clean_file(
        src, tmp_path / "o", Options(gmail_canonical=True), summary_format="both", dns_lookup=lookup
    )
    data = json.loads(paths["summary_json"].read_text(encoding="utf-8"))
    assert data["total_rows"] == 9 and data["kept"] == 4 and data["rejected"] == 5
    assert data["reasons"] == {
        "disposable_domain": 1, "duplicate": 1, "duplicate_gmail_variant": 1,
        "multiple_at": 1, "not_opted_in": 1,
    }
    assert data["flags"] == {"role_account": 1, "typo_domain": 1}
    assert data["consent_column"] == "consent"
    assert "not legal advice" in data["casl_note"]
    # example.com, example.org, gmial.com, gmail.com; rejected rows are not looked up
    assert data["dns"]["unique_domains_checked"] == 4


def test_summary_markdown_content(tmp_path):
    src = write_input(tmp_path)
    _, paths = clean_file(src, tmp_path / "o", Options(), dns_lookup=lookup)
    md = paths["summary_md"].read_text(encoding="utf-8")
    assert md.startswith("# Email list hygiene summary")
    assert "| `duplicate` | 1 |" in md
    assert "zq-demo-sam@gmail.com" in md  # the typo suggestion is in the output
    assert "not legal advice" in md
    assert "No SMTP probing" in md


def test_cli_end_to_end_no_dns(tmp_path, capsys):
    src = write_input(tmp_path)
    out = tmp_path / "cli-out"
    code = cli.main([str(src), "-o", str(out), "--no-dns", "--gmail-canonical",
                     "--summary-format", "both", "--prefix", "run"])
    assert code == 0
    assert (out / "run.cleaned.csv").exists()
    assert (out / "run.rejected.csv").exists()
    assert (out / "run.summary.md").exists() and (out / "run.summary.json").exists()
    printed = capsys.readouterr().out
    assert "kept: 4" in printed and "rejected: 5" in printed


def test_cli_reports_errors(tmp_path, capsys):
    assert cli.main([str(tmp_path / "missing.csv"), "--no-dns"]) == 2
    bad = tmp_path / "nomail.csv"
    bad.write_text("name\nx\n", encoding="utf-8")
    assert cli.main([str(bad), "-o", str(tmp_path / "o"), "--no-dns"]) == 2
    assert "error:" in capsys.readouterr().err


def test_cli_module_entry_point_exists():
    import email_list_hygiene.__main__  # noqa: F401  (import must not run main)
