from entity_extractor import extract_entities


TESTS = [
    {
        "text": (
            "I live in a condo in Bangkok and work from 9 to 5. "
            "I want a calm quiet one-year-old female British "
            "Shorthair that can stay alone."
        ),
        "expected": {
            "age_years": 1,
            "breed": "British Shorthair",
            "gender": "female",
            "location": "Bangkok",
            "pet_type": "cat",
        },
    },
    {
        "text": (
            "I want a two-year-old male Golden Retriever "
            "in Pathum Thani."
        ),
        "expected": {
            "age_years": 2,
            "breed": "Golden Retriever",
            "gender": "male",
            "location": "Pathum Thani",
            "pet_type": "dog",
        },
    },
]


for test in TESTS:
    result = extract_entities(test["text"])
    print("=" * 70)
    print(test["text"])
    print(result)

    for key, expected_value in test["expected"].items():
        actual_value = result.get(key)

        if actual_value != expected_value:
            raise AssertionError(
                f"{key}: expected {expected_value!r}, "
                f"received {actual_value!r}"
            )

print("All entity extraction tests passed.")
