# PAWCONNECT HYBRID AI BACKEND VERSION 1.0.0

from pathlib import Path
from typing import Any
import json
import re

import joblib
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from entity_extractor import extract_entities
from ranking import rank_animals


# =========================================================
# PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = BASE_DIR / "pawconnect_multilabel_model_v4.joblib"
FEATURES_PATH = BASE_DIR / "pawconnect_text_features_v4.joblib"
LABEL_BINARIZER_PATH = (
    BASE_DIR / "pawconnect_label_binarizer_v4.joblib"
)
CONFIG_PATH = (
    BASE_DIR / "pawconnect_model_config_v4.json"
)


required_files = [
    MODEL_PATH,
    FEATURES_PATH,
    LABEL_BINARIZER_PATH,
    CONFIG_PATH,
]

missing_files = [
    file.name
    for file in required_files
    if not file.exists()
]

if missing_files:
    raise FileNotFoundError(
        "Missing AI model files: "
        + ", ".join(missing_files)
    )


# =========================================================
# LOAD MODEL
# =========================================================

model = joblib.load(MODEL_PATH)
features = joblib.load(FEATURES_PATH)
mlb = joblib.load(LABEL_BINARIZER_PATH)

with CONFIG_PATH.open(
    "r",
    encoding="utf-8",
) as f:
    config = json.load(f)

MODEL_VERSION = str(
    config.get(
        "model_version",
        "v4",
    )
)

THRESHOLD = float(
    config.get(
        "threshold",
        0.45,
    )
)


# =========================================================
# FASTAPI
# =========================================================

app = FastAPI(
    title="PawConnect Hybrid AI API",
    version="1.0.0",
    description=(
        "Hybrid recommendation engine using "
        "multi-label machine learning, "
        "entity extraction and compatibility ranking."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# REQUEST MODELS
# =========================================================

class UserInput(BaseModel):
    text: str = Field(
        min_length=3,
        max_length=1000,
    )


class AnimalInput(BaseModel):

    id: int | str

    shelter_id: int | str | None = None

    name: str | None = None
    type: str | None = None
    breed: str | None = None
    size: str | None = None

    age: (
        str
        | int
        | float
        | None
    ) = None

    gender: str | None = None
    temperament: str | None = None
    location: str | None = None

    health_status: str | None = None
    vaccination_status: str | None = None
    sterilization_status: str | None = None

    description: str | None = None
    image_url: str | None = None
    adoption_status: str | None = None

    energy_level: str | None = None

    apartment_friendly: (
        bool
        | int
        | str
        | None
    ) = None

    child_friendly: (
        bool
        | int
        | str
        | None
    ) = None

    pet_friendly: (
        bool
        | int
        | str
        | None
    ) = None

    experience_required: (
        str
        | None
    ) = None

    daily_attention_hours: (
        float
        | int
        | str
        | None
    ) = None


class RecommendationInput(BaseModel):

    text: str = Field(
        min_length=3,
        max_length=1000,
    )

    animals: list[AnimalInput]

    recommendation_limit: int = Field(
        default=4,
        ge=1,
        le=20,
    )

    # =========================================================
# RULE ENGINE
# =========================================================

def apply_schedule_rules(
    text: str,
    scores: dict[str, float],
) -> dict[str, float]:

    lowered = text.lower()

    limited_time_patterns = [
        r"\bwork(?:ing)?\s+from\s+\d{1,2}\s*(?:am|pm)?\s+to\s+\d{1,2}",
        r"\b9\s*to\s*5\b",
        r"\bwork long hours\b",
        r"\baway during the day\b",
        r"\bnot home during the day\b",
        r"\bstay alone\b",
        r"\bhome alone\b",
        r"\bbusy schedule\b",
    ]

    plenty_time_patterns = [
        r"\bwork from home\b",
        r"\bhome most of the day\b",
        r"\bsomeone is always home\b",
        r"\bplenty of time\b",
        r"\bavailable all day\b",
        r"\bcan spend most of the day\b",
    ]

    has_limited = any(
        re.search(pattern, lowered)
        for pattern in limited_time_patterns
    )

    has_plenty = any(
        re.search(pattern, lowered)
        for pattern in plenty_time_patterns
    )

    if has_limited and not has_plenty:

        scores["limited_time"] = max(
            scores.get(
                "limited_time",
                0.0,
            ),
            0.95,
        )

        scores["independent"] = max(
            scores.get(
                "independent",
                0.0,
            ),
            0.90,
        )

        scores.pop(
            "plenty_time",
            None,
        )

    elif has_plenty and not has_limited:

        scores["plenty_time"] = max(
            scores.get(
                "plenty_time",
                0.0,
            ),
            0.95,
        )

        scores.pop(
            "limited_time",
            None,
        )

    return scores


def apply_experience_rules(
    text: str,
    scores: dict[str, float],
) -> dict[str, float]:

    lowered = text.lower()

    beginner_patterns = [
        r"\bfirst pet\b",
        r"\bfirst[- ]time owner\b",
        r"\bnever owned a pet\b",
        r"\bno experience\b",
        r"\bbeginner owner\b",
    ]

    experienced_patterns = [
        r"\bexperienced owner\b",
        r"\bowned pets before\b",
        r"\bmany years of experience\b",
        r"\bhad pets for years\b",
        r"\bcomfortable training\b",
    ]

    beginner = any(
        re.search(
            pattern,
            lowered,
        )
        for pattern in beginner_patterns
    )

    experienced = any(
        re.search(
            pattern,
            lowered,
        )
        for pattern in experienced_patterns
    )

    if beginner and not experienced:

        scores["beginner_owner"] = max(
            scores.get(
                "beginner_owner",
                0.0,
            ),
            0.95,
        )

        scores.pop(
            "experienced_owner",
            None,
        )

    elif experienced and not beginner:

        scores["experienced_owner"] = max(
            scores.get(
                "experienced_owner",
                0.0,
            ),
            0.95,
        )

        scores.pop(
            "beginner_owner",
            None,
        )

    return scores


def keep_best_exclusive_label(
    scores: dict[str, float],
    labels: list[str],
) -> dict[str, float]:

    existing = [
        label
        for label in labels
        if label in scores
    ]

    if len(existing) <= 1:
        return scores

    winner = max(
        existing,
        key=lambda label: scores[label],
    )

    for label in existing:
        if label != winner:
            scores.pop(
                label,
                None,
            )

    return scores


def apply_exclusive_groups(
    scores: dict[str, float],
) -> dict[str, float]:

    groups = [
        [
            "prefers_cat",
            "prefers_dog",
        ],
        [
            "apartment_friendly",
            "house_friendly",
        ],
        [
            "active",
            "moderate_activity",
            "low_energy",
        ],
        [
            "limited_time",
            "plenty_time",
        ],
        [
            "beginner_owner",
            "experienced_owner",
        ],
        [
            "quiet",
            "vocal",
        ],
    ]

    for group in groups:
        scores = keep_best_exclusive_label(
            scores,
            group,
        )

    return scores


# =========================================================
# AI PREDICTION
# =========================================================

def run_prediction(
    text: str,
) -> dict[str, Any]:

    cleaned_text = text.strip()

    if not cleaned_text:
        raise HTTPException(
            status_code=400,
            detail="Please enter a pet preference.",
        )

    try:

        X = features.transform(
            [cleaned_text]
        )

        probabilities = model.predict_proba(
            X
        )[0]

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {exc}",
        ) from exc

    prediction_scores = {
        str(label): round(
            float(score),
            4,
        )
        for label, score in zip(
            mlb.classes_,
            probabilities,
        )
        if float(score) >= THRESHOLD
    }

    prediction_scores = apply_schedule_rules(
        cleaned_text,
        prediction_scores,
    )

    prediction_scores = apply_experience_rules(
        cleaned_text,
        prediction_scores,
    )

    prediction_scores = apply_exclusive_groups(
        prediction_scores,
    )

    predictions = sorted(
        [
            {
                "label": label,
                "confidence": round(
                    score,
                    4,
                ),
            }
            for label, score in prediction_scores.items()
        ],
        key=lambda item: item["confidence"],
        reverse=True,
    )

    if not predictions:

        predictions = sorted(
            [
                {
                    "label": str(label),
                    "confidence": round(
                        float(score),
                        4,
                    ),
                }
                for label, score in zip(
                    mlb.classes_,
                    probabilities,
                )
            ],
            key=lambda item: item["confidence"],
            reverse=True,
        )[:3]

    entities = extract_entities(
        cleaned_text
    )

    return {
        "text": cleaned_text,
        "labels": [
            item["label"]
            for item in predictions
        ],
        "confidence": {
            item["label"]: item["confidence"]
            for item in predictions
        },
        "predictions": predictions,
        "entities": entities,
        "threshold": THRESHOLD,
        "model_version": MODEL_VERSION,
        "system_type": "hybrid_ai",
    }

# =========================================================
# CONVERT AI OUTPUT TO RANKING PREFERENCES
# =========================================================

def build_ranking_preferences(
    prediction_result: dict[str, Any],
) -> dict[str, Any]:

    labels = prediction_result.get("labels", [])
    confidence = prediction_result.get("confidence", {})
    entities = prediction_result.get("entities", {})
    original_text = str(
        prediction_result.get("text", "")
    ).strip().lower()

    if not isinstance(labels, list):
        labels = []

    if not isinstance(confidence, dict):
        confidence = {}

    if not isinstance(entities, dict):
        entities = {}

    normalized_labels = {
        str(label).strip().lower()
        for label in labels
    }

    readable_labels = [
        label.replace("_", " ")
        for label in normalized_labels
    ]

    # Begin with exact entities extracted from the user's text.
    preferences: dict[str, Any] = {}

    # Keep raw model output for debugging and research reporting,
    # but do not automatically use every prediction for ranking.
    preferences["labels"] = sorted(readable_labels)
    preferences["predicted_labels"] = sorted(
        readable_labels
    )
    preferences["confidence"] = confidence

    # =====================================================
    # DETECT WHAT THE USER ACTUALLY MENTIONED
    # =====================================================

    mentions_cat = bool(
        re.search(
            r"\b(cat|kitten|feline)\b",
            original_text,
        )
    )

    mentions_dog = bool(
        re.search(
            r"\b(dog|puppy|canine)\b",
            original_text,
        )
    )

    mentions_apartment = bool(
        re.search(
            r"\b(apartment|condo|flat)\b",
            original_text,
        )
    )

    mentions_house = bool(
        re.search(
            r"\b(house|home with a yard|yard|garden)\b",
            original_text,
        )
    )

    mentions_children = bool(
        re.search(
            r"\b(child|children|kid|kids|baby|babies)\b",
            original_text,
        )
    )

    mentions_other_pets = bool(
        re.search(
            (
                r"\b(other pets?|another pet|existing pets?|"
                r"pets? at home|dog at home|dogs at home|"
                r"cat at home|cats at home)\b"
            ),
            original_text,
        )
    )

    mentions_activity = bool(
        re.search(
            (
                r"\b(active|energetic|athletic|exercise|"
                r"high energy|high-energy|moderate activity|"
                r"low energy|low-energy|relaxed lifestyle)\b"
            ),
            original_text,
        )
    )

    mentions_experience = bool(
        re.search(
            (
                r"\b(first pet|first-time owner|first time owner|"
                r"beginner|no experience|never owned|"
                r"experienced owner|owned pets before|"
                r"many years of experience)\b"
            ),
            original_text,
        )
    )

    mentions_schedule = bool(
        re.search(
            (
                r"\b(work from home|home all day|"
                r"home most of the day|busy schedule|"
                r"long hours|work long hours|9\s*to\s*5|"
                r"away during the day|hours? per day|"
                r"hours? daily|available all day)\b"
            ),
            original_text,
        )
    )

    temperament_patterns = {
        "calm": r"\b(calm|relaxed|easygoing|laid-back)\b",
        "quiet": r"\b(quiet|not vocal|silent)\b",
        "friendly": r"\b(friendly|social|outgoing)\b",
        "playful": r"\b(playful|likes to play)\b",
        "gentle": r"\b(gentle|patient|soft-tempered)\b",
        "independent": (
            r"\b(independent|self-sufficient|"
            r"can stay alone|comfortable alone)\b"
        ),
        "protective": r"\b(protective|guarding|guard dog)\b",
        "affectionate": r"\b(affectionate|loving|cuddly)\b",
    }

    explicitly_requested_traits = [
        trait
        for trait, pattern in temperament_patterns.items()
        if re.search(pattern, original_text)
    ]

    # =====================================================
    # EXACT ENTITY PREFERENCES
    # These have priority over ML predictions.
    # =====================================================

    entity_pet_type = str(
        entities.get("pet_type", "")
    ).strip().lower()

    if entity_pet_type in {"cat", "dog"}:
        preferences["pet_type"] = entity_pet_type

    elif mentions_cat and not mentions_dog:
        preferences["pet_type"] = "cat"

    elif mentions_dog and not mentions_cat:
        preferences["pet_type"] = "dog"

    elif mentions_cat or mentions_dog:
        # Use the model only when the text refers to pets
        # but extraction did not resolve the type.
        if "prefers_cat" in normalized_labels:
            preferences["pet_type"] = "cat"

        elif "prefers_dog" in normalized_labels:
            preferences["pet_type"] = "dog"

    breed = entities.get("breed")

    if breed:
        preferences["breed"] = str(breed).strip()

    gender = entities.get("gender")

    if gender:
        preferences["gender"] = str(gender).strip().lower()

    location = entities.get("location")

    if location:
        preferences["location"] = str(location).strip()

    size = entities.get("size")

    if size:
        preferences["size"] = str(size).strip().lower()

    if entities.get("age_years") is not None:
        preferences["age_years"] = entities["age_years"]

    if entities.get("age_months") is not None:
        preferences["age_months"] = entities["age_months"]

    # =====================================================
    # HOME TYPE
    # =====================================================

    if mentions_apartment:
        preferences["home_type"] = "apartment"
        preferences["apartment_friendly"] = True

    elif mentions_house:
        preferences["home_type"] = "house"

    # =====================================================
    # CHILD COMPATIBILITY
    # Only activate this category when children are mentioned.
    # =====================================================

    if mentions_children:
        negative_children = bool(
            re.search(
                (
                    r"\b(no children|no kids|without children|"
                    r"without kids|do not have children|"
                    r"don't have children|do not have kids|"
                    r"don't have kids)\b"
                ),
                original_text,
            )
        )

        preferences["has_children"] = not negative_children

        if not negative_children:
            preferences["child_friendly"] = True

    # =====================================================
    # OTHER-PET COMPATIBILITY
    # =====================================================

    if mentions_other_pets:
        negative_other_pets = bool(
            re.search(
                (
                    r"\b(no other pets?|without other pets?|"
                    r"do not have other pets?|"
                    r"don't have other pets?)\b"
                ),
                original_text,
            )
        )

        preferences["has_other_pets"] = (
            not negative_other_pets
        )

        if not negative_other_pets:
            preferences["pet_friendly"] = True

    # =====================================================
    # ENERGY LEVEL
    # Apply an inferred value only when activity was mentioned.
    # =====================================================

    if mentions_activity:

        if re.search(
            (
                r"\b(high energy|high-energy|very active|"
                r"energetic|athletic)\b"
            ),
            original_text,
        ):
            preferences["energy_level"] = "high"

        elif re.search(
            (
                r"\b(low energy|low-energy|relaxed lifestyle|"
                r"not very active)\b"
            ),
            original_text,
        ):
            preferences["energy_level"] = "low"

        elif "active" in normalized_labels:
            preferences["energy_level"] = "high"

        elif "low_energy" in normalized_labels:
            preferences["energy_level"] = "low"

        elif "moderate_activity" in normalized_labels:
            preferences["energy_level"] = "medium"

    # =====================================================
    # EXPERIENCE
    # =====================================================

    if mentions_experience:

        beginner_text = bool(
            re.search(
                (
                    r"\b(first pet|first-time owner|"
                    r"first time owner|beginner|"
                    r"no experience|never owned)\b"
                ),
                original_text,
            )
        )

        experienced_text = bool(
            re.search(
                (
                    r"\b(experienced owner|owned pets before|"
                    r"many years of experience)\b"
                ),
                original_text,
            )
        )

        if beginner_text:
            preferences["experience_level"] = "beginner"

        elif experienced_text:
            preferences["experience_level"] = (
                "experienced"
            )

        elif "beginner_owner" in normalized_labels:
            preferences["experience_level"] = "beginner"

        elif "experienced_owner" in normalized_labels:
            preferences["experience_level"] = (
                "experienced"
            )

    # =====================================================
    # AVAILABLE TIME
    # =====================================================

    if mentions_schedule:

        explicit_hours_match = re.search(
            (
                r"\b(\d+(?:\.\d+)?)\s*"
                r"hours?\s*(?:per day|daily|a day)?\b"
            ),
            original_text,
        )

        if explicit_hours_match:
            preferences[
                "available_attention_hours"
            ] = float(
                explicit_hours_match.group(1)
            )

        elif "limited_time" in normalized_labels:
            preferences[
                "available_attention_hours"
            ] = 2

        elif "plenty_time" in normalized_labels:
            preferences[
                "available_attention_hours"
            ] = 8

    # =====================================================
    # TEMPERAMENT
    # Use only traits directly stated by the user.
    # =====================================================

    preferences["temperament_traits"] = (
        explicitly_requested_traits
    )

    # =====================================================
    # CATEGORY-SPECIFIC CONFIDENCE WEIGHTS
    # A weight becomes active only when the category was
    # explicitly mentioned or extracted.
    # =====================================================

    preferences["weights"] = {
        "pet_type": (
            max(
                float(
                    confidence.get(
                        "prefers_cat",
                        0,
                    )
                ),
                float(
                    confidence.get(
                        "prefers_dog",
                        0,
                    )
                ),
            )
            if preferences.get("pet_type")
            else 0
        ),

        "breed": (
            1.0
            if preferences.get("breed")
            else 0
        ),

        "location": (
            1.0
            if preferences.get("location")
            else 0
        ),

        "age": (
            1.0
            if preferences.get("age_years")
            is not None
            else 0
        ),

        "size": (
            1.0
            if preferences.get("size")
            else 0
        ),

        "gender": (
            1.0
            if preferences.get("gender")
            else 0
        ),

        "apartment": (
            float(
                confidence.get(
                    "apartment_friendly",
                    1.0,
                )
            )
            if mentions_apartment
            else 0
        ),

        "child": (
            max(
                float(
                    confidence.get(
                        "child_friendly",
                        0,
                    )
                ),
                float(
                    confidence.get(
                        "good_with_children",
                        0,
                    )
                ),
                0.8,
            )
            if (
                mentions_children
                and preferences.get(
                    "child_friendly"
                )
            )
            else 0
        ),

        "pet": (
            max(
                float(
                    confidence.get(
                        "pet_friendly",
                        0,
                    )
                ),
                float(
                    confidence.get(
                        "good_with_other_pets",
                        0,
                    )
                ),
                0.8,
            )
            if (
                mentions_other_pets
                and preferences.get(
                    "pet_friendly"
                )
            )
            else 0
        ),

        "energy": (
            max(
                float(
                    confidence.get(
                        "active",
                        0,
                    )
                ),
                float(
                    confidence.get(
                        "moderate_activity",
                        0,
                    )
                ),
                float(
                    confidence.get(
                        "low_energy",
                        0,
                    )
                ),
            )
            if mentions_activity
            else 0
        ),

        "experience": (
            max(
                float(
                    confidence.get(
                        "beginner_owner",
                        0,
                    )
                ),
                float(
                    confidence.get(
                        "experienced_owner",
                        0,
                    )
                ),
            )
            if mentions_experience
            else 0
        ),

        "time": (
            max(
                float(
                    confidence.get(
                        "limited_time",
                        0,
                    )
                ),
                float(
                    confidence.get(
                        "plenty_time",
                        0,
                    )
                ),
            )
            if mentions_schedule
            else 0
        ),

        "temperament": (
            1.0
            if explicitly_requested_traits
            else 0
        ),
    }

    # Useful for debugging and proving that the system
    # distinguishes explicit input from inferred predictions.
    preferences["explicit_categories"] = {
        "pet_type": bool(
            preferences.get("pet_type")
        ),
        "breed": bool(
            preferences.get("breed")
        ),
        "age": (
            preferences.get("age_years")
            is not None
        ),
        "location": bool(
            preferences.get("location")
        ),
        "size": bool(
            preferences.get("size")
        ),
        "gender": bool(
            preferences.get("gender")
        ),
        "home": (
            mentions_apartment
            or mentions_house
        ),
        "children": mentions_children,
        "other_pets": mentions_other_pets,
        "activity": mentions_activity,
        "experience": mentions_experience,
        "schedule": mentions_schedule,
        "temperament": bool(
            explicitly_requested_traits
        ),
    }

    preferences[
        "preference_builder_version"
    ] = "explicit-aware-v3"

    return preferences

# =========================================================
# API ROUTES
# =========================================================

@app.get("/")
def root():

    return {
        "message": (
            "PawConnect Hybrid AI API is running"
        ),
        "status": "ready",
        "model_version": MODEL_VERSION,
        "threshold": THRESHOLD,
        "label_count": len(
            mlb.classes_
        ),
        "entity_extraction": True,
        "ranking_engine": True,
        "system_type": "hybrid_ai",
    }


@app.get("/health")
def health():

    return {
        "status": "healthy",
        "model_loaded": True,
        "entity_engine_loaded": True,
        "ranking_engine_loaded": True,
        "model_version": MODEL_VERSION,
    }


@app.post("/extract")
def extract(
    data: UserInput,
):

    text = data.text.strip()

    if not text:

        raise HTTPException(
            status_code=400,
            detail="Please enter a description.",
        )

    return {
        "text": text,
        "entities": extract_entities(
            text
        ),
    }


@app.post("/predict")
def predict(
    data: UserInput,
):

    return run_prediction(
        data.text
    )


@app.post("/recommend")
def recommend(
    data: RecommendationInput,
):

    text = data.text.strip()

    if not text:

        raise HTTPException(
            status_code=400,
            detail="Please enter a pet preference.",
        )

    if not data.animals:

        raise HTTPException(
            status_code=400,
            detail="No animals supplied.",
        )

    try:

        # -----------------------------
        # AI Prediction
        # -----------------------------

        prediction = run_prediction(
            text
        )

        preferences = (
            build_ranking_preferences(
                prediction
            )
        )

        animals = [
            animal.model_dump()
            for animal in data.animals
        ]

        available_animals = [

            animal

            for animal in animals

            if str(
                animal.get(
                    "adoption_status",
                    "available",
                )
            ).strip().lower()
            == "available"

        ]

        if not available_animals:

            raise HTTPException(
                status_code=400,
                detail=(
                    "No available animals."
                ),
            )

        # -----------------------------
        # AI Ranking
        # -----------------------------

        ranking_result = rank_animals(

            animals=available_animals,

            preferences=preferences,

            recommendation_limit=
            data.recommendation_limit,

        )

        # -----------------------------
        # Response
        # -----------------------------

        return {

            "text": text,

            "labels":
                prediction["labels"],

            "confidence":
                prediction["confidence"],

            "predictions":
                prediction["predictions"],

            "entities":
                prediction["entities"],

            "preferences":
                preferences,

            "best_match":
                ranking_result[
                    "best_match"
                ],

            "other_recommendations":
                ranking_result[
                    "other_recommendations"
                ],

            "recommendations":
                ranking_result[
                    "recommendations"
                ],

            "total_scored":
                ranking_result[
                    "total_scored"
                ],

            "threshold":
                THRESHOLD,

            "model_version":
                MODEL_VERSION,

            "system_type":
                "hybrid_ai_with_ranking",
        }

    except HTTPException:
        raise

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Recommendation failed: "
                f"{str(exc)}"
            ),
        ) from exc


# =========================================================
# RUN SERVER
# =========================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )