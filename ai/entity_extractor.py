# CORRECTED ENTITY EXTRACTOR VERSION 0.4.1
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any


DOG_BREEDS = [
    "Labrador Retriever",
    "Golden Retriever",
    "German Shepherd",
    "French Bulldog",
    "Bulldog",
    "Poodle",
    "Beagle",
    "Rottweiler",
    "Dachshund",
    "Siberian Husky",
    "Shih Tzu",
    "Chihuahua",
    "Pomeranian",
    "Border Collie",
    "Corgi",
    "Yorkshire Terrier",
    "Maltese",
    "Boxer",
    "Great Dane",
    "Doberman",
    "Mixed Breed Dog",
]

CAT_BREEDS = [
    "Domestic Shorthair",
    "British Shorthair",
    "Siamese",
    "Persian",
    "Maine Coon",
    "Ragdoll",
    "Bengal",
    "Scottish Fold",
    "Sphynx",
    "Russian Blue",
    "American Shorthair",
    "Abyssinian",
    "Norwegian Forest Cat",
    "Mixed Breed Cat",
]

LOCATIONS = [
    "Bangkok",
    "Pathum Thani",
    "Rangsit",
    "Nonthaburi",
    "Samut Prakan",
    "Ayutthaya",
    "Chiang Mai",
    "Phuket",
    "Pattaya",
    "Chonburi",
    "Nakhon Pathom",
]


@dataclass
class ExtractedEntities:
    age_years: int | None = None
    age_months: int | None = None
    breed: str | None = None
    gender: str | None = None
    size: str | None = None
    location: str | None = None
    pet_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def _contains_phrase(text: str, phrase: str) -> bool:
    return re.search(
        rf"\b{re.escape(phrase.lower())}\b",
        text.lower(),
    ) is not None


def extract_age(
    text: str,
) -> tuple[int | None, int | None]:
    lowered = text.lower()

    year_patterns = [
        r"\b(\d{1,2})\s*[- ]?year[- ]?old\b",
        r"\b(\d{1,2})\s*years?\s*old\b",
        r"\bage\s*(?:is\s*)?(\d{1,2})\b",
        r"\b(\d{1,2})\s*yrs?\b",
    ]

    month_patterns = [
        r"\b(\d{1,2})\s*[- ]?month[- ]?old\b",
        r"\b(\d{1,2})\s*months?\s*old\b",
        r"\b(\d{1,2})\s*mos?\b",
    ]

    for pattern in year_patterns:
        match = re.search(pattern, lowered)
        if match:
            return int(match.group(1)), None

    for pattern in month_patterns:
        match = re.search(pattern, lowered)
        if match:
            return None, int(match.group(1))

    word_ages = {
        "one-year-old": 1,
        "two-year-old": 2,
        "three-year-old": 3,
        "four-year-old": 4,
        "five-year-old": 5,
        "six-year-old": 6,
        "seven-year-old": 7,
        "eight-year-old": 8,
        "nine-year-old": 9,
        "ten-year-old": 10,
    }

    for phrase, value in word_ages.items():
        if phrase in lowered:
            return value, None

    return None, None


def extract_breed(text: str) -> str | None:
    all_breeds = sorted(
        set(DOG_BREEDS + CAT_BREEDS),
        key=len,
        reverse=True,
    )

    for breed in all_breeds:
        if _contains_phrase(text, breed):
            return breed

    return None


def extract_gender(text: str) -> str | None:
    lowered = text.lower()

    female_patterns = [
        r"\bfemale\b",
        r"\bgirl\s+(?:dog|cat|pet)\b",
    ]

    male_patterns = [
        r"\bmale\b",
        r"\bboy\s+(?:dog|cat|pet)\b",
    ]

    for pattern in female_patterns:
        if re.search(pattern, lowered):
            return "female"

    for pattern in male_patterns:
        if re.search(pattern, lowered):
            return "male"

    return None


def extract_size(text: str) -> str | None:
    lowered = text.lower()

    size_patterns = {
        "small": [
            r"\bsmall(?:-sized)?\b",
            r"\btiny\b",
            r"\bcompact\b",
        ],
        "medium": [
            r"\bmedium(?:-sized)?\b",
            r"\bmid-sized\b",
        ],
        "large": [
            r"\blarge(?:-sized)?\b",
            r"\bbig\b",
            r"\bgiant\b",
        ],
    }

    for size, patterns in size_patterns.items():
        for pattern in patterns:
            if re.search(pattern, lowered):
                return size

    return None


def extract_location(text: str) -> str | None:
    for location in sorted(
        LOCATIONS,
        key=len,
        reverse=True,
    ):
        if _contains_phrase(text, location):
            return location

    return None


def extract_pet_type(
    text: str,
    detected_breed: str | None = None,
) -> str | None:
    lowered = text.lower()

    dog_match = re.search(
        r"\b(dog|puppy|canine)\b",
        lowered,
    )

    cat_match = re.search(
        r"\b(cat|kitten|feline)\b",
        lowered,
    )

    if dog_match and not cat_match:
        return "dog"

    if cat_match and not dog_match:
        return "cat"

    if detected_breed:
        if detected_breed in DOG_BREEDS:
            return "dog"

        if detected_breed in CAT_BREEDS:
            return "cat"

    return None


def extract_entities(text: str) -> dict[str, Any]:
    cleaned = _normalize(text)

    age_years, age_months = extract_age(cleaned)
    detected_breed = extract_breed(cleaned)

    result = ExtractedEntities(
        age_years=age_years,
        age_months=age_months,
        breed=detected_breed,
        gender=extract_gender(cleaned),
        size=extract_size(cleaned),
        location=extract_location(cleaned),
        pet_type=extract_pet_type(
            cleaned,
            detected_breed,
        ),
    )

    return result.to_dict()
