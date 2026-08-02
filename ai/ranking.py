from __future__ import annotations

from typing import Any
import math

# ==========================================================
# NORMALIZATION
# ==========================================================

TEMPERAMENT_GROUPS = {
    "calm": [
        "calm",
        "quiet",
        "gentle",
        "relaxed",
        "easygoing",
        "laid back",
        "laid-back",
        "docile",
        "sweet",
    ],
    "active": [
        "active",
        "energetic",
        "playful",
        "athletic",
        "high energy",
        "high-energy",
    ],
    "friendly": [
        "friendly",
        "social",
        "outgoing",
        "loving",
        "affectionate",
        "people friendly",
    ],
    "independent": [
        "independent",
        "self sufficient",
        "self-sufficient",
        "alone",
    ],
    "protective": [
        "protective",
        "loyal",
        "guard",
    ],
}


# ==========================================================
# HELPERS
# ==========================================================

def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def normalize_boolean(value: Any) -> bool:
    if isinstance(value, bool):
        return value

    if isinstance(value, int):
        return value == 1

    return normalize_text(value) in {
        "1",
        "true",
        "yes",
        "y",
    }


def normalize_list(value: Any) -> list[str]:

    if value is None:
        return []

    if isinstance(value, (list, tuple, set)):
        return [
            normalize_text(v)
            for v in value
            if normalize_text(v)
        ]

    text = normalize_text(value)

    if not text:
        return []

    return [
        item.strip()
        for item in text.split(",")
        if item.strip()
    ]


def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:

    try:
        return float(value)

    except Exception:
        return default


def extract_age_in_years(
    value: Any,
) -> float | None:

    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    text = normalize_text(value)

    digits = ""

    for ch in text:

        if ch.isdigit() or ch == ".":
            digits += ch

        elif digits:
            break

    if not digits:
        return None

    age = safe_float(digits)

    if "week" in text:
        return age / 52

    if "month" in text:
        return age / 12

    return age


def get_preference(
    preferences: dict[str, Any],
    *keys: str,
    default=None,
):

    for key in keys:

        if key in preferences:

            value = preferences.get(key)

            if value is not None:
                return value

    return default


# ==========================================================
# TEMPERAMENT
# ==========================================================

def has_trait(
    text: str,
    trait: str,
) -> bool:

    text = normalize_text(text)

    synonyms = TEMPERAMENT_GROUPS.get(
        trait,
        [trait],
    )

    return any(
        word in text
        for word in synonyms
    )


def trait_score(
    animal_text: str,
    requested_traits: list[str],
):

    score = 0
    matched = []

    for trait in requested_traits:

        if has_trait(animal_text, trait):

            score += 1
            matched.append(trait)

    return score, matched


# ==========================================================
# SCORE HELPERS
# ==========================================================

def add_reason(
    reasons: list[str],
    text: str,
):

    if text not in reasons:
        reasons.append(text)


def add_concern(
    concerns: list[str],
    text: str,
):

    if text not in concerns:
        concerns.append(text)


def clamp(
    value: float,
    minimum: float = 0,
    maximum: float = 100,
):

    return max(
        minimum,
        min(
            maximum,
            value,
        ),
    )
# ==========================================================
# MAIN AI SCORING ENGINE
# ==========================================================

def calculate_animal_match(
    animal: dict[str, Any],
    preferences: dict[str, Any],
):

    score = 50.0

    reasons = []
    concerns = []

    # -----------------------------
    # Animal
    # -----------------------------

    animal_type = normalize_text(animal.get("type"))
    animal_breed = normalize_text(animal.get("breed"))
    animal_gender = normalize_text(animal.get("gender"))
    animal_size = normalize_text(animal.get("size"))
    animal_location = normalize_text(animal.get("location"))
    animal_energy = normalize_text(animal.get("energy_level"))
    animal_temperament = normalize_text(animal.get("temperament"))
    animal_description = normalize_text(animal.get("description"))
    animal_experience = normalize_text(animal.get("experience_required"))

    apartment = normalize_boolean(
        animal.get("apartment_friendly")
    )

    child = normalize_boolean(
        animal.get("child_friendly")
    )

    pet = normalize_boolean(
        animal.get("pet_friendly")
    )

    attention = safe_float(
        animal.get("daily_attention_hours"),
        0,
    )

    animal_age = extract_age_in_years(
        animal.get("age")
    )

    combined_text = " ".join([
        animal_temperament,
        animal_description,
        animal_energy,
    ])

    # -----------------------------
    # Preferences
    # -----------------------------

    preferred_type = normalize_text(
        get_preference(
            preferences,
            "pet_type",
            "preferredType",
        )
    )

    preferred_breed = normalize_text(
        get_preference(
            preferences,
            "breed",
        )
    )

    preferred_gender = normalize_text(
        get_preference(
            preferences,
            "gender",
        )
    )

    preferred_size = normalize_text(
        get_preference(
            preferences,
            "size",
        )
    )

    preferred_location = normalize_text(
        get_preference(
            preferences,
            "location",
        )
    )

    preferred_energy = normalize_text(
        get_preference(
            preferences,
            "energy_level",
        )
    )

    preferred_traits = normalize_list(
        get_preference(
            preferences,
            "temperament_traits",
            default=[],
        )
    )

    experience_level = normalize_text(
        get_preference(
            preferences,
            "experience_level",
        )
    )

    available_hours = safe_float(
        get_preference(
            preferences,
            "available_attention_hours",
            default=-1,
        ),
        -1,
    )

    # =====================================================
    # PET TYPE
    # =====================================================

    if preferred_type:

        if animal_type == preferred_type:

            score += 30

            add_reason(
                reasons,
                f"Preferred {animal_type}.",
            )

        else:

            score -= 30

            add_concern(
                concerns,
                "Different pet type.",
            )

    # =====================================================
    # BREED
    # =====================================================

    if preferred_breed:

        if preferred_breed == animal_breed:

            score += 25

            add_reason(
                reasons,
                f"Exact breed match ({animal.get('breed')})."
            )

        elif preferred_breed in animal_breed:

            score += 18

            add_reason(
                reasons,
                "Very similar breed."
            )

        else:

            score -= 15

            add_concern(
                concerns,
                "Breed differs."
            )

    # =====================================================
    # GENDER
    # =====================================================

    if preferred_gender:

        if preferred_gender == animal_gender:

            score += 8

            add_reason(
                reasons,
                "Preferred gender matched."
            )

        else:

            score -= 5

            add_concern(
                concerns,
                "Gender differs."
            )

    # =====================================================
    # SIZE
    # =====================================================

    if preferred_size:

        if preferred_size == animal_size:

            score += 8

            add_reason(
                reasons,
                "Preferred size."
            )

        else:

            score -= 4

    # =====================================================
    # LOCATION
    # =====================================================

    if preferred_location:

        if preferred_location in animal_location:

            score += 5

            add_reason(
                reasons,
                "Near preferred location."
            )

    # =====================================================
    # APARTMENT
    # =====================================================

    if normalize_boolean(
        preferences.get(
            "apartment_friendly"
        )
    ):

        if apartment:

            score += 10

            add_reason(
                reasons,
                "Apartment friendly."
            )

        else:

            score -= 8

            add_concern(
                concerns,
                "Not ideal for apartments."
            )

    # =====================================================
    # ENERGY
    # =====================================================

    if preferred_energy:

        if preferred_energy in animal_energy:

            score += 10

            add_reason(
                reasons,
                "Energy level matches."
            )

        elif has_trait(
            combined_text,
            preferred_energy,
        ):

            score += 8

            add_reason(
                reasons,
                "Lifestyle matches."
            )

        else:

            score -= 5

            add_concern(
                concerns,
                "Energy mismatch."
            )

    # =====================================================
    # TEMPERAMENT
    # =====================================================

    trait_matches, matched = trait_score(
        combined_text,
        preferred_traits,
    )

    if preferred_traits:

        score += trait_matches * 4

        for item in matched[:3]:

            add_reason(
                reasons,
                item.capitalize() + " temperament."
            )

    # =====================================================
    # CHILD
    # =====================================================

    if preferences.get(
        "child_friendly"
    ):

        if child:

            score += 8

            add_reason(
                reasons,
                "Good with children."
            )

    # =====================================================
    # PETS
    # =====================================================

    if preferences.get(
        "pet_friendly"
    ):

        if pet:

            score += 8

            add_reason(
                reasons,
                "Good with other pets."
            )

    # =====================================================
    # EXPERIENCE
    # =====================================================

    if experience_level:

        beginner = (
            "beginner"
            in experience_level
        )

        requires_experience = (
            "experienced"
            in animal_experience
        )

        if beginner:

            if requires_experience:

                score -= 8

                add_concern(
                    concerns,
                    "Better for experienced owners."
                )

            else:

                score += 5

                add_reason(
                    reasons,
                    "Beginner friendly."
                )

    # =====================================================
    # ATTENTION
    # =====================================================

    if available_hours >= 0:

        if (
            attention == 0
            or available_hours >= attention
        ):

            score += 5

            add_reason(
                reasons,
                "Fits your schedule."
            )

        else:

            score -= 5

            add_concern(
                concerns,
                f"Needs {attention:g} hours daily."
            )

    # =====================================================
    # AGE
    # =====================================================

    preferred_age = preferences.get(
        "age_years"
    )

    if (
        preferred_age is not None
        and animal_age is not None
    ):

        if abs(
            animal_age -
            safe_float(preferred_age)
        ) <= 1:

            score += 3

            add_reason(
                reasons,
                "Preferred age."
            )

    score = round(clamp(score))

    result = dict(animal)

    result["match_score"] = score
    result["matchPercentage"] = score
    result["compatibility_score"] = score

    result["reasons"] = reasons[:7]
    result["matchReasons"] = reasons[:7]
    result["concerns"] = concerns[:5]

    return result

# ==========================================================
# FINAL RANKING
# ==========================================================

def rank_animals(
    animals: list[dict[str, Any]],
    preferences: dict[str, Any],
    recommendation_limit: int = 4,
):

    scored_animals = []

    for animal in animals:

        scored = calculate_animal_match(
            animal,
            preferences,
        )

        scored_animals.append(scored)

    # =====================================================
    # SMART TIE BREAKER
    # =====================================================

    def ranking_key(animal):

        reasons = animal.get(
            "matchReasons",
            [],
        )

        return (

            animal.get(
                "match_score",
                0,
            ),

            len(reasons),

            normalize_boolean(
                animal.get(
                    "apartment_friendly"
                )
            ),

            normalize_boolean(
                animal.get(
                    "pet_friendly"
                )
            ),

            normalize_boolean(
                animal.get(
                    "child_friendly"
                )
            ),

            -safe_float(
                animal.get(
                    "daily_attention_hours"
                ),
                999,
            ),

            normalize_text(
                animal.get(
                    "breed"
                )
            ),

            -int(
                animal.get(
                    "id",
                    0,
                )
            ),
        )

    scored_animals.sort(
        key=ranking_key,
        reverse=True,
    )

    recommendation_limit = max(
        1,
        recommendation_limit,
    )

    recommendations = scored_animals[
        :recommendation_limit
    ]

    best_match = (
        recommendations[0]
        if recommendations
        else None
    )

    other = (
        recommendations[1:]
        if len(recommendations) > 1
        else []
    )

    # =====================================================
    # SCORE NORMALIZATION
    # Make the top match stand out more.
    # =====================================================

    if recommendations:

        highest = recommendations[0][
            "match_score"
        ]

        second = (
            recommendations[1]["match_score"]
            if len(recommendations) > 1
            else highest
        )

        if highest - second < 8:

            recommendations[0][
                "match_score"
            ] = min(
                100,
                highest + 8,
            )

            recommendations[0][
                "matchPercentage"
            ] = recommendations[0][
                "match_score"
            ]

            recommendations[0][
                "compatibility_score"
            ] = recommendations[0][
                "match_score"
            ]

    # =====================================================
    # QUALITY LABEL
    # =====================================================

    for animal in recommendations:

        score = animal[
            "match_score"
        ]

        if score >= 90:

            animal[
                "match_level"
            ] = "Excellent"

        elif score >= 80:

            animal[
                "match_level"
            ] = "Very Good"

        elif score >= 70:

            animal[
                "match_level"
            ] = "Good"

        elif score >= 60:

            animal[
                "match_level"
            ] = "Fair"

        else:

            animal[
                "match_level"
            ] = "Low"

    return {

        "best_match": best_match,

        "other_recommendations": other,

        "recommendations": recommendations,

        "total_scored": len(
            scored_animals
        ),
    }
