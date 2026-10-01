# PAWCONNECT ENTITY EXTRACTOR VERSION 0.5.0

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any


# =========================================================
# NUMBER WORDS
# =========================================================

NUMBER_WORDS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
}


def parse_number(
    value: str,
) -> int | float | None:

    value = value.strip().lower()

    if value in NUMBER_WORDS:
        return NUMBER_WORDS[value]

    try:
        number = float(value)

        if number.is_integer():
            return int(number)

        return number

    except ValueError:
        return None


# =========================================================
# BREED DATA
# =========================================================

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


# =========================================================
# LOCATION DATA
# =========================================================

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


# =========================================================
# RESULT MODEL
# =========================================================

@dataclass
class ExtractedEntities:

    age_years: int | float | None = None
    age_months: int | float | None = None

    breed: str | None = None

    gender: str | None = None

    size: str | None = None

    location: str | None = None

    pet_type: str | None = None

    def to_dict(
        self,
    ) -> dict[str, Any]:

        return asdict(self)


# =========================================================
# HELPERS
# =========================================================

def _normalize(
    text: str,
) -> str:

    return re.sub(
        r"\s+",
        " ",
        text.strip(),
    )


def _contains_phrase(
    text: str,
    phrase: str,
) -> bool:

    return (
        re.search(
            rf"\b{re.escape(phrase.lower())}\b",
            text.lower(),
        )
        is not None
    )


# =========================================================
# AGE EXTRACTION
# =========================================================

def extract_age(
    text: str,
) -> dict[str, int | float | None]:
    """
    Extract exact pet age from natural-language text.

    Supports examples such as:

        one year old
        one-year-old
        1 year old
        1-year-old
        two years old
        two-year-old
        3 yrs old
        seven months old
        seven-month-old
        7 month old
        5 mos
    """

    lowered = text.lower()

    number_pattern = (
        r"(\d+(?:\.\d+)?|"
        r"zero|one|two|three|four|five|six|seven|"
        r"eight|nine|ten|eleven|twelve|thirteen|"
        r"fourteen|fifteen|sixteen|seventeen|"
        r"eighteen|nineteen|twenty)"
    )

    # =====================================================
    # YEARS
    #
    # Supports spaces and hyphens:
    #
    # two years old
    # two-year-old
    # 2-year-old
    # 2 yrs old
    # =====================================================

    year_match = re.search(
        number_pattern
        + r"(?:\s*-\s*|\s+)"
        + r"(?:year|years|yr|yrs)"
        + r"(?:"
        + r"(?:\s*-\s*|\s+)"
        + r"old"
        + r")?",
        lowered,
    )

    if year_match:

        age = parse_number(
            year_match.group(1)
        )

        if age is not None:

            return {
                "age_years": age,
                "age_months": None,
            }

    # =====================================================
    # MONTHS
    #
    # Supports:
    #
    # seven months old
    # seven-month-old
    # 7-month-old
    # 5 mos
    # =====================================================

    month_match = re.search(
        number_pattern
        + r"(?:\s*-\s*|\s+)"
        + r"(?:month|months|mo|mos)"
        + r"(?:"
        + r"(?:\s*-\s*|\s+)"
        + r"old"
        + r")?",
        lowered,
    )

    if month_match:

        age = parse_number(
            month_match.group(1)
        )

        if age is not None:

            return {
                "age_years": None,
                "age_months": age,
            }

    return {
        "age_years": None,
        "age_months": None,
    }
    # -----------------------------------------------------
    # MONTHS
    # -----------------------------------------------------

    month_match = re.search(
        number_pattern
        + r"\s*"
        + r"(?:month|months|mo|mos)"
        + r"(?:\s*old)?",
        lowered,
    )

    if month_match:

        age = parse_number(
            month_match.group(1)
        )

        if age is not None:

            return {
                "age_years": None,
                "age_months": age,
            }

    return {
        "age_years": None,
        "age_months": None,
    }


# =========================================================
# BREED EXTRACTION
# =========================================================

def extract_breed(
    text: str,
) -> str | None:

    all_breeds = sorted(
        set(
            DOG_BREEDS
            + CAT_BREEDS
        ),
        key=len,
        reverse=True,
    )

    for breed in all_breeds:

        if _contains_phrase(
            text,
            breed,
        ):

            return breed

    return None


# =========================================================
# GENDER EXTRACTION
# =========================================================

def extract_gender(
    text: str,
) -> str | None:

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

        if re.search(
            pattern,
            lowered,
        ):

            return "female"

    for pattern in male_patterns:

        if re.search(
            pattern,
            lowered,
        ):

            return "male"

    return None


# =========================================================
# SIZE EXTRACTION
# =========================================================

def extract_size(
    text: str,
) -> str | None:
    """
    Extract physical animal size.

    IMPORTANT:
    Energy phrases such as:

        medium-energy
        medium energy
        low-energy
        high-energy

    must NEVER be interpreted as physical pet size.
    """

    lowered = text.lower()

    # -----------------------------------------------------
    # Remove energy phrases BEFORE checking physical size.
    # -----------------------------------------------------

    energy_patterns = [
        r"\blow[- ]energy\b",
        r"\bmedium[- ]energy\b",
        r"\bmoderate[- ]energy\b",
        r"\bhigh[- ]energy\b",
    ]

    size_text = lowered

    for pattern in energy_patterns:

        size_text = re.sub(
            pattern,
            "",
            size_text,
        )

    # -----------------------------------------------------
    # Physical size patterns
    # -----------------------------------------------------

    size_patterns = {

        "small": [
            r"\bsmall-sized\b",
            r"\bsmall sized\b",
            r"\bsmall\s+(?:dog|cat|pet|animal|puppy|kitten)\b",
            r"\btiny\s+(?:dog|cat|pet|animal|puppy|kitten)\b",
            r"\bcompact\s+(?:dog|cat|pet|animal)\b",
        ],

        "medium": [
            r"\bmedium-sized\b",
            r"\bmedium sized\b",
            r"\bmid-sized\b",
            r"\bmid sized\b",
            r"\bmedium\s+(?:dog|cat|pet|animal|puppy|kitten)\b",
        ],

        "large": [
            r"\blarge-sized\b",
            r"\blarge sized\b",
            r"\blarge\s+(?:dog|cat|pet|animal|puppy|kitten)\b",
            r"\bbig\s+(?:dog|cat|pet|animal|puppy|kitten)\b",
            r"\bgiant\s+(?:dog|cat|pet|animal)\b",
        ],
    }

    for size, patterns in size_patterns.items():

        for pattern in patterns:

            if re.search(
                pattern,
                size_text,
            ):

                return size

    return None


# =========================================================
# LOCATION EXTRACTION
# =========================================================

def extract_location(
    text: str,
) -> str | None:

    for location in sorted(
        LOCATIONS,
        key=len,
        reverse=True,
    ):

        if _contains_phrase(
            text,
            location,
        ):

            return location

    return None


# =========================================================
# PET TYPE EXTRACTION
# =========================================================

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

    # -----------------------------------------------------
    # Infer from breed when species not written explicitly.
    # -----------------------------------------------------

    if detected_breed:

        if detected_breed in DOG_BREEDS:
            return "dog"

        if detected_breed in CAT_BREEDS:
            return "cat"

    return None


# =========================================================
# MAIN ENTITY EXTRACTION
# =========================================================

def extract_entities(
    text: str,
) -> dict[str, Any]:

    cleaned = _normalize(
        text
    )

    age = extract_age(
        cleaned
    )

    detected_breed = extract_breed(
        cleaned
    )

    result = ExtractedEntities(

        age_years=age[
            "age_years"
        ],

        age_months=age[
            "age_months"
        ],

        breed=detected_breed,

        gender=extract_gender(
            cleaned
        ),

        size=extract_size(
            cleaned
        ),

        location=extract_location(
            cleaned
        ),

        pet_type=extract_pet_type(
            cleaned,
            detected_breed,
        ),
    )

    return result.to_dict()