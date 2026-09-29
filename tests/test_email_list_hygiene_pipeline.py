"""Dedupe, roles, disposable domains, typos and consent through clean_rows."""

import pytest

from email_list_hygiene import Options, clean_rows

HEADER = ["email", "name"]


def run(addresses, **opts):
    opts.setdefault("check_dns", False)
    rows = [[a, "n"] for a in addresses]
    return clean_rows(HEADER, rows, Options(**opts))


def reasons(result):
    return [r.reasons for r in result.rows]


# --- duplicates -----------------------------------------------------------


def test_exact_duplicates_after_normalisation_keep_first():
    res = run(["Pat.Demo@example.com", " pat.demo@EXAMPLE.com ", "other@example.com"])
    assert [r.kept for r in res.rows] == [True, False, True]
    assert res.rows[1].reasons == ["duplicate"]


def test_local_part_compared_case_insensitively_but_case_kept():
    res = run(["Pat@example.com", "PAT@example.com"])
    assert res.rows[0].normalized == "Pat@example.com"
    assert res.rows[1].reasons == ["duplicate"]


def test_gmail_variants_are_distinct_without_flag():
    res = run(["zq-demo-zz.demo@gmail.com", "zq-demo-zzdemo@gmail.com", "zq-demo-zzdemo+news@gmail.com"])
    assert all(r.kept for r in res.rows)


def test_gmail_dot_plus_and_googlemail_variants_with_flag():
    res = run(
        [
            "zq-demo-zz.demo@gmail.com",
            "zq-demo-zzdemo@gmail.com",
            "zq-demo-z.z.d.e.m.o+promo@gmail.com",
            "zq-demo-ZZDEMO@googlemail.com",
            "zq-demo-zzdemo2@gmail.com",
        ],
        gmail_canonical=True,
    )
    assert [r.kept for r in res.rows] == [True, False, False, False, True]
    assert res.rows[1].reasons == ["duplicate_gmail_variant"]
    assert res.rows[3].reasons == ["duplicate_gmail_variant"]


def test_gmail_canonical_does_not_touch_other_domains():
    res = run(["a.b@example.com", "ab@example.com"], gmail_canonical=True)
    assert all(r.kept for r in res.rows)


def test_exact_duplicate_reported_as_duplicate_even_with_gmail_flag():
    res = run(["zq-demo-zz@gmail.com", "zq-demo-ZZ@gmail.com"], gmail_canonical=True)
    assert res.rows[1].reasons == ["duplicate"]


def test_first_row_wins_even_if_it_is_rejected():
    rows = [["dup@example.com", "no"], ["dup@example.com", "yes"]]
    res = clean_rows(["email", "consent"], rows, Options(check_dns=False))
    assert res.rows[0].reasons == ["not_opted_in"]
    assert "duplicate" in res.rows[1].reasons


def test_multiple_reasons_are_all_reported():
    res = run(["info@mailinator.com", "info@mailinator.com"])
    assert res.rows[1].reasons == ["disposable_domain", "duplicate"]


# --- role accounts --------------------------------------------------------


@pytest.mark.parametrize(
    "addr",
    ["info@example.com", "Sales@example.com", "no-reply@example.com", "no.reply@example.org",
     "admin+x@example.ca", "Support@example.com", "contact@example.com", "noreply@example.com"],
)
def test_role_accounts_are_flagged_by_default(addr):
    res = run([addr])
    assert res.rows[0].kept
    assert res.rows[0].flags == ["role_account"]


def test_role_accounts_can_be_rejected():
    res = run(["info@example.com", "amelie@example.com"], reject_roles=True)
    assert res.rows[0].reasons == ["role_account"]
    assert res.rows[1].kept and res.rows[1].flags == []


def test_personal_local_part_is_not_a_role():
    assert run(["information.seeker@example.com"]).rows[0].flags == []


# --- disposable -----------------------------------------------------------


def test_disposable_domains_rejected_by_default():
    res = run(["zq-demo-a@mailinator.com", "zq-demo-b@YOPMAIL.com", "c@example.com"])
    assert [r.reasons for r in res.rows] == [["disposable_domain"], ["disposable_domain"], []]


def test_disposable_subdomain_matches():
    assert run(["zq-demo-a@x.mailinator.com"]).rows[0].reasons == ["disposable_domain"]


def test_disposable_can_be_kept_and_flagged():
    res = run(["zq-demo-a@mailinator.com"], keep_disposable=True)
    assert res.rows[0].kept and res.rows[0].flags == ["disposable_domain"]


def test_disposable_list_has_source_and_date_header():
    from email_list_hygiene.data import DISPOSABLE_FILE, load_disposable_domains

    head = DISPOSABLE_FILE.read_text(encoding="ascii").splitlines()[:15]
    text = "\n".join(head)
    assert "Source:" in text and "Snapshot date:" in text
    assert "mailinator.com" in load_disposable_domains()


# --- typos ----------------------------------------------------------------


def test_typo_is_flagged_with_suggestion_but_not_fixed():
    res = run(["zq-demo-amelie@gmial.com"])
    row = res.rows[0]
    assert row.kept
    assert row.flags == ["typo_domain"]
    assert row.suggestion == "zq-demo-amelie@gmail.com"
    assert row.normalized == "zq-demo-amelie@gmial.com"  # never auto-fixed


def test_reject_typos_option():
    res = run(["zq-demo-amelie@hotmial.com"], reject_typos=True)
    assert res.rows[0].reasons == ["typo_domain"]
    assert res.rows[0].suggestion == "zq-demo-amelie@hotmail.com"


def test_fix_typos_option_applies_the_fix_and_dedupes_on_it():
    res = run(["zq-demo-amelie@gmail.com", "zq-demo-amelie@gmial.com"], fix_typos=True)
    assert res.rows[1].normalized == "zq-demo-amelie@gmail.com"
    assert "typo_fixed" in res.rows[1].flags
    assert res.rows[1].reasons == ["duplicate"]


def test_suggestion_appears_in_summary():
    res = run(["zq-demo-a@yaho.ca"])
    assert res.summary["flagged"][0]["suggestion"] == "zq-demo-a@yahoo.ca"
    assert res.summary["flags"] == {"typo_domain": 1}


# --- consent --------------------------------------------------------------


def consent_run(header, rows, **opts):
    opts.setdefault("check_dns", False)
    return clean_rows(header, rows, Options(**opts))


def test_consent_filter_keeps_only_opted_in():
    rows = [
        ["a@example.com", "yes"],
        ["b@example.com", "No"],
        ["c@example.com", "TRUE"],
        ["d@example.com", ""],
        ["e@example.com", "maybe"],
        ["f@example.com", "oui"],
    ]
    res = consent_run(["email", "opt_in"], rows)
    assert res.summary["consent_column"] == "opt_in"
    assert [r.kept for r in res.rows] == [True, False, True, False, False, True]
    assert res.rows[1].reasons == ["not_opted_in"]
    assert res.rows[3].reasons == ["consent_unknown"]
    assert res.rows[4].reasons == ["consent_unknown"]


@pytest.mark.parametrize("name", ["consent", "Subscribed", "marketing_consent", "optIn", "Opt-In", "casl_consent"])
def test_consent_column_names_detected(name):
    res = consent_run(["email", name], [["a@example.com", "no"]])
    assert res.rows[0].reasons == ["not_opted_in"]


@pytest.mark.parametrize("name", ["consent_date", "optInDate", "unsubscribed", "opt_out", "consent_source", "name"])
def test_non_flag_columns_not_detected_as_consent(name):
    res = consent_run(["email", name], [["a@example.com", "no"]])
    assert res.summary["consent_column"] is None
    assert res.rows[0].kept


def test_explicit_consent_column_and_disable_switch():
    header = ["email", "ok_to_mail"]
    rows = [["a@example.com", "no"]]
    assert consent_run(header, rows, consent_column="ok_to_mail").rows[0].reasons == ["not_opted_in"]
    assert consent_run(header, rows).rows[0].kept  # not auto-detected
    header2 = ["email", "consent"]
    assert consent_run(header2, [["a@example.com", "no"]], filter_consent=False).rows[0].kept


def test_unknown_explicit_column_raises():
    with pytest.raises(ValueError):
        consent_run(["email"], [["a@example.com"]], consent_column="nope")


def test_no_email_column_raises():
    with pytest.raises(ValueError):
        clean_rows(["name"], [["x"]], Options(check_dns=False))


def test_email_column_detection_variants():
    for name in ["Email", "E-mail", "email_address", "Courriel"]:
        res = clean_rows([name, "x"], [["a@example.com", "1"]], Options(check_dns=False))
        assert res.rows[0].kept


def test_short_rows_are_padded():
    res = clean_rows(["email", "name", "consent"], [["a@example.com"]], Options(check_dns=False))
    assert res.rows[0].reasons == ["consent_unknown"]
    assert res.rows[0].values == ["a@example.com", "", ""]
