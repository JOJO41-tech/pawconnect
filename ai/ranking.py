from __future__ import annotations

from typing import Any

from explanation_engine import (
    build_no_match_response,
    build_success_response,
)
from fallback_engine import resolve_fallback
from filter_engine import (
    filter_animals_by_required_constraints,
)
from scoring_engine import rank_candidates


# =========================================================
# PREFERENCE PROFILE NORMALIZATION
# =========================================================

def _coerce_preference_profile(
    preferences: dict[str, Any] | None,
) -> dict[str, Any]:
    preferences = preferences or {}

    if (
        isinstance(preferences.get("required"), dict)
        and isinstance(preferences.get("preferred"), dict)
    ):
        return {
            "required": dict(
                preferences["required"]
            ),
            "preferred": dict(
                preferences["preferred"]
            ),
            "metadata": dict(
                preferences.get(
                    "metadata",
                    {},
                )
            ),
        }

    required: dict[str, Any] = {}
    preferred: dict[str, Any] = {}

    required_fields = (
        "pet_type",
        "breed",
        "gender",
        "size",
        "location",
        "age_years",
        "age_months",
    )

    for field in required_fields:
        value = preferences.get(field)

        if (
            value is not None
            and value != ""
        ):
            required[field] = value

    preferred_fields = (
        "energy_level",
        "apartment_friendly",
        "child_friendly",
        "pet_friendly",
        "experience_level",
        "available_attention_hours",
    )

    for field in preferred_fields:
        value = preferences.get(field)

        if (
            value is not None
            and value != ""
        ):
            preferred[field] = value

    temperament = preferences.get(
        "temperament_traits"
    )

    if temperament:
        preferred[
            "temperament"
        ] = temperament

    metadata = preferences.get(
        "metadata",
        {},
    )

    if not isinstance(
        metadata,
        dict,
    ):
        metadata = {}

    return {
        "required": required,
        "preferred": preferred,
        "metadata": {
            **metadata,

            "model": metadata.get(
                "model",
                preferences.get(
                    "system_type",
                    "ml",
                ),
            ),

            "schema_version": metadata.get(
                "schema_version",
                "1.0",
            ),

            "legacy_profile_converted": True,
        },
    }


# =========================================================
# ATTACH EXPLANATION CONTEXT
# =========================================================

def _attach_explanation_context(
    recommendations: list[dict[str, Any]],
    required: dict[str, Any],
    preferred: dict[str, Any],
    mode: str,
) -> list[dict[str, Any]]:
    """
    Attach the user's actual constraints to each
    recommendation before explanation generation.
    """

    for recommendation in recommendations:

        if mode == "exact":
            recommendation[
                "required_constraints"
            ] = dict(required)

        else:
            recommendation.setdefault(
                "required_constraints",
                {},
            )

        recommendation[
            "preferred_constraints"
        ] = dict(preferred)

        recommendation[
            "recommendation_mode"
        ] = mode

    return recommendations


# =========================================================
# WEBSITE COMPATIBILITY FIELDS
# =========================================================

def _apply_api_compatibility_fields(
    recommendations: list[dict[str, Any]],
) -> list[dict[str, Any]]:

    for animal in recommendations:

        score = float(
            animal.get(
                "compatibility_score",
                0,
            )
        )

        animal[
            "match_score"
        ] = score

        animal[
            "matchPercentage"
        ] = score

        matched = list(
            animal.get(
                "matched_preferences",
                [],
            )
        )

        missing = list(
            animal.get(
                "missing_preferences",
                [],
            )
        )

        failed_required = list(
            animal.get(
                "failed_required_messages",
                [],
            )
        )

        animal[
            "reasons"
        ] = matched

        animal[
            "matchReasons"
        ] = matched

        animal[
            "concerns"
        ] = (
            failed_required
            + missing
        )

    return recommendations


# =========================================================
# EMPTY RESULT
# =========================================================

def _build_empty_ranking_result(
    *,
    message: str,
    total_scored: int,
    mode: str,
    preference_profile: dict[str, Any],
) -> dict[str, Any]:

    response = build_no_match_response(
        message
    )

    return {
        **response,

        "best_match": None,

        "other_recommendations": [],

        "recommendations": [],

        "total_scored": (
            total_scored
        ),

        "mode": mode,

        "preference_profile": (
            preference_profile
        ),
    }


# =========================================================
# MAIN RANKING ENGINE
# =========================================================

def rank_animals(
    animals: list[dict[str, Any]],
    preferences: dict[str, Any],
    recommendation_limit: int = 4,
) -> dict[str, Any]:
    """
    PawConnect Ranking Engine v2.3

    Pipeline:
      1. Normalize preference profile.
      2. Read preferred confidence.
      3. Fall back to raw ML confidence when needed.
      4. Filter required constraints.
      5. Resolve exact / alternative / no-match mode.
      6. Rank candidates.
      7. Apply confidence-aware preferred scoring.
      8. Attach explanation context.
      9. Generate explanations.
      10. Preserve website API compatibility.
    """

    # -----------------------------------------------------
    # Validate inputs
    # -----------------------------------------------------

    if not isinstance(
        animals,
        list,
    ):
        raise TypeError(
            "animals must be a list."
        )

    if not isinstance(
        preferences,
        dict,
    ):
        raise TypeError(
            "preferences must be a dictionary."
        )

    recommendation_limit = max(
        1,
        min(
            int(
                recommendation_limit
            ),
            20,
        ),
    )

    # -----------------------------------------------------
    # Normalize preference profile
    # -----------------------------------------------------

    preference_profile = (
        _coerce_preference_profile(
            preferences
        )
    )

    required = preference_profile.get(
        "required",
        {},
    )

    if not isinstance(
        required,
        dict,
    ):
        required = {}

    preferred = preference_profile.get(
        "preferred",
        {},
    )

    if not isinstance(
        preferred,
        dict,
    ):
        preferred = {}

    # -----------------------------------------------------
    # Metadata
    # -----------------------------------------------------

    metadata = preference_profile.get(
        "metadata",
        {},
    )

    if not isinstance(
        metadata,
        dict,
    ):
        metadata = {}

    # -----------------------------------------------------
    # Preferred confidence
    #
    # First try the new structured field.
    # If it does not exist, fall back to the raw ML
    # confidence dictionary already produced by app.py.
    # -----------------------------------------------------

    preferred_confidence = metadata.get(
        "preferred_confidence"
    )

    if not isinstance(
        preferred_confidence,
        dict,
    ):
        preferred_confidence = metadata.get(
            "confidence",
            {},
        )

    if not isinstance(
        preferred_confidence,
        dict,
    ):
        preferred_confidence = {}

    # -----------------------------------------------------
    # Required constraint filtering
    # -----------------------------------------------------

    filter_result = (
        filter_animals_by_required_constraints(
            animals,
            required,
        )
    )

    # -----------------------------------------------------
    # Exact / Alternative / No Match
    # -----------------------------------------------------

    fallback_result = resolve_fallback(
        animals=animals,

        preference_profile=(
            preference_profile
        ),

        exact_matches=filter_result[
            "exact_matches"
        ],
    )

    mode = fallback_result[
        "mode"
    ]

    candidates = fallback_result[
        "candidates"
    ]

    message = fallback_result[
        "message"
    ]

    # -----------------------------------------------------
    # No candidates
    # -----------------------------------------------------

    if not candidates:

        return _build_empty_ranking_result(
            message=message,

            total_scored=len(
                animals
            ),

            mode=mode,

            preference_profile=(
                preference_profile
            ),
        )

    # -----------------------------------------------------
    # Compatibility scoring
    # -----------------------------------------------------

    ranked = rank_candidates(
        candidates,
        preferred,
        preferred_confidence,
    )[
        :recommendation_limit
    ]

    # -----------------------------------------------------
    # Attach explanation context
    # -----------------------------------------------------

    ranked = _attach_explanation_context(
        recommendations=ranked,

        required=required,

        preferred=preferred,

        mode=mode,
    )

    # -----------------------------------------------------
    # Generate explanations
    # -----------------------------------------------------

    success_response = (
        build_success_response(
            ranked,
            message,
        )
    )

    recommendations = (
        _apply_api_compatibility_fields(
            success_response[
                "recommendations"
            ]
        )
    )

    # -----------------------------------------------------
    # Best + remaining recommendations
    # -----------------------------------------------------

    best_match = (
        recommendations[0]
        if recommendations
        else None
    )

    other_recommendations = (
        recommendations[1:]
        if len(
            recommendations
        ) > 1
        else []
    )

    # -----------------------------------------------------
    # Final API response
    # -----------------------------------------------------

    return {
        **success_response,

        "best_match": (
            best_match
        ),

        "other_recommendations": (
            other_recommendations
        ),

        "recommendations": (
            recommendations
        ),

        "total_scored": len(
            animals
        ),

        "exact_match_count": (
            filter_result[
                "exact_match_count"
            ]
        ),

        "mode": mode,

        "preference_profile": (
            preference_profile
        ),

        "confidence_weighting_available": (
            bool(
                preferred_confidence
            )
        ),
    }
