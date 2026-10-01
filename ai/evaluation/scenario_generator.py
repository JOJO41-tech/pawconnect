"""
Seeded generator for recommendation scenarios, relevance labels,
and baseline rankers used by the ranking-metric and adversarial
hard-constraint evaluations.

Relevance is defined from the recommendation specification, not
from PawConnect's weighted score:

    grade 0  wrong pet type, or not available for adoption
    grade 1  right pet type but fails another required constraint
    grade 2+ satisfies every required constraint;
             2 + round(3 * fraction of preferred traits matched)  -> 2..5

The oracle counts preferred traits with equal (unweighted) importance
and exact matching only, so it does not reuse PawConnect's weights,
confidence scaling, or partial-credit rules.
"""

from __future__ import annotations

import random
from typing import Any, Callable

PET_TYPES = ["dog", "cat"]
GENDERS = ["male", "female"]
SIZES = ["small", "medium", "large"]
LOCATIONS = ["Bangkok", "Chiang Mai", "Pathum Thani", "Nonthaburi"]
ENERGY = ["low", "medium", "high"]
TRAITS = ["friendly", "calm", "playful", "protective", "independent", "affectionate"]
BOOLEAN_FIELDS = ["apartment_friendly", "child_friendly", "pet_friendly"]

OPTIONAL_REQUIRED = {"gender": GENDERS, "size": SIZES, "location": LOCATIONS}
PREFERRED_FIELDS = ["energy_level", "temperament", *BOOLEAN_FIELDS]

# Baseline weights mirror scoring_engine.WEIGHTS so the aggregate
# baseline differs from PawConnect only in how required
# constraints are treated.
SOFT_WEIGHTS = {
    "energy_level": 20.0,
    "temperament": 20.0,
    "apartment_friendly": 15.0,
    "child_friendly": 10.0,
    "pet_friendly": 10.0,
}
AGGREGATE_REQUIRED_WEIGHT = 15.0


# =========================================================
# GENERATION
# =========================================================

def random_animal(rng: random.Random, animal_id: int, pet_type: str | None = None) -> dict[str, Any]:
    return {
        "id": animal_id,
        "name": f"Pet{animal_id}",
        "type": pet_type or rng.choice(PET_TYPES),
        "gender": rng.choice(GENDERS),
        "size": rng.choice(SIZES),
        "location": rng.choice(LOCATIONS),
        "energy_level": rng.choice(ENERGY),
        "temperament": ", ".join(rng.sample(TRAITS, rng.randint(1, 3))),
        "apartment_friendly": rng.random() < 0.5,
        "child_friendly": rng.random() < 0.5,
        "pet_friendly": rng.random() < 0.5,
        "adoption_status": "available" if rng.random() < 0.9 else "adopted",
    }


def random_preferences(rng: random.Random) -> dict[str, Any]:
    required: dict[str, Any] = {"pet_type": rng.choice(PET_TYPES)}

    for field in rng.sample(list(OPTIONAL_REQUIRED), rng.randint(0, 2)):
        required[field] = rng.choice(OPTIONAL_REQUIRED[field])

    preferred: dict[str, Any] = {}

    for field in rng.sample(PREFERRED_FIELDS, rng.randint(2, 4)):
        if field == "energy_level":
            preferred[field] = rng.choice(ENERGY)
        elif field == "temperament":
            preferred[field] = rng.sample(TRAITS, rng.randint(1, 2))
        else:
            preferred[field] = True

    return {"required": required, "preferred": preferred}


def generate_scenarios(count: int, pool_size: int, seed: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    return [
        {
            "id": f"G{index:04d}",
            "preferences": random_preferences(rng),
            "animals": [random_animal(rng, animal_id) for animal_id in range(1, pool_size + 1)],
        }
        for index in range(1, count + 1)
    ]


# =========================================================
# ORACLE
# =========================================================

def is_available(animal: dict[str, Any]) -> bool:
    return str(animal.get("adoption_status", "available")).lower() == "available"


def required_matches(animal: dict[str, Any], required: dict[str, Any]) -> dict[str, bool]:
    return {
        field: str(animal.get("type" if field == "pet_type" else field, "")).lower() == str(value).lower()
        for field, value in required.items()
    }


def preferred_matches(animal: dict[str, Any], preferred: dict[str, Any]) -> tuple[int, int]:
    matched = 0
    total = 0
    animal_traits = {t.strip().lower() for t in str(animal.get("temperament", "")).split(",")}

    for field, value in preferred.items():
        if field == "temperament":
            for trait in value:
                total += 1
                matched += trait.lower() in animal_traits
        else:
            total += 1
            matched += animal.get(field) == value

    return matched, total


def relevance(animal: dict[str, Any], preferences: dict[str, Any]) -> int:
    required = preferences["required"]
    checks = required_matches(animal, required)

    if not is_available(animal) or not checks.get("pet_type", True):
        return 0

    if not all(checks.values()):
        return 1

    matched, total = preferred_matches(animal, preferences["preferred"])
    return 2 + round(3 * matched / total) if total else 2


def violates_hard_constraint(animal: dict[str, Any], preferences: dict[str, Any]) -> bool:
    """Non-relaxable constraints: pet type and availability."""
    pet_type = preferences["required"].get("pet_type")
    wrong_type = pet_type and str(animal.get("type", "")).lower() != str(pet_type).lower()
    return bool(wrong_type) or not is_available(animal)


# =========================================================
# BASELINE RANKERS
# =========================================================
# Each ranker returns an ordered list of animal dicts.

Ranker = Callable[[dict[str, Any], int], list[dict[str, Any]]]


def _soft_score(animal: dict[str, Any], preferred: dict[str, Any]) -> float:
    score = 0.0
    animal_traits = {t.strip().lower() for t in str(animal.get("temperament", "")).split(",")}

    for field, value in preferred.items():
        weight = SOFT_WEIGHTS.get(field, 10.0)
        if field == "temperament":
            score += weight * sum(t.lower() in animal_traits for t in value) / len(value)
        else:
            score += weight * (animal.get(field) == value)

    return score


def aggregate_score_ranker(scenario: dict[str, Any], k: int) -> list[dict[str, Any]]:
    """
    Single aggregate score: required constraints become weighted
    terms, so strong soft matches can compensate for a violated
    requirement (the design PawConnect is contrasted against).
    """
    preferences = scenario["preferences"]
    available = [a for a in scenario["animals"] if is_available(a)]

    def score(animal):
        required_hits = sum(required_matches(animal, preferences["required"]).values())
        return required_hits * AGGREGATE_REQUIRED_WEIGHT + _soft_score(animal, preferences["preferred"])

    return sorted(available, key=lambda a: (-score(a), a["id"]))[:k]


def filter_only_ranker(scenario: dict[str, Any], k: int) -> list[dict[str, Any]]:
    """Hard-constraint filtering, then listing order (no preference ranking)."""
    required = scenario["preferences"]["required"]
    eligible = [
        a for a in scenario["animals"]
        if is_available(a) and all(required_matches(a, required).values())
    ]
    return sorted(eligible, key=lambda a: a["id"])[:k]


def make_random_ranker(seed: int) -> Ranker:
    rng = random.Random(seed)

    def ranker(scenario: dict[str, Any], k: int) -> list[dict[str, Any]]:
        available = [a for a in scenario["animals"] if is_available(a)]
        rng.shuffle(available)
        return available[:k]

    return ranker
