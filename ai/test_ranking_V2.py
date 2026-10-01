from ranking import rank_animals


ANIMALS = [
    {
        "id": 1,
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
    {
        "id": 2,
        "name": "Milo",
        "type": "cat",
        "breed": "Siamese",
        "age": 2,
        "gender": "male",
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


def run_case(
    title,
    profile,
):
    print("\n" + "=" * 60)
    print(title)

    result = rank_animals(
        animals=ANIMALS,
        preferences=profile,
        recommendation_limit=4,
    )

    print("Mode:", result["mode"])
    print("Message:", result["message"])

    for animal in result["recommendations"]:
        print(
            animal["name"],
            animal["compatibility_score"],
        )
        print(animal["explanation"])


run_case(
    "CASE 1: Exact Russian Blue",
    {
        "required": {
            "pet_type": "cat",
            "breed": "Russian Blue",
            "age_years": 1,
            "location": "Bangkok",
        },
        "preferred": {},
        "metadata": {
            "model": "ml",
        },
    },
)

run_case(
    "CASE 2: Missing breed with no soft preferences",
    {
        "required": {
            "pet_type": "cat",
            "breed": "Bengal",
        },
        "preferred": {},
        "metadata": {
            "model": "ml",
        },
    },
)

run_case(
    "CASE 3: Missing breed with soft preferences",
    {
        "required": {
            "pet_type": "cat",
            "breed": "Bengal",
        },
        "preferred": {
            "energy_level": "low",
            "temperament": [
                "calm",
                "friendly",
            ],
            "apartment_friendly": True,
        },
        "metadata": {
            "model": "ml",
        },
    },
)