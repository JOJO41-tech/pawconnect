from scoring_engine import score_animal


# =========================================================
# TEST ANIMAL
# =========================================================

animal = {
    "name": "Test Cat",

    "energy_level": "low",

    "temperament": (
        "calm and friendly"
    ),

    "apartment_friendly": 1,

    "child_friendly": 1,

    "pet_friendly": 1,

    # Intentional mismatch:
    # User = beginner
    # Animal = experienced
    "experience_required": (
        "experienced"
    ),

    "daily_attention_hours": 2,

    "recommendation_mode": "exact",

    "required_match_ratio": 1.0,
}


# =========================================================
# USER PREFERENCES
# =========================================================

preferred = {
    "energy_level": "low",

    "temperament": [
        "calm",
        "friendly",
    ],

    "apartment_friendly": True,

    "experience_level": (
        "beginner"
    ),

    "available_attention_hours": 2,
}


# =========================================================
# HIGH ML CONFIDENCE
# =========================================================

high_confidence = {
    "low_energy": 0.95,

    "calm": 0.90,

    "friendly": 0.85,

    "apartment_friendly": 0.90,

    "beginner_owner": 0.90,

    "limited_time": 0.90,
}


# =========================================================
# LOW ML CONFIDENCE
# =========================================================

low_confidence = {
    "low_energy": 0.50,

    "calm": 0.50,

    "friendly": 0.50,

    "apartment_friendly": 0.50,

    "beginner_owner": 0.50,

    "limited_time": 0.50,
}


# =========================================================
# HIGH CONFIDENCE TEST
# =========================================================

print("=" * 60)
print("HIGH CONFIDENCE")
print("=" * 60)

result_high = score_animal(
    animal,
    preferred,
    high_confidence,
)

print(
    "Score:",
    result_high[
        "compatibility_score"
    ],
)

print(
    "Earned:",
    result_high[
        "earned_weight"
    ],
)

print(
    "Possible:",
    result_high[
        "possible_weight"
    ],
)

print(
    "Required match:",
    result_high[
        "required_match_percentage"
    ],
)

print(
    "Preferred match:",
    result_high[
        "preferred_match_percentage"
    ],
)

print(
    "Confidence weighting:",
    result_high[
        "confidence_weighting_applied"
    ],
)

print(
    "Matched:",
    result_high[
        "matched_preferences"
    ],
)

print(
    "Missing:",
    result_high[
        "missing_preferences"
    ],
)


# =========================================================
# LOW CONFIDENCE TEST
# =========================================================

print()

print("=" * 60)
print("LOW CONFIDENCE")
print("=" * 60)

result_low = score_animal(
    animal,
    preferred,
    low_confidence,
)

print(
    "Score:",
    result_low[
        "compatibility_score"
    ],
)

print(
    "Earned:",
    result_low[
        "earned_weight"
    ],
)

print(
    "Possible:",
    result_low[
        "possible_weight"
    ],
)

print(
    "Required match:",
    result_low[
        "required_match_percentage"
    ],
)

print(
    "Preferred match:",
    result_low[
        "preferred_match_percentage"
    ],
)

print(
    "Confidence weighting:",
    result_low[
        "confidence_weighting_applied"
    ],
)

print(
    "Matched:",
    result_low[
        "matched_preferences"
    ],
)

print(
    "Missing:",
    result_low[
        "missing_preferences"
    ],
)


# =========================================================
# COMPARISON
# =========================================================

print()

print("=" * 60)
print("COMPARISON")
print("=" * 60)

high_score = result_high[
    "compatibility_score"
]

low_score = result_low[
    "compatibility_score"
]

print(
    "High confidence score:",
    high_score,
)

print(
    "Low confidence score:",
    low_score,
)

print(
    "Difference:",
    round(
        high_score - low_score,
        2,
    ),
)


# =========================================================
# SIMPLE VALIDATION
# =========================================================

if (
    result_high[
        "confidence_weighting_applied"
    ]
    and result_low[
        "confidence_weighting_applied"
    ]
):
    print(
        "PASS: Confidence weighting "
        "was applied."
    )

else:
    print(
        "FAIL: Confidence weighting "
        "was not applied."
    )


if (
    "Experience level differs."
    in result_high[
        "missing_preferences"
    ]
):
    print(
        "PASS: Experience mismatch "
        "was detected."
    )

else:
    print(
        "FAIL: Experience mismatch "
        "was not detected."
    )