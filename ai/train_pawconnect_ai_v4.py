from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.multiclass import OneVsRestClassifier
from sklearn.preprocessing import MultiLabelBinarizer

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

TRAIN_FILE = DATA_DIR / "pawconnect_v4_train.jsonl"
VALIDATION_FILE = DATA_DIR / "pawconnect_v4_validation.jsonl"
TEST_FILE = DATA_DIR / "pawconnect_v4_test.jsonl"

MODEL_PATH = BASE_DIR / "pawconnect_multilabel_model_v4.joblib"
FEATURES_PATH = BASE_DIR / "pawconnect_text_features_v4.joblib"
MLB_PATH = BASE_DIR / "pawconnect_label_binarizer_v4.joblib"
CONFIG_PATH = BASE_DIR / "pawconnect_model_config_v4.json"
EVALUATION_PATH = BASE_DIR / "pawconnect_model_evaluation_v4.json"

def load_jsonl(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing dataset file: {path}")
    texts, labels = [], []
    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            text = row.get("text")
            row_labels = row.get("labels")
            if not isinstance(text, str) or not text.strip():
                raise ValueError(f"Invalid text at {path.name}:{line_number}")
            if not isinstance(row_labels, list):
                raise ValueError(f"Invalid labels at {path.name}:{line_number}")
            texts.append(text.strip())
            labels.append(sorted(set(row_labels)))
    return texts, labels

def metrics(y_true, probabilities, threshold):
    pred = (probabilities >= threshold).astype(int)
    return {
        "micro_precision": float(precision_score(y_true, pred, average="micro", zero_division=0)),
        "micro_recall": float(recall_score(y_true, pred, average="micro", zero_division=0)),
        "micro_f1": float(f1_score(y_true, pred, average="micro", zero_division=0)),
        "macro_f1": float(f1_score(y_true, pred, average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(y_true, pred, average="weighted", zero_division=0)),
        "exact_match_ratio": float(accuracy_score(y_true, pred)),
    }

def main():
    print("Loading PawConnect v4 clean dataset...")
    train_texts, train_labels = load_jsonl(TRAIN_FILE)
    val_texts, val_labels = load_jsonl(VALIDATION_FILE)
    test_texts, test_labels = load_jsonl(TEST_FILE)

    print(f"Training samples:   {len(train_texts)}")
    print(f"Validation samples: {len(val_texts)}")
    print(f"Test samples:       {len(test_texts)}")

    mlb = MultiLabelBinarizer()
    y_train = mlb.fit_transform(train_labels)
    y_val = mlb.transform(val_labels)
    y_test = mlb.transform(test_labels)

    vectorizer = TfidfVectorizer(
        lowercase=True,
        strip_accents="unicode",
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.98,
        sublinear_tf=True,
        max_features=50000,
    )

    print("Building TF-IDF features...")
    x_train = vectorizer.fit_transform(train_texts)
    x_val = vectorizer.transform(val_texts)
    x_test = vectorizer.transform(test_texts)

    model = OneVsRestClassifier(
        LogisticRegression(
            solver="liblinear",
            max_iter=2000,
            class_weight="balanced",
            random_state=20260729,
        ),
        n_jobs=1,
    )

    print("Training Version 4 model...")
    model.fit(x_train, y_train)

    val_probs = model.predict_proba(x_val)
    best_threshold, best_score = 0.50, -1.0
    validation_metrics = {}

    for threshold in np.arange(0.30, 0.86, 0.05):
        current = metrics(y_val, val_probs, float(threshold))
        if current["micro_f1"] > best_score:
            best_score = current["micro_f1"]
            best_threshold = round(float(threshold), 2)
            validation_metrics = current

    print(f"Best threshold: {best_threshold}")
    print(f"Validation micro-F1: {validation_metrics['micro_f1']:.4f}")

    test_probs = model.predict_proba(x_test)
    test_metrics = metrics(y_test, test_probs, best_threshold)

    config = {
        "model_version": "v4",
        "threshold": best_threshold,
        "labels": list(mlb.classes_),
        "label_count": len(mlb.classes_),
        "training_samples": len(train_texts),
        "validation_samples": len(val_texts),
        "test_samples": len(test_texts),
        "exact_entities_are_not_classification_labels": [
            "age_years", "breed", "size", "gender", "location"
        ]
    }

    evaluation = {
        "model_version": "v4",
        "validation": validation_metrics,
        "test": test_metrics
    }

    joblib.dump(model, MODEL_PATH)
    joblib.dump(vectorizer, FEATURES_PATH)
    joblib.dump(mlb, MLB_PATH)
    CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")
    EVALUATION_PATH.write_text(json.dumps(evaluation, indent=2), encoding="utf-8")

    print("Training completed successfully.")
    print(f"Test micro-F1: {test_metrics['micro_f1']:.4f}")
    print(f"Test macro-F1: {test_metrics['macro_f1']:.4f}")
    print(f"Exact match: {test_metrics['exact_match_ratio']:.4f}")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Training failed: {exc}", file=sys.stderr)
        sys.exit(1)
