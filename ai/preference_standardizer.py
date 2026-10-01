from __future__ import annotations

from typing import Any

from normalize import (
    normalize_text,
    normalize_lower,
    normalize_boolean_or_none,
    normalize_list,
    safe_float,
    normalize_size,
)


# =========================================================
# STANDARDIZATION
# =========================================================

def standardize_preferences(
    preferences: dict[str, Any] | None,
    *,
    model_name: str = "ml",
    original_prompt: str = "",
) -> dict[str, Any]:
    """
    Convert the legacy PawConnect preference dictionary into
    the standardized schema used by ML, LLM, and Hybrid models.

    Output:
        {
            "required": {...},
            "preferred": {...},
            "metadata": {...}
        }
    """

    preferences = preferences or {}

    if not isinstance(
        preferences,
        dict,
    ):
        raise TypeError(
            "preferences must be a dictionary."
        )

    # Already standardized: return a cleaned copy.
    if (
        isinstance(
            preferences.get("required"),
            dict,
        )
        and isinstance(
            preferences.get("preferred"),
            dict,
        )
    ):
        metadata = dict(
            preferences.get(
                "metadata",
                {},
            )
        )

        metadata.setdefault(
            "model",
            model_name,
        )

        metadata.setdefault(
            "original_prompt",
            original_prompt,
        )

        metadata.setdefault(
            "schema_version",
            "1.0",
        )

        return {
            "required": dict(
                preferences["required"]
            ),
            "preferred": dict(
                preferences["preferred"]
            ),
            "metadata": metadata,
        }

    required: dict[str, Any] = {}
    preferred: dict[str, Any] = {}

    # =====================================================
    # REQUIRED CONSTRAINTS
    # =====================================================

    pet_type = normalize_lower(
        preferences.get("pet_type")
    )

    if pet_type in {"cat", "dog"}:
        required["pet_type"] = pet_type

    breed = normalize_text(
        preferences.get("breed")
    )

    if breed:
        required["breed"] = breed

    gender = normalize_lower(
        preferences.get("gender")
    )

    if gender:
        required["gender"] = gender

    size = normalize_size(
        preferences.get("size")
    )

    if size:
        required["size"] = size

    location = normalize_text(
        preferences.get("location")
    )

    if location:
        required["location"] = location

    age_years = safe_float(
        preferences.get("age_years")
    )

    age_months = safe_float(
        preferences.get("age_months")
    )

    if age_years is not None:
        required["age_years"] = age_years

    if age_months is not None:
        required["age_months"] = age_months

    # =====================================================
    # PREFERRED CONSTRAINTS
    # =====================================================

    energy_level = normalize_lower(
        preferences.get("energy_level")
    )

    if energy_level:
        preferred[
            "energy_level"
        ] = energy_level

    temperament = normalize_list(
        preferences.get(
            "temperament_traits",
            preferences.get(
                "temperament",
                [],
            ),
        )
    )

    if temperament:
        preferred[
            "temperament"
        ] = temperament

    for field in (
        "apartment_friendly",
        "child_friendly",
        "pet_friendly",
    ):
        normalized = normalize_boolean_or_none(
            preferences.get(field)
        )

        if normalized is not None:
            preferred[field] = normalized

    experience_level = normalize_lower(
        preferences.get(
            "experience_level"
        )
    )

    if experience_level:
        preferred[
            "experience_level"
        ] = experience_level

    attention_hours = safe_float(
        preferences.get(
            "available_attention_hours"
        )
    )

    if attention_hours is not None:
        preferred[
            "available_attention_hours"
        ] = attention_hours

    # =====================================================
    # METADATA
    # =====================================================

    confidence = preferences.get(
        "confidence"
    )

    labels = preferences.get(
        "predicted_labels",
        preferences.get(
            "labels",
            [],
        ),
    )

    explicit_categories = preferences.get(
        "explicit_categories",
        {},
    )

    weights = preferences.get(
        "weights",
        {},
    )

    metadata = {
        "model": model_name,
        "original_prompt": (
            original_prompt
            or normalize_text(
                preferences.get(
                    "original_prompt"
                )
            )
        ),
        "schema_version": "1.0",
        "source_format": "legacy_flat_preferences",
        "confidence": confidence,
        "predicted_labels": normalize_list(
            labels
        ),
        "explicit_categories": (
            explicit_categories
            if isinstance(
                explicit_categories,
                dict,
            )
            else {}
        ),
        "weights": (
            weights
            if isinstance(
                weights,
                dict,
            )
            else {}
        ),
        "preference_builder_version": (
            preferences.get(
                "preference_builder_version"
            )
        ),
        "has_required_constraints": bool(
            required
        ),
        "has_preferred_constraints": bool(
            preferred
        ),
    }

    return {
        "required": required,
        "preferred": preferred,
        "metadata": metadata,
    }


# =========================================================
# VALIDATION
# =========================================================

def validate_standardized_profile(
    profile: dict[str, Any],
) -> list[str]:
    errors: list[str] = []

    if not isinstance(
        profile,
        dict,
    ):
        return [
            "Profile must be a dictionary."
        ]

    if not isinstance(
        profile.get("required"),
        dict,
    ):
        errors.append(
            "'required' must be a dictionary."
        )

    if not isinstance(
        profile.get("preferred"),
        dict,
    ):
        errors.append(
            "'preferred' must be a dictionary."
        )

    if not isinstance(
        profile.get("metadata"),
        dict,
    ):
        errors.append(
            "'metadata' must be a dictionary."
        )

    return errors