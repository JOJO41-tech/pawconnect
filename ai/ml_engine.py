from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib


BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = BASE_DIR / "pawconnect_multilabel_model_v4.joblib"
FEATURES_PATH = BASE_DIR / "pawconnect_text_features_v4.joblib"
LABEL_BINARIZER_PATH = BASE_DIR / "pawconnect_label_binarizer_v4.joblib"
CONFIG_PATH = BASE_DIR / "pawconnect_model_config_v4.json"


model = joblib.load(MODEL_PATH)
features = joblib.load(FEATURES_PATH)
mlb = joblib.load(LABEL_BINARIZER_PATH)

with CONFIG_PATH.open(
    "r",
    encoding="utf-8",
) as file:
    config = json.load(file)


THRESHOLD = float(
    config.get(
        "threshold",
        0.45,
    )
)

MODEL_VERSION = str(
    config.get(
        "model_version",
        "v4",
    )
)


def predict_ml_only(
    text: str,
) -> dict[str, Any]:
    """
    ML-only baseline.

    IMPORTANT:
    No rule correction.
    No entity extractor.
    No hybrid reasoning.
    No hard-constraint fallback logic.

    This baseline shows the raw behavior of the
    trained v4 multi-label classifier.
    """

    cleaned_text = text.strip()

    if not cleaned_text:
        raise ValueError(
            "Text must not be empty."
        )

    X = features.transform(
        [cleaned_text]
    )

    probabilities = model.predict_proba(
        X
    )[0]

    all_scores = {
        str(label): round(
            float(score),
            4,
        )
        for label, score in zip(
            mlb.classes_,
            probabilities,
        )
    }

    selected = {
        label: score
        for label, score in all_scores.items()
        if score >= THRESHOLD
    }

    predictions = sorted(
        [
            {
                "label": label,
                "confidence": score,
            }
            for label, score in selected.items()
        ],
        key=lambda item: item["confidence"],
        reverse=True,
    )

    if not predictions:
        predictions = sorted(
            [
                {
                    "label": label,
                    "confidence": score,
                }
                for label, score in all_scores.items()
            ],
            key=lambda item: item["confidence"],
            reverse=True,
        )[:3]

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
        "threshold": THRESHOLD,
        "model_version": MODEL_VERSION,
        "system_type": "ml_only",
    }