import base64
import json

from knownow.auth import is_reviewer, parse_principal, roles_for_login


def header(**overrides) -> str:
    data = {
        "identityProvider": "aad",
        "userId": "u1",
        "userDetails": "Asha@Contoso.com",
        "userRoles": ["anonymous", "authenticated"],
        "claims": [{"typ": "groups", "val": "GROUP-1"}],
    }
    data.update(overrides)
    return base64.b64encode(json.dumps(data).encode()).decode().rstrip("=")


def test_parse_principal_handles_missing_padding():
    p = parse_principal(header())
    assert p is not None and p.user_id == "u1" and p.is_authenticated


def test_parse_principal_rejects_garbage():
    assert parse_principal(None) is None
    assert parse_principal("not-base64!!") is None
    assert parse_principal(base64.b64encode(b"[]").decode()) is None


def test_reviewer_by_email_case_insensitive():
    p = parse_principal(header())
    assert is_reviewer(p, frozenset({"asha@contoso.com"}), "")


def test_reviewer_by_group():
    p = parse_principal(header())
    assert is_reviewer(p, frozenset(), "group-1")


def test_reviewer_by_role():
    p = parse_principal(header(userRoles=["authenticated", "reviewer"], claims=[]))
    assert is_reviewer(p, frozenset(), "")


def test_not_reviewer_when_anonymous_or_unlisted():
    anon = parse_principal(header(userRoles=["anonymous"]))
    assert not is_reviewer(anon, frozenset({"asha@contoso.com"}), "")
    other = parse_principal(header(userDetails="bob@contoso.com", claims=[]))
    assert not is_reviewer(other, frozenset({"asha@contoso.com"}), "group-1")


def test_roles_source_payload():
    payload = {
        "userId": "u1",
        "userDetails": "x",
        "claims": [{"typ": "preferred_username", "val": "asha@contoso.com"}],
    }
    assert roles_for_login(payload, frozenset({"asha@contoso.com"}), "") == ["reviewer"]
    assert roles_for_login(payload, frozenset(), "") == []
