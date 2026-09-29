import pytest

from email_list_hygiene import validate_email


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("  amelie.test@Example.COM  ", "amelie.test@example.com"),
        ("Mixed.Case@Example.Org", "Mixed.Case@example.org"),
        ("a+tag@example.ca", "a+tag@example.ca"),
        ("o'brien.demo@example.com", "o'brien.demo@example.com"),
        ("x_y-z!#$%&*/=?^`{|}~@example.com", "x_y-z!#$%&*/=?^`{|}~@example.com"),
        ("user@sub.domain.example.org", "user@sub.domain.example.org"),
        ("user@xn--bcher-kva.example", "user@xn--bcher-kva.example"),
    ],
)
def test_valid_addresses_are_normalised(raw, expected):
    assert validate_email(raw) == (expected, None)


@pytest.mark.parametrize(
    "raw,code",
    [
        ("", "empty_email"),
        ("   ", "empty_email"),
        ("no-at-sign.example.com", "missing_at"),
        ("a@b@example.com", "multiple_at"),
        ("@example.com", "local_empty"),
        (".lead@example.com", "local_bad_dots"),
        ("trail.@example.com", "local_bad_dots"),
        ("dou..ble@example.com", "local_bad_dots"),
        ("sp ace@example.com", "local_invalid_chars"),
        ('"quoted"@example.com', "local_invalid_chars"),
        ("(comment)user@example.com", "local_invalid_chars"),
        ("caf\u00e9@example.com", "local_invalid_chars"),
        ("user@", "domain_empty"),
        ("user@localhost", "domain_no_dot"),
        ("user@example..com", "domain_empty_label"),
        ("user@example.com.", "domain_empty_label"),
        ("user@.example.com", "domain_empty_label"),
        ("user@-bad.example.com", "domain_invalid_chars"),
        ("user@bad-.example.com", "domain_invalid_chars"),
        ("user@exa_mple.com", "domain_invalid_chars"),
        ("user@[192.0.2.1]", "domain_invalid_chars"),
        ("user@example.123", "domain_numeric_tld"),
        ("user@xn--zzzz-invalid-.example", "domain_invalid_chars"),
    ],
)
def test_invalid_addresses(raw, code):
    normalized, error = validate_email(raw)
    assert normalized is None
    assert error == code


def test_local_part_length_limit_is_64():
    assert validate_email("a" * 64 + "@example.com")[1] is None
    assert validate_email("a" * 65 + "@example.com") == (None, "local_too_long")


def test_label_length_limit_is_63():
    assert validate_email("u@" + "a" * 63 + ".example")[1] is None
    assert validate_email("u@" + "a" * 64 + ".example") == (None, "label_too_long")


def test_total_length_limit_is_254():
    def build(total):
        tail = "b" * 63 + "." + "c" * 63 + "."
        fill = total - 64 - 1 - len(tail) - len(".ca")
        return "a" * 64 + "@" + tail + "d" * fill + ".ca"

    exact = build(254)
    assert len(exact) == 254
    assert validate_email(exact)[1] is None
    over = build(255)
    assert len(over) == 255
    assert validate_email(over) == (None, "address_too_long")


def test_idn_domain_becomes_punycode_and_lowercase():
    normalized, error = validate_email("user@B\u00dcCHER.example")
    assert error is None
    assert normalized == "user@xn--bcher-kva.example"
    assert validate_email("user@caf\u00e9.example") == ("user@xn--caf-dma.example", None)


def test_idn_keeps_local_part_case():
    assert validate_email("Jo.Demo@Caf\u00e9.example")[0] == "Jo.Demo@xn--caf-dma.example"


def test_idn_with_bad_label_is_rejected():
    assert validate_email("user@bad\u0000name.example")[1] is not None
    assert validate_email("user@" + "\u00e9" * 64 + ".example") == (None, "label_too_long")
