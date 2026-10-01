from __future__ import annotations

from typing import Any

from normalize import (
    normalize_lower,
    normalize_boolean,
    safe_float,
    normalize_size,
)


def extract_age_in_years(
    value: Any,
) -> float | None:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    text = normalize_lower(value)

    if not text:
        return None

    number = ""
    started = False

    for char in text:
        if char.isdigit() or char == ".":
            number += char
            started = True

        elif started:
            break

    if not number:
        return None

    parsed = safe_float(number)

    if parsed is None:
        return None

    if "week" in text:
        return parsed / 52

    if "month" in text:
        return parsed / 12

    return parsed


# =========================================================
# REQUIRED CONSTRAINT CHECKS
# =========================================================

def matches_pet_type(
    animal: dict[str, Any],
    required_value: Any,
) -> bool:
    return normalize_lower(
        animal.get("type")
    ) == normalize_lower(required_value)


def matches_breed(
    animal: dict[str, Any],
    required_value: Any,
) -> bool:
    return normalize_lower(
        animal.get("breed")
    ) == normalize_lower(required_value)


def matches_gender(
    animal: dict[str, Any],
    required_value: Any,
) -> bool:
    return normalize_lower(
        animal.get("gender")
    ) == normalize_lower(required_value)


def matches_size(
    animal: dict[str, Any],
    required_value: Any,
) -> bool:
    return normalize_size(
        animal.get("size")
    ) == normalize_size(required_value)


def matches_location(
    animal: dict[str, Any],
    required_value: Any,
) -> bool:
    """
    Location is matched case-insensitively using containment.

    Example:
        required: "Bangkok"
        animal: "Bangkok, Thailand"
    """

    required = normalize_lower(required_value)
    animal_location = normalize_lower(
        animal.get("location")
    )

    if not required or not animal_location:
        return False

    return (
        required in animal_location
        or animal_location in required
    )


def matches_age(
    animal: dict[str, Any],
    *,
    age_years: Any = None,
    age_months: Any = None,
) -> bool:
    """
    Exact age matching.

    If the user says one year, only one-year-old animals match.
    If the user says six months, only six-month-old animals match.

    A small numerical tolerance is used only for floating-point safety,
    not as a recommendation range.
    """

    animal_age_years = extract_age_in_years(
        animal.get("age")
    )

    if animal_age_years is None:
        return False

    requested_years = safe_float(
        age_years
    )

    requested_months = safe_float(
        age_months
    )

    if requested_months is not None:
        requested_years = requested_months / 12

    if requested_years is None:
        return True

    return abs(
        animal_age_years - requested_years
    ) < 0.01


# =========================================================
# ANIMAL-LEVEL FILTERING
# =========================================================

def evaluate_required_constraints(
    animal: dict[str, Any],
    required: dict[str, Any],
) -> dict[str, Any]:
    matched: list[str] = []
    failed: list[str] = []

    if "pet_type" in required:
        if matches_pet_type(
            animal,
            required["pet_type"],
        ):
            matched.append("pet_type")
        else:
            failed.append("pet_type")

    if "breed" in required:
        if matches_breed(
            animal,
            required["breed"],
        ):
            matched.append("breed")
        else:
            failed.append("breed")

    if "gender" in required:
        if matches_gender(
            animal,
            required["gender"],
        ):
            matched.append("gender")
        else:
            failed.append("gender")

    if "size" in required:
        if matches_size(
            animal,
            required["size"],
        ):
            matched.append("size")
        else:
            failed.append("size")

    if "location" in required:
        if matches_location(
            animal,
            required["location"],
        ):
            matched.append("location")
        else:
            failed.append("location")

    if (
        "age_years" in required
        or "age_months" in required
    ):
        if matches_age(
            animal,
            age_years=required.get(
                "age_years"
            ),
            age_months=required.get(
                "age_months"
            ),
        ):
            matched.append("age")
        else:
            failed.append("age")

    is_available = normalize_lower(
        animal.get(
            "adoption_status",
            "available",
        )
    ) == "available"

    if not is_available:
        failed.append(
            "adoption_status"
        )

    return {
        "is_match": not failed,
        "matched_constraints": matched,
        "failed_constraints": failed,
    }


def animal_matches_required_constraints(
    animal: dict[str, Any],
    required: dict[str, Any],
) -> bool:
    result = evaluate_required_constraints(
        animal,
        required,
    )

    return bool(
        result["is_match"]
    )


# =========================================================
# COLLECTION FILTERING
# =========================================================

def filter_animals_by_required_constraints(
    animals: list[dict[str, Any]],
    required: dict[str, Any],
) -> dict[str, Any]:
    exact_matches: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for animal in animals:
        evaluation = (
            evaluate_required_constraints(
                animal,
                required,
            )
        )

        enriched = dict(animal)

        enriched[
            "required_constraint_evaluation"
        ] = evaluation

        if evaluation["is_match"]:
            exact_matches.append(enriched)
        else:
            rejected.append(enriched)

    return {
        "exact_matches": exact_matches,
        "rejected": rejected,
        "exact_match_count": len(
            exact_matches
        ),
        "rejected_count": len(
            rejected
        ),
        "required_constraints": required,
    }


# =========================================================
# FALLBACK SUPPORT
# =========================================================

def calculate_required_match_ratio(
    animal: dict[str, Any],
    required: dict[str, Any],
) -> float:
    """
    Used later by the fallback engine.

    This does not decide whether alternatives are allowed.
    It only measures how many required constraints matched.
    """

    evaluation = evaluate_required_constraints(
        animal,
        required,
    )

    matched = len(
        evaluation[
            "matched_constraints"
        ]
    )

    failed = len(
        evaluation[
            "failed_constraints"
        ]
    )

    total = matched + failed

    if total == 0:
        return 1.0

    return round(
        matched / total,
        4,
    )


def describe_failed_constraints(
    animal: dict[str, Any],
    required: dict[str, Any],
) -> list[str]:
    evaluation = evaluate_required_constraints(
        animal,
        required,
    )

    messages: list[str] = []

    mapping = {
        "pet_type": "Pet type differs.",
        "breed": "Breed differs.",
        "gender": "Gender differs.",
        "size": "Size differs.",
        "location": "Location differs.",
        "age": "Age differs.",
        "adoption_status": (
            "Pet is not currently available."
        ),
    }

    for failed in evaluation[
        "failed_constraints"
    ]:
        message = mapping.get(
            failed,
            f"{failed.replace('_', ' ').title()} differs.",
        )

        if message not in messages:
            messages.append(message)

    return messages