from __future__ import annotations

from typing import Any

from filter_engine import (
    normalize_boolean,
    normalize_lower,
)


# =========================================================
# PAWCONNECT SCORING ENGINE VERSION 2.2
# CONFIDENCE-WEIGHTED PREFERRED SCORING
# =========================================================
#
# Exact matches:
#   Required constraints are already satisfied.
#   Preferred constraints determine compatibility.
#
# Alternatives:
#   Required similarity = 70%
#   Preferred compatibility = 30%
#
# ML confidence:
#   Preferred constraints detected by the ML model are
#   weighted by their prediction confidence.
#
# Example:
#   energy base weight = 20
#   ML confidence = 0.80
#   effective weight = 16
#
# Explicit/user-provided preferences without ML confidence
# receive full weight (confidence = 1.0).
# =========================================================


# =========================================================
# BASE PREFERRED CONSTRAINT WEIGHTS
# =========================================================

WEIGHTS = {
    "energy_level": 20.0,
    "temperament": 20.0,
    "apartment_friendly": 15.0,
    "experience_level": 15.0,
    "available_attention_hours": 10.0,
    "child_friendly": 10.0,
    "pet_friendly": 10.0,
}


# =========================================================
# GENERAL HELPERS
# =========================================================

def _clamp_score(score: float) -> float:
    return max(
        0.0,
        min(
            100.0,
            round(float(score), 2),
        ),
    )


def _safe_confidence(value: Any) -> float:
    """
    Convert a confidence value into the range 0.0-1.0.

    Missing confidence defaults to 1.0 so explicit preferences
    retain their full configured weight.
    """

    if value is None:
        return 1.0

    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 1.0

    return max(
        0.0,
        min(
            1.0,
            confidence,
        ),
    )


def _required_percentage(
    animal: dict[str, Any],
) -> float:
    """
    Convert required_match_ratio from 0-1 into 0-100.
    """

    try:
        ratio = float(
            animal.get(
                "required_match_ratio",
                1.0,
            )
        )
    except (TypeError, ValueError):
        ratio = 0.0

    ratio = max(
        0.0,
        min(
            1.0,
            ratio,
        ),
    )

    return round(
        ratio * 100,
        2,
    )


# =========================================================
# CONFIDENCE HELPERS
# =========================================================

def _get_confidence(
    preferred_confidence: dict[str, Any],
    *keys: str,
) -> float:
    """
    Return the first available confidence for the supplied
    classifier label names.

    If no confidence exists, return 1.0.
    """

    if not isinstance(
        preferred_confidence,
        dict,
    ):
        return 1.0

    for key in keys:
        if key in preferred_confidence:
            return _safe_confidence(
                preferred_confidence.get(key)
            )

    return 1.0


def _effective_weight(
    base_weight: float,
    confidence: float,
) -> float:
    """
    Scale a base preference weight using ML confidence.
    """

    return (
        float(base_weight)
        * _safe_confidence(confidence)
    )


def _energy_confidence(
    preferred: dict[str, Any],
    preferred_confidence: dict[str, Any],
) -> float:

    wanted = normalize_lower(
        preferred.get(
            "energy_level"
        )
    )

    if wanted == "high":
        return _get_confidence(
            preferred_confidence,
            "active",
        )

    if wanted == "medium":
        return _get_confidence(
            preferred_confidence,
            "moderate_activity",
        )

    if wanted == "low":
        return _get_confidence(
            preferred_confidence,
            "low_energy",
        )

    return 1.0


def _temperament_trait_confidence(
    trait: str,
    preferred_confidence: dict[str, Any],
) -> float:

    normalized_trait = normalize_lower(
        trait
    )

    return _get_confidence(
        preferred_confidence,
        normalized_trait,
    )


def _boolean_confidence(
    field: str,
    preferred_confidence: dict[str, Any],
) -> float:

    mappings = {
        "apartment_friendly": (
            "apartment_friendly",
        ),
        "child_friendly": (
            "good_with_children",
            "child_friendly",
        ),
        "pet_friendly": (
            "good_with_pets",
            "good_with_other_pets",
            "pet_friendly",
        ),
    }

    keys = mappings.get(
        field,
        (field,),
    )

    return _get_confidence(
        preferred_confidence,
        *keys,
    )


def _experience_confidence(
    preferred: dict[str, Any],
    preferred_confidence: dict[str, Any],
) -> float:

    wanted = normalize_lower(
        preferred.get(
            "experience_level"
        )
    )

    if wanted == "beginner":
        return _get_confidence(
            preferred_confidence,
            "beginner_owner",
        )

    if wanted == "experienced":
        return _get_confidence(
            preferred_confidence,
            "experienced_owner",
        )

    return 1.0


def _attention_confidence(
    preferred: dict[str, Any],
    preferred_confidence: dict[str, Any],
) -> float:

    wanted = preferred.get(
        "available_attention_hours"
    )

    if wanted is None:
        return 1.0

    try:
        wanted_value = float(
            wanted
        )
    except (TypeError, ValueError):
        return 1.0

    if wanted_value <= 2.0:
        return _get_confidence(
            preferred_confidence,
            "limited_time",
        )

    return _get_confidence(
        preferred_confidence,
        "plenty_time",
    )


# =========================================================
# ENERGY
# =========================================================

def score_energy(
    preferred: dict[str, Any],
    animal: dict[str, Any],
    preferred_confidence: dict[str, Any],
):
    wanted = normalize_lower(
        preferred.get(
            "energy_level"
        )
    )

    actual = normalize_lower(
        animal.get(
            "energy_level"
        )
    )

    if not wanted:
        return (
            0.0,
            0.0,
            "",
        )

    confidence = _energy_confidence(
        preferred,
        preferred_confidence,
    )

    weight = _effective_weight(
        WEIGHTS["energy_level"],
        confidence,
    )

    if wanted == actual:
        return (
            weight,
            weight,
            "Energy level matches.",
        )

    return (
        0.0,
        weight,
        "Energy level differs.",
    )


# =========================================================
# TEMPERAMENT
# =========================================================

def score_temperament(
    preferred: dict[str, Any],
    animal: dict[str, Any],
    preferred_confidence: dict[str, Any],
):
    wanted_raw = preferred.get(
        "temperament",
        [],
    )

    if isinstance(
        wanted_raw,
        str,
    ):
        wanted_raw = [
            wanted_raw
        ]

    wanted = [
        normalize_lower(item)
        for item in wanted_raw
        if item
    ]

    if not wanted:
        return (
            0.0,
            0.0,
            [],
        )

    animal_temperament = normalize_lower(
        animal.get(
            "temperament"
        )
    )

    total_confidence = 0.0
    earned_confidence = 0.0
    matched: list[str] = []

    for trait in wanted:

        confidence = (
            _temperament_trait_confidence(
                trait,
                preferred_confidence,
            )
        )

        total_confidence += confidence

        if (
            trait
            and trait
            in animal_temperament
        ):
            matched.append(
                trait
            )

            earned_confidence += confidence

    if total_confidence <= 0:
        return (
            0.0,
            0.0,
            matched,
        )

    average_confidence = (
        total_confidence
        / len(wanted)
    )

    weight = _effective_weight(
        WEIGHTS["temperament"],
        average_confidence,
    )

    matched_ratio = (
        earned_confidence
        / total_confidence
    )

    score = (
        matched_ratio
        * weight
    )

    return (
        score,
        weight,
        matched,
    )


# =========================================================
# BOOLEAN PREFERENCES
# =========================================================

def score_boolean(
    field: str,
    preferred: dict[str, Any],
    animal: dict[str, Any],
    base_weight: float,
    preferred_confidence: dict[str, Any],
):
    if field not in preferred:
        return (
            0.0,
            0.0,
        )

    preferred_value = normalize_boolean(
        preferred[field]
    )

    animal_value = normalize_boolean(
        animal.get(
            field
        )
    )

    confidence = _boolean_confidence(
        field,
        preferred_confidence,
    )

    weight = _effective_weight(
        base_weight,
        confidence,
    )

    if (
        preferred_value
        == animal_value
    ):
        return (
            weight,
            weight,
        )

    return (
        0.0,
        weight,
    )


# =========================================================
# EXPERIENCE
# =========================================================

def score_experience(
    preferred: dict[str, Any],
    animal: dict[str, Any],
    preferred_confidence: dict[str, Any],
):
    wanted = normalize_lower(
        preferred.get(
            "experience_level"
        )
    )

    if not wanted:
        return (
            0.0,
            0.0,
        )

    actual = normalize_lower(
        animal.get(
            "experience_required"
        )
    )

    confidence = _experience_confidence(
        preferred,
        preferred_confidence,
    )

    weight = _effective_weight(
        WEIGHTS["experience_level"],
        confidence,
    )

    if wanted == actual:
        return (
            weight,
            weight,
        )

    return (
        0.0,
        weight,
    )


# =========================================================
# ATTENTION HOURS
# =========================================================

def score_attention(
    preferred: dict[str, Any],
    animal: dict[str, Any],
    preferred_confidence: dict[str, Any],
):
    wanted = preferred.get(
        "available_attention_hours"
    )

    if wanted is None:
        return (
            0.0,
            0.0,
        )

    confidence = _attention_confidence(
        preferred,
        preferred_confidence,
    )

    weight = _effective_weight(
        WEIGHTS[
            "available_attention_hours"
        ],
        confidence,
    )

    try:
        wanted_value = float(
            wanted
        )

        actual_value = float(
            animal.get(
                "daily_attention_hours",
                0,
            )
        )

    except (TypeError, ValueError):
        return (
            0.0,
            weight,
        )

    if actual_value <= wanted_value:
        return (
            weight,
            weight,
        )

    return (
        0.0,
        weight,
    )


# =========================================================
# PREFERRED / LIFESTYLE SCORE
# =========================================================

def calculate_preferred_score(
    animal: dict[str, Any],
    preferred: dict[str, Any],
    preferred_confidence: dict[str, Any] | None = None,
) -> dict[str, Any]:

    preferred_confidence = (
        preferred_confidence
        or {}
    )

    earned = 0.0
    possible = 0.0

    matched: list[str] = []
    missing: list[str] = []

    # -----------------------------------------------------
    # Energy
    # -----------------------------------------------------

    score, weight, message = score_energy(
        preferred,
        animal,
        preferred_confidence,
    )

    earned += score
    possible += weight

    if weight:

        if score:
            matched.append(
                message
            )

        else:
            missing.append(
                message
            )

    # -----------------------------------------------------
    # Temperament
    # -----------------------------------------------------

    (
        score,
        weight,
        matched_temperaments,
    ) = score_temperament(
        preferred,
        animal,
        preferred_confidence,
    )

    earned += score
    possible += weight

    if weight:

        if matched_temperaments:

            matched.extend(
                [
                    f"Temperament: {trait}"
                    for trait
                    in matched_temperaments
                ]
            )

        if score < weight:

            missing.append(
                "Some preferred temperament "
                "traits differ."
            )

    # -----------------------------------------------------
    # Boolean preferences
    # -----------------------------------------------------

    boolean_fields = [
        "apartment_friendly",
        "child_friendly",
        "pet_friendly",
    ]

    for field in boolean_fields:

        score, weight = score_boolean(
            field,
            preferred,
            animal,
            WEIGHTS[field],
            preferred_confidence,
        )

        earned += score
        possible += weight

        if weight:

            readable_name = (
                field
                .replace(
                    "_",
                    " ",
                )
                .title()
            )

            if score:

                matched.append(
                    readable_name
                )

            else:

                missing.append(
                    f"{readable_name} differs."
                )

    # -----------------------------------------------------
    # Experience
    # -----------------------------------------------------

    score, weight = score_experience(
        preferred,
        animal,
        preferred_confidence,
    )

    earned += score
    possible += weight

    if weight:

        if score:

            matched.append(
                "Experience level matches."
            )

        else:

            missing.append(
                "Experience level differs."
            )

    # -----------------------------------------------------
    # Daily attention
    # -----------------------------------------------------

    score, weight = score_attention(
        preferred,
        animal,
        preferred_confidence,
    )

    earned += score
    possible += weight

    if weight:

        if score:

            matched.append(
                "Daily attention requirement "
                "fits your availability."
            )

        else:

            missing.append(
                "Daily attention requirement "
                "may exceed your availability."
            )

    # -----------------------------------------------------
    # Convert to percentage
    # -----------------------------------------------------

    if possible > 0:

        preferred_percentage = (
            earned
            / possible
        ) * 100

    else:

        preferred_percentage = 0.0

    return {
        "earned_weight": round(
            earned,
            2,
        ),

        "possible_weight": round(
            possible,
            2,
        ),

        "preferred_percentage": (
            _clamp_score(
                preferred_percentage
            )
        ),

        "has_preferred_constraints": (
            possible > 0
        ),

        "matched_preferences": matched,

        "missing_preferences": missing,
    }


# =========================================================
# FINAL COMPATIBILITY CALCULATION
# =========================================================

def calculate_final_compatibility(
    *,
    animal: dict[str, Any],
    preferred_percentage: float,
    has_preferred_constraints: bool,
) -> float:
    """
    Calculate final compatibility.

    EXACT MATCH:
        No preferred constraints -> 100%
        Preferred constraints -> preferred score

    ALTERNATIVE:
        No preferred constraints ->
            required-match percentage

        Preferred constraints ->
            70% required similarity
            30% preferred compatibility
    """

    mode = normalize_lower(
        animal.get(
            "recommendation_mode",
            "exact",
        )
    )

    required_percentage = (
        _required_percentage(
            animal
        )
    )

    # -----------------------------------------------------
    # Exact match
    # -----------------------------------------------------

    if mode == "exact":

        if not has_preferred_constraints:
            return 100.0

        return _clamp_score(
            preferred_percentage
        )

    # -----------------------------------------------------
    # Alternative
    # -----------------------------------------------------

    if mode == "alternative":

        if not has_preferred_constraints:

            return _clamp_score(
                required_percentage
            )

        required_component = (
            required_percentage
            * 0.70
        )

        preferred_component = (
            preferred_percentage
            * 0.30
        )

        return _clamp_score(
            required_component
            + preferred_component
        )

    # -----------------------------------------------------
    # Safe fallback
    # -----------------------------------------------------

    if has_preferred_constraints:

        return _clamp_score(
            preferred_percentage
        )

    return _clamp_score(
        required_percentage
    )


# =========================================================
# MAIN ANIMAL SCORER
# =========================================================

def score_animal(
    animal: dict[str, Any],
    preferred: dict[str, Any],
    preferred_confidence: dict[str, Any] | None = None,
) -> dict[str, Any]:

    preferred_confidence = (
        preferred_confidence
        or {}
    )

    preferred_result = (
        calculate_preferred_score(
            animal,
            preferred,
            preferred_confidence,
        )
    )

    preferred_percentage = (
        preferred_result[
            "preferred_percentage"
        ]
    )

    has_preferred = (
        preferred_result[
            "has_preferred_constraints"
        ]
    )

    required_percentage = (
        _required_percentage(
            animal
        )
    )

    compatibility = (
        calculate_final_compatibility(
            animal=animal,
            preferred_percentage=(
                preferred_percentage
            ),
            has_preferred_constraints=(
                has_preferred
            ),
        )
    )

    result = dict(
        animal
    )

    result[
        "compatibility_score"
    ] = compatibility

    result[
        "required_match_percentage"
    ] = required_percentage

    result[
        "preferred_match_percentage"
    ] = preferred_percentage

    result[
        "matched_preferences"
    ] = preferred_result[
        "matched_preferences"
    ]

    result[
        "missing_preferences"
    ] = preferred_result[
        "missing_preferences"
    ]

    result[
        "earned_weight"
    ] = preferred_result[
        "earned_weight"
    ]

    result[
        "possible_weight"
    ] = preferred_result[
        "possible_weight"
    ]

    result[
        "confidence_weighting_applied"
    ] = bool(
        preferred_confidence
    )

    return result


# =========================================================
# CANDIDATE RANKING
# =========================================================

def rank_candidates(
    candidates: list[
        dict[str, Any]
    ],
    preferred: dict[str, Any],
    preferred_confidence: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Score and rank recommendation candidates.

    Ranking priority:

    1. Higher compatibility score
    2. Higher required-constraint match ratio
    3. Fewer failed required constraints
    4. Lower numeric animal ID
    5. Alphabetical animal name

    The final two rules provide deterministic tie-breaking
    so repeated experiments return the same ordering.
    """

    preferred_confidence = (
        preferred_confidence
        or {}
    )

    scored = [
        score_animal(
            animal,
            preferred,
            preferred_confidence,
        )
        for animal in candidates
    ]

    def safe_id(
        animal: dict[str, Any],
    ) -> tuple[int, str]:
        """
        Create a deterministic sortable ID.

        Numeric IDs are sorted numerically.
        Non-numeric IDs are sorted as text.
        """

        value = animal.get(
            "id",
            "",
        )

        try:
            return (
                0,
                f"{int(value):020d}",
            )

        except (
            TypeError,
            ValueError,
        ):
            return (
                1,
                str(value).strip().lower(),
            )

    def ranking_key(
        animal: dict[str, Any],
    ):
        compatibility = float(
            animal.get(
                "compatibility_score",
                0,
            )
        )

        required_ratio = float(
            animal.get(
                "required_match_ratio",
                0,
            )
        )

        failed_count = len(
            animal.get(
                "failed_required_constraints",
                [],
            )
        )

        animal_id = safe_id(
            animal
        )

        animal_name = str(
            animal.get(
                "name",
                "",
            )
        ).strip().lower()

        return (
            -compatibility,
            -required_ratio,
            failed_count,
            animal_id,
            animal_name,
        )

    scored.sort(
        key=ranking_key
    )

    return scored