"""Resource governance vocabularies for the first-stage platform framework."""

from __future__ import annotations


GOVERNANCE_OPTIONS: dict[str, list[str]] = {
    "confidentiality": ["public", "internal", "restricted", "confidential"],
    "copyright": [
        "unknown",
        "owned",
        "licensed",
        "public_domain",
        "restricted",
        "prohibited",
    ],
    "risk": ["low", "medium", "high", "blocked"],
    "lifecycle": ["draft", "active", "archived", "expired", "deleted"],
    "permission_scope": ["organization", "project", "user", "role"],
}


def governance_snapshot() -> dict[str, list[str]]:
    return {key: list(values) for key, values in GOVERNANCE_OPTIONS.items()}
