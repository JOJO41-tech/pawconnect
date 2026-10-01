from __future__ import annotations

from typing import Any

from filter_engine import (
    calculate_required_match_ratio,
    describe_failed_constraints,
    evaluate_required_constraints,
    normalize_lower,
)


# =========================================================
# FALLBACK ENGINE VERSION 2.2
# =========================================================


# =========================================================
# BASIC HELPERS
# =========================================================

def alternatives_are_allowed(
    preference_profile: dict[str, Any],
) -> bool:
    """
    Allow transparent alternatives whenever the user
    supplied at least one meaningful constraint.

    Alternatives are never presented as exact matches.
    Any failed relaxable constraints are shown clearly.

    IMPORTANT:
    pet_type is never relaxed.
    """

    required = preference_profile.get(
        "required",
        {},
    )

    preferred = preference_profile.get(
        "preferred",
        {},
    )

    has_required = (
        isinstance(required, dict)
        and bool(required)
    )

    has_preferred = (
        isinstance(preferred, dict)
        and bool(preferred)
    )

    return has_required or has_preferred


def has_required_constraints(
    preference_profile: dict[str, Any],
) -> bool:
    required = preference_profile.get(
        "required",
        {},
    )

    return (
        isinstance(required, dict)
        and bool(required)
    )


def is_available(
    animal: dict[str, Any],
) -> bool:
    return (
        normalize_lower(
            animal.get(
                "adoption_status",
                "available",
            )
        )
        == "available"
    )


def get_animal_pet_type(
    animal: dict[str, Any],
) -> str:
    """
    Return the animal's normalized pet type.

    Supports both:
        pet_type
        type

    because PawConnect animal records may use
    either field name.
    """

    return normalize_lower(
        animal.get(
            "pet_type",
            animal.get(
                "type",
                "",
            ),
        )
    )


def satisfies_non_relaxable_constraints(
    animal: dict[str, Any],
    required: dict[str, Any],
) -> bool:
    """
    Check constraints that must NEVER be relaxed.

    Currently:
        pet_type

    Example:
        required pet_type = dog

    A cat will return False and will never enter
    the alternative ranking stage.
    """

    required_pet_type = normalize_lower(
        required.get(
            "pet_type",
            ""
        )
    )

    if required_pet_type:

        animal_pet_type = (
            get_animal_pet_type(
                animal
            )
        )

        if (
            animal_pet_type
            != required_pet_type
        ):
            return False

    return True


# =========================================================
# USER-FACING FORMATTING
# =========================================================

def format_required_value(
    key: str,
    value: Any,
) -> str:

    if key == "age_years":
        number = float(value)

        if number.is_integer():
            number = int(number)

        unit = (
            "year"
            if number == 1
            else "years"
        )

        return f"{number} {unit} old"

    if key == "age_months":
        number = float(value)

        if number.is_integer():
            number = int(number)

        unit = (
            "month"
            if number == 1
            else "months"
        )

        return f"{number} {unit} old"

    if isinstance(value, str):
        return value

    return str(value)


def build_no_exact_match_message(
    required: dict[str, Any],
) -> str:

    if not required:
        return (
            "No suitable pets are currently available."
        )

    parts: list[str] = []

    display_order = [
        "breed",
        "pet_type",
        "age_years",
        "age_months",
        "gender",
        "size",
        "location",
    ]

    for key in display_order:

        if key not in required:
            continue

        value = format_required_value(
            key,
            required[key],
        )

        if key == "breed":
            parts.append(
                value
            )

        elif key == "pet_type":
            parts.append(
                value
            )

        elif key in {
            "age_years",
            "age_months",
        }:
            parts.append(
                value
            )

        elif key == "gender":
            parts.append(
                value
            )

        elif key == "size":
            parts.append(
                f"{value} size"
            )

        elif key == "location":
            parts.append(
                f"in {value}"
            )

    if not parts:
        return (
            "No pet currently matches all "
            "required constraints."
        )

    requirement_text = ", ".join(
        parts
    )

    return (
        "No available pet currently matches all "
        f"requested requirements: {requirement_text}."
    )


def build_no_pet_type_match_message(
    required: dict[str, Any],
) -> str:
    """
    Build a specific message when the requested
    pet type has no valid alternatives.
    """

    pet_type = normalize_lower(
        required.get(
            "pet_type",
            ""
        )
    )

    if not pet_type:
        return (
            "No available pets could be used "
            "as suitable alternatives."
        )

    if pet_type == "dog":
        plural_pet_type = "dogs"

    elif pet_type == "cat":
        plural_pet_type = "cats"

    else:
        plural_pet_type = f"{pet_type}s"

    return (
        f"No available {plural_pet_type} currently "
        "match your request. Try changing your "
        "preferences or check again later."
    )


def build_alternative_notice(
    required: dict[str, Any],
) -> str:

    base = build_no_exact_match_message(
        required
    )

    return (
        f"{base} "
        "Showing the closest available alternatives. "
        "Any required constraints that do not match "
        "are listed clearly."
    )


# =========================================================
# ALTERNATIVE PREPARATION
# =========================================================

def prepare_alternative_candidate(
    animal: dict[str, Any],
    required: dict[str, Any],
) -> dict[str, Any]:

    evaluation = (
        evaluate_required_constraints(
            animal,
            required,
        )
    )

    result = dict(
        animal
    )

    match_ratio = (
        calculate_required_match_ratio(
            animal,
            required,
        )
    )

    failed_constraints = list(
        evaluation.get(
            "failed_constraints",
            [],
        )
    )

    failed_messages = (
        describe_failed_constraints(
            animal,
            required,
        )
    )

    result[
        "required_constraint_evaluation"
    ] = evaluation

    result[
        "required_match_ratio"
    ] = match_ratio

    result[
        "failed_required_constraints"
    ] = failed_constraints

    result[
        "failed_required_messages"
    ] = failed_messages

    result[
        "is_exact_match"
    ] = False

    result[
        "recommendation_mode"
    ] = "alternative"

    return result


def build_alternative_candidates(
    animals: list[dict[str, Any]],
    required: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Build alternatives from available pets only.

    NON-RELAXABLE:
        pet_type

    RELAXABLE:
        breed
        age
        gender
        size
        location
        and other normal matching constraints

    Example:

        User:
            "I want a dog."

        Database:
            Leo  = cat
            Loki = cat
            Maya = cat

        Result:
            []

    Cats must never be presented as alternatives
    when the user explicitly requested a dog.
    """

    alternatives: list[
        dict[str, Any]
    ] = []

    for animal in animals:

        # -------------------------------------------------
        # Only available animals can be recommended
        # -------------------------------------------------

        if not is_available(
            animal
        ):
            continue

        # -------------------------------------------------
        # HARD / NON-RELAXABLE CONSTRAINTS
        # -------------------------------------------------

        if not satisfies_non_relaxable_constraints(
            animal,
            required,
        ):
            continue

        # -------------------------------------------------
        # Evaluate required constraints
        # -------------------------------------------------

        evaluation = (
            evaluate_required_constraints(
                animal,
                required,
            )
        )

        # -------------------------------------------------
        # Exact matches are handled before fallback.
        # -------------------------------------------------

        if evaluation.get(
            "is_match",
            False,
        ):
            continue

        candidate = (
            prepare_alternative_candidate(
                animal,
                required,
            )
        )

        alternatives.append(
            candidate
        )

    return alternatives


# =========================================================
# ALTERNATIVE SORTING
# =========================================================

def sort_alternatives_by_required_similarity(
    alternatives: list[
        dict[str, Any]
    ],
) -> list[dict[str, Any]]:
    """
    Rank alternatives by how many required constraints
    they satisfy.

    Higher required_match_ratio is better.
    Fewer failed constraints is better.

    pet_type mismatches never reach this stage.

    Example:

        Requested:
            cat
            Sphynx
            3 years
            male
            Chiang Mai

        Sasha:
            cat ✓
            Sphynx ✓
            3 years ✓
            male ✗
            Chiang Mai ✗

        Sasha receives a 3/5 required-match ratio and
        should rank above a pet matching only 1/5.
    """

    return sorted(
        alternatives,
        key=lambda animal: (
            float(
                animal.get(
                    "required_match_ratio",
                    0,
                )
            ),
            -len(
                animal.get(
                    "failed_required_constraints",
                    [],
                )
            ),
        ),
        reverse=True,
    )


# =========================================================
# EXACT MATCH PREPARATION
# =========================================================

def prepare_exact_matches(
    exact_matches: list[
        dict[str, Any]
    ],
) -> list[dict[str, Any]]:

    prepared: list[
        dict[str, Any]
    ] = []

    for animal in exact_matches:

        item = dict(
            animal
        )

        item[
            "is_exact_match"
        ] = True

        item[
            "recommendation_mode"
        ] = "exact"

        item[
            "required_match_ratio"
        ] = 1.0

        item[
            "failed_required_constraints"
        ] = []

        item[
            "failed_required_messages"
        ] = []

        prepared.append(
            item
        )

    return prepared


# =========================================================
# FALLBACK DECISION ENGINE
# =========================================================

def resolve_fallback(
    *,
    animals: list[dict[str, Any]],
    preference_profile: dict[str, Any],
    exact_matches: list[
        dict[str, Any]
    ],
) -> dict[str, Any]:
    """
    Decide whether PawConnect returns:

    1. Exact matches
    2. Transparent closest alternatives
    3. No results

    IMPORTANT:

    pet_type is a non-relaxable constraint.

    If the user explicitly requests a dog,
    cats are removed before alternative ranking.

    Other constraints may still be relaxed and
    transparently explained to the user.
    """

    required = preference_profile.get(
        "required",
        {},
    )

    preferred = preference_profile.get(
        "preferred",
        {},
    )

    if not isinstance(
        required,
        dict,
    ):
        required = {}

    if not isinstance(
        preferred,
        dict,
    ):
        preferred = {}

    # -----------------------------------------------------
    # CASE 1
    # Exact matches exist
    # -----------------------------------------------------

    if exact_matches:

        prepared_exact = (
            prepare_exact_matches(
                exact_matches
            )
        )

        return {
            "mode": "exact",

            "candidates": (
                prepared_exact
            ),

            "message": (
                "Exact matches were found."
            ),

            "alternatives_allowed": False,

            "required_constraints": (
                required
            ),

            "preferred_constraints": (
                preferred
            ),
        }

    # -----------------------------------------------------
    # CASE 2
    # No meaningful constraints
    # -----------------------------------------------------

    if not alternatives_are_allowed(
        preference_profile
    ):

        return {
            "mode": "no_match",

            "candidates": [],

            "message": (
                build_no_exact_match_message(
                    required
                )
            ),

            "alternatives_allowed": False,

            "required_constraints": (
                required
            ),

            "preferred_constraints": (
                preferred
            ),
        }

    # -----------------------------------------------------
    # CASE 3
    # Build closest alternatives
    # -----------------------------------------------------

    alternatives = (
        build_alternative_candidates(
            animals,
            required,
        )
    )

    # -----------------------------------------------------
    # CASE 4
    # No valid alternatives remain
    #
    # This is especially important when pet_type
    # removes every animal.
    # -----------------------------------------------------

    if not alternatives:

        if normalize_lower(
            required.get(
                "pet_type",
                ""
            )
        ):

            message = (
                build_no_pet_type_match_message(
                    required
                )
            )

        else:

            message = (
                "No available pets could be used "
                "as suitable alternatives."
            )

        return {
            "mode": "no_match",

            "candidates": [],

            "message": message,

            "alternatives_allowed": False,

            "required_constraints": (
                required
            ),

            "preferred_constraints": (
                preferred
            ),
        }

    # -----------------------------------------------------
    # CASE 5
    # Rank valid alternatives.
    #
    # At this point every candidate already satisfies
    # the non-relaxable pet_type constraint.
    # -----------------------------------------------------

    alternatives = (
        sort_alternatives_by_required_similarity(
            alternatives
        )
    )

    return {
        "mode": "alternative",

        "candidates": alternatives,

        "message": (
            build_alternative_notice(
                required
            )
        ),

        "alternatives_allowed": True,

        "required_constraints": (
            required
        ),

        "preferred_constraints": (
            preferred
        ),
    }