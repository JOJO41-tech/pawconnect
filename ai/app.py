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

    labels = prediction_result.get(
        "labels",
        [],
    )

    confidence = prediction_result.get(
        "confidence",
        {},
    )

    entities = prediction_result.get(
        "entities",
        {},
    )

    if not isinstance(
        entities,
        dict,
    ):
        entities = {}

    preferences: dict[str, Any] = dict(
        entities
    )

    readable_labels = [
        str(label)
        .strip()
        .lower()
        .replace(
            "_",
            " ",
        )
        for label in labels
    ]

    preferences["labels"] = readable_labels
    preferences["predicted_labels"] = readable_labels
    preferences["temperament_traits"] = readable_labels

    # -------------------------------------------------
    # Save AI confidence
    # ranking.py will use these as weights.
    # -------------------------------------------------

    preferences["confidence"] = confidence

    # -------------------------------------------------
    # Pet Type
    # -------------------------------------------------

    if "prefers_dog" in labels:
        preferences["pet_type"] = "dog"

    elif "prefers_cat" in labels:
        preferences["pet_type"] = "cat"

    # -------------------------------------------------
    # Home Type
    # -------------------------------------------------

    if "apartment_friendly" in labels:

        preferences[
            "apartment_friendly"
        ] = True

        preferences.setdefault(
            "home_type",
            "apartment",
        )

    elif "house_friendly" in labels:

        preferences.setdefault(
            "home_type",
            "house",
        )

    # -------------------------------------------------
    # Child Friendly
    # -------------------------------------------------

    if (
        "child_friendly" in labels
        or "good_with_children" in labels
    ):

        preferences[
            "child_friendly"
        ] = True

    # -------------------------------------------------
    # Pet Friendly
    # -------------------------------------------------

    if (
        "pet_friendly" in labels
        or "good_with_other_pets" in labels
    ):

        preferences[
            "pet_friendly"
        ] = True

    # -------------------------------------------------
    # Energy Level
    # -------------------------------------------------

    if "active" in labels:

        preferences[
            "energy_level"
        ] = "high"

    elif (
        "moderate_activity"
        in labels
    ):

        preferences[
            "energy_level"
        ] = "medium"

    elif "low_energy" in labels:

        preferences[
            "energy_level"
        ] = "low"

    # -------------------------------------------------
    # Experience
    # -------------------------------------------------

    if "beginner_owner" in labels:

        preferences[
            "experience_level"
        ] = "beginner"

    elif (
        "experienced_owner"
        in labels
    ):

        preferences[
            "experience_level"
        ] = "experienced"

    # -------------------------------------------------
    # Available Time
    # -------------------------------------------------

    if "limited_time" in labels:

        preferences[
            "available_attention_hours"
        ] = 2

    elif "plenty_time" in labels:

        preferences[
            "available_attention_hours"
        ] = 8

    # -------------------------------------------------
    # Exact Entity Overrides
    # -------------------------------------------------

    if entities.get("pet_type"):
        preferences["pet_type"] = entities["pet_type"]

    if entities.get("breed"):
        preferences["breed"] = entities["breed"]

    if entities.get("gender"):
        preferences["gender"] = entities["gender"]

    if entities.get("location"):
        preferences["location"] = entities["location"]

    if entities.get("size"):
        preferences["size"] = entities["size"]

    if entities.get("age_years") is not None:
        preferences["age_years"] = entities["age_years"]

    # -------------------------------------------------
    # AI Confidence Weights
    # ranking.py uses these values directly.
    # -------------------------------------------------

    preferences["weights"] = {

        "pet_type":
            max(
                confidence.get(
                    "prefers_cat",
                    0,
                ),
                confidence.get(
                    "prefers_dog",
                    0,
                ),
            ),

        "energy":
            max(
                confidence.get(
                    "active",
                    0,
                ),
                confidence.get(
                    "moderate_activity",
                    0,
                ),
                confidence.get(
                    "low_energy",
                    0,
                ),
            ),

        "apartment":
            confidence.get(
                "apartment_friendly",
                0,
            ),

        "child":
            max(
                confidence.get(
                    "child_friendly",
                    0,
                ),
                confidence.get(
                    "good_with_children",
                    0,
                ),
            ),

        "pet":
            max(
                confidence.get(
                    "pet_friendly",
                    0,
                ),
                confidence.get(
                    "good_with_other_pets",
                    0,
                ),
            ),

        "experience":
            max(
                confidence.get(
                    "beginner_owner",
                    0,
                ),
                confidence.get(
                    "experienced_owner",
                    0,
                ),
            ),

        "time":
            max(
                confidence.get(
                    "limited_time",
                    0,
                ),
                confidence.get(
                    "plenty_time",
                    0,
                ),
            ),
    }

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