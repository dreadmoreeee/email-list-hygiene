"""CSV reading/writing and the Markdown / JSON summary."""

import csv
import json
from pathlib import Path

from .core import FLAGS, REASONS, clean_rows


def read_csv(path, delimiter=","):
    """Return (header, rows). Handles a UTF-8 BOM; blank lines are skipped."""
    with open(path, newline="", encoding="utf-8-sig") as handle:
        table = [row for row in csv.reader(handle, delimiter=delimiter) if row]
    if not table:
        raise ValueError(f"{path}: empty file (no header row)")
    return table[0], table[1:]


def _unique(name, header):
    while name in header:
        name = "hygiene_" + name
    return name


def _write(path, header, rows, delimiter):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter=delimiter, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def write_outputs(result, out_dir, prefix, summary_format="md", delimiter=",", annotate=False):
    """Write cleaned / rejected CSVs and the summary. Returns the paths."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    header = result.header
    idx = result.email_index

    cleaned_header = list(header)
    if annotate:
        flags_col = _unique("hygiene_flags", header)
        sugg_col = _unique("hygiene_suggestion", header)
        cleaned_header += [flags_col, sugg_col]
    cleaned_rows = []
    for res in result.kept:
        row = list(res.values)
        row[idx] = res.normalized
        if annotate:
            row += [";".join(res.flags), res.suggestion or ""]
        cleaned_rows.append(row)

    reason_col = _unique("reason", header)
    sugg_col = _unique("suggestion", header)
    rejected_header = list(header) + [reason_col, sugg_col]
    rejected_rows = [
        list(res.values) + [";".join(res.reasons), res.suggestion or ""] for res in result.rejected
    ]

    paths = {
        "cleaned": out / f"{prefix}.cleaned.csv",
        "rejected": out / f"{prefix}.rejected.csv",
    }
    _write(paths["cleaned"], cleaned_header, cleaned_rows, delimiter)
    _write(paths["rejected"], rejected_header, rejected_rows, delimiter)
    if summary_format in ("json", "both"):
        paths["summary_json"] = out / f"{prefix}.summary.json"
        paths["summary_json"].write_text(
            json.dumps(result.summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
        )
    if summary_format in ("md", "both"):
        paths["summary_md"] = out / f"{prefix}.summary.md"
        paths["summary_md"].write_text(render_markdown(result.summary), encoding="utf-8")
    return paths


def clean_file(path, out_dir, options=None, delimiter=",", summary_format="md",
               annotate=False, dns_lookup=None, prefix=None):
    """Read ``path``, clean it and write the outputs. Returns (result, paths)."""
    header, rows = read_csv(path, delimiter)
    result = clean_rows(header, rows, options, dns_lookup=dns_lookup)
    prefix = prefix or Path(path).stem
    paths = write_outputs(result, out_dir, prefix, summary_format, delimiter, annotate)
    return result, paths


def render_markdown(summary):
    s = summary
    lines = [
        "# Email list hygiene summary",
        "",
        f"- Rows read: {s['total_rows']}",
        f"- Kept: {s['kept']}",
        f"- Rejected: {s['rejected']}",
        f"- Email column: `{s['email_column']}`",
        "- Consent column: "
        + (f"`{s['consent_column']}`" if s["consent_column"] else "none detected (no consent filtering)"),
        "",
        "## Rejected, by reason",
        "",
        "A row can have several reasons, so the counts can add up to more than the number of rejected rows.",
        "",
    ]
    if s["reasons"]:
        lines += ["| Reason | Rows | Meaning |", "| --- | ---: | --- |"]
        for code, count in s["reasons"].items():
            lines.append(f"| `{code}` | {count} | {REASONS.get(code, '')} |")
    else:
        lines.append("No rows rejected.")
    lines += ["", "## Flags", ""]
    if s["flags"]:
        lines += ["Flags never reject a row by themselves; the counts include rows rejected for other reasons.", ""]
        lines += ["| Flag | Rows | Meaning |", "| --- | ---: | --- |"]
        for code, count in s["flags"].items():
            lines.append(f"| `{code}` | {count} | {FLAGS.get(code, '')} |")
    else:
        lines.append("Nothing flagged.")
    suggestions = [f for f in s["flagged"] if f["suggestion"]]
    if suggestions:
        lines += ["", "## Typo suggestions", "", "| Row | Address | Suggested |", "| ---: | --- | --- |"]
        for item in suggestions:
            lines.append(f"| {item['row']} | {item['email']} | {item['suggestion']} |")
    lines += ["", "## DNS", ""]
    dns = s["dns"]
    if dns["enabled"]:
        lines.append(f"Unique domains looked up: {dns['unique_domains_checked']}")
        lines.append("")
        lines += ["| Domain | Result | Detail |", "| --- | --- | --- |"]
        for domain, info in dns["domains"].items():
            lines.append(f"| {domain} | `{info['status']}` | {info['detail']} |")
    else:
        lines.append("DNS checks disabled (`--no-dns`).")
    lines += ["", "## Notes", "", s["casl_note"], ""]
    lines.append("No SMTP probing is performed and no message is sent.")
    lines.append("")
    return "\n".join(lines)
