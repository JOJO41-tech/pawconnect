from __future__ import annotations

from typing import Any


# =========================================================
# SHARED NORMALIZATION HELPERS
#
# Used by preference_standardizer, filter_engine, and
# scoring_engine. Keep this the single source of truth —
# these previously existed as near-identical copies in each
# module and had drifted (normalize_boolean in particular).
# =========================================================

def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalize_lower(value: Any) -> str:
    return normalize_text(value).lower()


def normalize_boolean(value: Any) -> bool:
    """
    Best-effort boolean coercion. Unrecognized input defaults to False.

    Used where a concrete bool is required, e.g. comparing an animal's
    field against a preferred boolean constraint.
    """
    if isinstance(value, bool):
        return value

    if isinstance(value, int):
        return value == 1

    return normalize_lower(value) in {"1", "true", "yes", "y"}


def normalize_boolean_or_none(value: Any) -> bool | None:
    """
    Tri-state boolean coercion: returns None when the input isn't
    recognized as a boolean, instead of silently defaulting to False.

    Used where "unrecognized" must be distinguished from "explicitly
    false", e.g. deciding whether to record a preferred constraint at
    all during preference standardization.
    """
    if value is None:
        return None

    if isinstance(value, bool):
        return value

    if isinstance(value, int):
        return value == 1

    text = normalize_lower(value)

    if text in {"true", "yes", "y", "1"}:
        return True

    if text in {"false", "no", "n", "0"}:
        return False

    return None


def normalize_list(value: Any) -> list[str]:
    if value is None:
        return []

    if isinstance(value, (list, tuple, set)):
        return [
            normalize_lower(item)
            for item in value
            if normalize_lower(item)
        ]

    text = normalize_text(value)

    if not text:
        return []

    return [
        item.strip().lower()
        for item in text.split(",")
        if item.strip()
    ]


def safe_float(value: Any) -> float | None:
    if value is None or value == "":
        return None

    try:
        return float(value)

    except (TypeError, ValueError):
        return None


def normalize_size(value: Any) -> str:
    normalized = normalize_lower(value)

    if normalized in {
        "tiny",
        "toy",
        "mini",
        "small-sized",
    }:
        return "small"

    if normalized in {
        "medium-sized",
        "mid-sized",
        "average",
    }:
        return "medium"

    if normalized in {
        "big",
        "large-sized",
        "giant",
    }:
        return "large"

    return normalized
