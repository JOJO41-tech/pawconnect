from scoring_engine import rank_candidates


animals = [
    {
        "id": 3,
        "name": "Buddy",
        "energy_level": "medium",
        "temperament": "friendly",
        "recommendation_mode": "exact",
        "required_match_ratio": 1.0,
        "failed_required_constraints": [],
    },
    {
        "id": 1,
        "name": "Max",
        "energy_level": "medium",
        "temperament": "friendly",
        "recommendation_mode": "exact",
        "required_match_ratio": 1.0,
        "failed_required_constraints": [],
    },
    {
        "id": 2,
        "name": "Luna",
        "energy_level": "medium",
        "temperament": "friendly",
        "recommendation_mode": "exact",
        "required_match_ratio": 1.0,
        "failed_required_constraints": [],
    },
]


preferred = {
    "energy_level": "medium",
}


results = rank_candidates(
    candidates=animals,
    preferred=preferred,
    preferred_confidence={
        "moderate_activity": 1.0,
    },
)


print("=" * 60)
print("DETERMINISTIC TIE TEST")
print("=" * 60)


for index, animal in enumerate(
    results,
    start=1,
):

    print(
        index,
        animal["id"],
        animal["name"],
        animal["compatibility_score"],
    )


ids = [
    animal["id"]
    for animal in results
]


assert ids == [
    1,
    2,
    3,
], (
    f"Expected [1, 2, 3], received {ids}"
)


print()
print(
    "PASS: Tie ranking is deterministic."
)