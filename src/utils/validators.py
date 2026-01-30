from __future__ import annotations


def ensure_non_empty(value: str, field_name: str) -> None:
    """Raise if a required string value is empty."""
    if not value:
        raise ValueError(f"{field_name} must not be empty")
