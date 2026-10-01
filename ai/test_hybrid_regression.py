from entity_extractor import extract_entities
from ranking import rank_animals


# =========================================================
# TEST ANIMALS
# =========================================================

ANIMALS = [
    {
        "id": 1,
        "name": "Buddy",
        "type": "dog",
        "breed": "Labrador Retriever",
        "age": 3,
        "gender": "male",
        "size": "medium",
        "location": "Bangkok",
        "energy_level": "medium",
        "temperament": "friendly, playful",
        "apartment_friendly": True,
        "child_friendly": True,
        "pet_friendly": True,
        "experience_required": "beginner",
        "daily_attention_hours": 4,
        "adoption_status": "available",
    },
    {
        "id": 2,
        "name": "Max",
        "type": "dog",
        "breed": "Beagle",
        "age": 2,
        "gender": "male",
        "size": "small",
        "location": "Bangkok",
        "energy_level": "high",
        "temperament": "friendly, active",
        "apartment_friendly": True,
        "child_friendly": True,
        "pet_friendly": True,
        "experience_required": "beginner",
        "daily_attention_hours": 5,
        "adoption_status": "available",
    },
    {
        "id": 3,
        "name": "Luna",
        "type": "cat",
        "breed": "Russian Blue",
        "age": 1,
        "gender": "female",
        "size": "small",
        "location": "Bangkok",
        "energy_level": "low",
        "temperament": "calm, friendly",
        "apartment_friendly": True,
        "child_friendly": True,
        "pet_friendly": True,
        "experience_required": "beginner",
        "daily_attention_hours": 2,
        "adoption_status": "available",
    },
]


# =========================================================
# HELPER
# =========================================================

def assert_equal(
    actual,
    expected,
    message,
):
    if actual != expected:
        raise AssertionError(
            f"{message}\n"
            f"Expected: {expected!r}\n"
            f"Actual:   {actual!r}"
        )


# =========================================================
# TEST 1
# MEDIUM ENERGY MUST NOT BECOME SIZE
# =========================================================

entities = extract_entities(
    "I want a medium-energy dog."
)

assert_equal(
    entities["pet_type"],
    "dog",
    "TEST 1 pet type failed.",
)

assert_equal(
    entities["size"],
    None,
    "TEST 1 medium-energy was incorrectly parsed as size.",
)

print(
    "PASS 1: medium-energy is not interpreted as size."
)


# =========================================================
# TEST 2
# MEDIUM-SIZED MUST STILL BE SIZE
# =========================================================

entities = extract_entities(
    "I want a medium-sized dog."
)

assert_equal(
    entities["pet_type"],
    "dog",
    "TEST 2 pet type failed.",
)

assert_equal(
    entities["size"],
    "medium",
    "TEST 2 medium-sized was not parsed correctly.",
)

print(
    "PASS 2: medium-sized is interpreted as physical size."
)


# =========================================================
# TEST 3
# PET TYPE MUST NEVER RELAX
# =========================================================

profile = {
    "required": {
        "pet_type": "dog",
        "breed": "Golden Retriever",
    },
    "preferred": {
        "energy_level": "low",
    },
    "metadata": {
        "model": "hybrid",
    },
}

cats_only = [
    ANIMALS[2],
]

result = rank_animals(
    animals=cats_only,
    preferences=profile,
    recommendation_limit=4,
)

assert_equal(
    result["recommendations"],
    [],
    "TEST 3 cat was recommended when dog was required.",
)

assert_equal(
    result["best_match"],
    None,
    "TEST 3 best_match should be None.",
)

print(
    "PASS 3: pet_type remains a hard constraint."
)


# =========================================================
# TEST 4
# RELAXABLE BREED SHOULD ALLOW SAME SPECIES ALTERNATIVE
# =========================================================

profile = {
    "required": {
        "pet_type": "dog",
        "breed": "Golden Retriever",
    },
    "preferred": {
        "energy_level": "medium",
    },
    "metadata": {
        "model": "hybrid",
    },
}

result = rank_animals(
    animals=[
        ANIMALS[0],
        ANIMALS[1],
    ],
    preferences=profile,
    recommendation_limit=4,
)

if not result["recommendations"]:
    raise AssertionError(
        "TEST 4 expected same-species alternatives."
    )

for animal in result["recommendations"]:
    assert_equal(
        animal["type"],
        "dog",
        "TEST 4 fallback returned wrong pet type.",
    )

print(
    "PASS 4: breed can relax while pet_type stays fixed."
)


# =========================================================
# TEST 5
# EXACT ENERGY MATCH SHOULD SCORE ABOVE MISMATCH
# =========================================================

profile = {
    "required": {
        "pet_type": "dog",
    },
    "preferred": {
        "energy_level": "medium",
    },
    "metadata": {
        "model": "hybrid",
        "preferred_confidence": {
            "moderate_activity": 1.0,
        },
    },
}

result = rank_animals(
    animals=[
        ANIMALS[0],
        ANIMALS[1],
    ],
    preferences=profile,
    recommendation_limit=4,
)

assert_equal(
    result["best_match"]["name"],
    "Buddy",
    "TEST 5 medium-energy dog should rank first.",
)

print(
    "PASS 5: exact energy preference affects ranking correctly."
)


# =========================================================
# TEST 6
# NO PREFERRED CONSTRAINTS
# EXACT REQUIRED MATCHES SHOULD SCORE 100
# =========================================================

profile = {
    "required": {
        "pet_type": "dog",
    },
    "preferred": {},
    "metadata": {
        "model": "hybrid",
    },
}

result = rank_animals(
    animals=[
        ANIMALS[0],
        ANIMALS[1],
    ],
    preferences=profile,
    recommendation_limit=4,
)

for animal in result["recommendations"]:

    assert_equal(
        animal["compatibility_score"],
        100.0,
        "TEST 6 exact required-only match should score 100.",
    )

print(
    "PASS 6: required-only exact matches score correctly."
)


# =========================================================
# TEST 7
# DETERMINISTIC TIE ORDER
# =========================================================

profile = {
    "required": {
        "pet_type": "dog",
    },
    "preferred": {},
    "metadata": {
        "model": "hybrid",
    },
}

result = rank_animals(
    animals=[
        ANIMALS[1],
        ANIMALS[0],
    ],
    preferences=profile,
    recommendation_limit=4,
)

ids = [
    animal["id"]
    for animal in result["recommendations"]
]

assert_equal(
    ids,
    [1, 2],
    "TEST 7 deterministic tie ranking failed.",
)

print(
    "PASS 7: tie ranking is deterministic."
)


# =========================================================
# TEST 8
# EXPLANATION MUST DISCLOSE RELAXED REQUIRED CONSTRAINT
# =========================================================

profile = {
    "required": {
        "pet_type": "dog",
        "breed": "Golden Retriever",
    },
    "preferred": {
        "energy_level": "medium",
    },
    "metadata": {
        "model": "hybrid",
    },
}

result = rank_animals(
    animals=[
        ANIMALS[0],
    ],
    preferences=profile,
    recommendation_limit=4,
)

recommendation = result["recommendations"][0]

failed = recommendation.get(
    "failed_required_constraints",
    [],
)

if "breed" not in failed:
    raise AssertionError(
        "TEST 8 breed mismatch was not disclosed."
    )

concerns = recommendation.get(
    "concerns",
    [],
)

if not any(
    "Breed differs"
    in item
    for item in concerns
):
    raise AssertionError(
        "TEST 8 explanation did not disclose breed mismatch."
    )

print(
    "PASS 8: relaxed required constraint is explained."
)


# =========================================================
# FINAL
# =========================================================

print()
print("=" * 60)
print("ALL HYBRID REGRESSION TESTS PASSED")
print("=" * 60)