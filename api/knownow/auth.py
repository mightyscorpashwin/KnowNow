"""Who is calling, and may they review content?

Static Web Apps signs users in with Entra ID and forwards the identity to the
linked Function App in the ``x-ms-client-principal`` header (base64 JSON).
The Function App only accepts traffic from its Static Web App, so the header
can be trusted.
"""
from __future__ import annotations

import base64
import binascii
import json
from dataclasses import dataclass, field

REVIEWER_ROLE = "reviewer"
GROUP_CLAIM_TYPES = {"groups", "http://schemas.microsoft.com/ws/2008/06/identity/claims/groups"}
EMAIL_CLAIM_TYPES = {
    "preferred_username",
    "email",
    "upn",
    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/upn",
}


@dataclass(frozen=True)
class Principal:
    user_id: str
    user_details: str
    roles: frozenset[str] = field(default_factory=frozenset)
    claims: tuple[tuple[str, str], ...] = ()

    @property
    def is_authenticated(self) -> bool:
        return "authenticated" in self.roles

    def claim_values(self, types: set[str]) -> list[str]:
        return [val for typ, val in self.claims if typ in types]

    @property
    def emails(self) -> set[str]:
        values = {self.user_details, *self.claim_values(EMAIL_CLAIM_TYPES)}
        return {v.strip().lower() for v in values if v and "@" in v}


def parse_principal(header_value: str | None) -> Principal | None:
    """Decode the x-ms-client-principal header. Returns None if missing or malformed."""
    if not header_value:
        return None
    try:
        padded = header_value + "=" * (-len(header_value) % 4)
        data = json.loads(base64.b64decode(padded).decode("utf-8"))
    except (binascii.Error, ValueError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict) or not data.get("userId"):
        return None
    claims = tuple(
        (str(c.get("typ", "")), str(c.get("val", "")))
        for c in data.get("claims") or []
        if isinstance(c, dict)
    )
    return Principal(
        user_id=str(data["userId"]),
        user_details=str(data.get("userDetails", "")),
        roles=frozenset(str(r).lower() for r in data.get("userRoles") or []),
        claims=claims,
    )


def is_reviewer(
    principal: Principal | None,
    reviewer_emails: frozenset[str],
    reviewer_group_id: str,
) -> bool:
    if principal is None or not principal.is_authenticated:
        return False
    if REVIEWER_ROLE in principal.roles:
        return True
    if principal.emails & reviewer_emails:
        return True
    if reviewer_group_id:
        groups = {g.lower() for g in principal.claim_values(GROUP_CLAIM_TYPES)}
        if reviewer_group_id.lower() in groups:
            return True
    return False


def roles_for_login(
    payload: dict,
    reviewer_emails: frozenset[str],
    reviewer_group_id: str,
) -> list[str]:
    """Static Web Apps 'rolesSource' hook: called once at sign-in with the
    user's claims; returns extra roles to attach to the session."""
    claims = tuple(
        (str(c.get("typ", "")), str(c.get("val", "")))
        for c in payload.get("claims") or []
        if isinstance(c, dict)
    )
    principal = Principal(
        user_id=str(payload.get("userId", "")),
        user_details=str(payload.get("userDetails", "")),
        roles=frozenset({"authenticated"}),
        claims=claims,
    )
    return [REVIEWER_ROLE] if is_reviewer(principal, reviewer_emails, reviewer_group_id) else []
