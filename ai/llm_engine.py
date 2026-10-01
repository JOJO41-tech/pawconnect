from __future__ import annotations

import json
import os
from typing import Any

from groq import Groq


# =========================================================
# CONFIGURATION
# =========================================================

API_KEY = os.getenv("GROQ_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY environment variable is not set."
    )


client = Groq(
    api_key=API_KEY
)


# Freeze this model for the entire research experiment.
MODEL_NAME = "llama-3.3-70b-versatile"


# =========================================================
# SYSTEM INSTRUCTION
# =========================================================

SYSTEM_INSTRUCTION = """
You are a preference extraction system for a pet adoption
recommendation research experiment.

Your task is to extract ONLY preferences explicitly stated
or unambiguously expressed by the user.

Do not guess missing preferences.
Do not infer unsupported information.

Return ONLY a valid JSON object.

The possible fields are:

pet_type
breed
age_years
age_months
gender
size
location
energy_level
temperament
apartment_friendly
child_friendly
pet_friendly
experience_level
available_attention_hours


NORMALIZATION RULES

Pet type:
dog / puppy / canine -> dog
cat / kitten / feline -> cat

Gender:
male -> male
female -> female

Size:
small -> small
medium-sized -> medium
large -> large

Energy:
low-energy -> low
medium-energy -> medium
moderate-energy -> medium
high-energy -> high
energetic -> high

Experience:
beginner owner -> beginner
first-time owner -> beginner
new pet owner -> beginner

experienced owner -> experienced
owned several pets before -> experienced
raised pets for years -> experienced


IMPORTANT DISTINCTIONS

"medium-energy" means:
energy_level = "medium"

It DOES NOT mean:
size = "medium"

"medium-sized" means:
size = "medium"

It DOES NOT mean:
energy_level = "medium"


TEMPERAMENT

Extract explicitly requested personality traits such as:

friendly
playful
calm
quiet
affectionate
independent

Return temperament as an array.

Example:

"friendly and playful dog"

becomes:

{
  "pet_type": "dog",
  "temperament": [
    "friendly",
    "playful"
  ]
}


LIFESTYLE

If the user explicitly says the animal must be suitable
for apartment living:

apartment_friendly = true

If the user explicitly requires compatibility with children:

child_friendly = true

If the user explicitly requires compatibility with other pets:

pet_friendly = true


AVAILABLE TIME

If the user explicitly says they have plenty of time for
the pet, work from home and can provide substantial
attention, or are around the house most of the day:

available_attention_hours = 8


NEGATION AND CONTRAST

Pay careful attention to negation.

Example:

"I want a dog, not a cat."

means:

{
  "pet_type": "dog"
}

Do NOT extract cat.


Example:

"My friend suggested a cat, but I actually want a dog."

means:

{
  "pet_type": "dog"
}


Example:

"I don't care whether it is male or female."

Do NOT extract gender.


Example:

"I don't care about breed."

Do NOT extract breed.


Example:

"I live in Bangkok, but location doesn't matter for the pet."

Do NOT extract Bangkok as the required pet location.


Example:

"I have children, but that doesn't mean the pet must be
child-friendly."

Do NOT extract child_friendly.


Do not convert background information into a pet preference
unless the user clearly connects it to what they want.


AGE

"two-year-old" -> age_years = 2

"six-month-old" -> age_months = 6


OUTPUT RULES

Return only fields supported by the user's text.

Do NOT return null fields.

Do NOT invent fields.

If no temperament is stated, do not return temperament.

Return valid JSON only.

No markdown.
No explanation.
No code fences.
"""


# =========================================================
# ALLOWED FIELDS
# =========================================================

ALLOWED_FIELDS = {
    "pet_type",
    "breed",
    "age_years",
    "age_months",
    "gender",
    "size",
    "location",
    "energy_level",
    "temperament",
    "apartment_friendly",
    "child_friendly",
    "pet_friendly",
    "experience_level",
    "available_attention_hours",
}


# =========================================================
# CLEAN OUTPUT
# =========================================================

def clean_result(
    result: dict[str, Any],
) -> dict[str, Any]:

    cleaned: dict[str, Any] = {}

    for key, value in result.items():

        if key not in ALLOWED_FIELDS:
            continue

        if value is None:
            continue

        if (
            key == "temperament"
            and isinstance(value, list)
            and len(value) == 0
        ):
            continue

        cleaned[key] = value

    return cleaned


# =========================================================
# LLM-ONLY PREDICTION
# =========================================================

def predict_llm_only(
    text: str,
) -> dict[str, Any]:

    cleaned_text = text.strip()

    if not cleaned_text:
        raise ValueError(
            "Text must not be empty."
        )

    completion = (
        client.chat.completions.create(
            model=MODEL_NAME,

            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_INSTRUCTION,
                },
                {
                    "role": "user",
                    "content": cleaned_text,
                },
            ],

            temperature=0,

            response_format={
                "type": "json_object"
            },
        )
    )

    response_text = (
        completion
        .choices[0]
        .message
        .content
    )

    if not response_text:
        raise RuntimeError(
            "Llama returned an empty response."
        )

    try:

        parsed = json.loads(
            response_text
        )

    except json.JSONDecodeError as exc:

        raise RuntimeError(
            "Llama returned invalid JSON: "
            + response_text
        ) from exc

    if not isinstance(
        parsed,
        dict,
    ):

        raise RuntimeError(
            "Llama response was not a JSON object."
        )

    structured_output = (
        clean_result(
            parsed
        )
    )

    return {
        "text":
            cleaned_text,

        "structured_output":
            structured_output,

        "raw_output":
            parsed,

        "model_name":
            MODEL_NAME,

        "system_type":
            "llm_only",
    }