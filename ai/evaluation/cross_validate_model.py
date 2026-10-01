"""
K-fold cross-validation of the TF-IDF + One-vs-Rest Logistic
Regression preference classifier.

Addresses reviewer requests for cross-validation. Uses exactly the
hyperparameters of train_pawconnect_ai_v4.py. Folds are drawn from
the train + validation splits; the held-out test split is never
used here. The decision threshold is tuned inside each fold on an
inner 10% split of that fold's training data, so the fold's
evaluation data is never used for model selection.

Run:
    python evaluation/cross_validate_model.py [--folds 5] [--seed 20260729]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import KFold, train_test_split
from sklearn.multiclass import OneVsRestClassifier
from sklearn.preprocessing import MultiLabelBinarizer


# =========================================================
# PATH SETUP
# =========================================================

CURRENT_DIR = Path(__file__).resolve().parent
AI_DIR = CURRENT_DIR.parent

if str(AI_DIR) not in sys.path:
    sys.path.insert(0, str(AI_DIR))

from train_pawconnect_ai_v4 import (  # noqa: E402
    TRAIN_FILE,
    VALIDATION_FILE,
    load_jsonl,
    metrics,
)


# =========================================================
# FILES & CONFIGURATION
# =========================================================

RESULTS_DIR = CURRENT_DIR / "results"
OUTPUT_FILE = RESULTS_DIR / "cross_validation_summary.json"

THRESHOLDS = np.arange(0.30, 0.86, 0.05)


def build_model(seed: int):
    vectorizer = TfidfVectorizer(
        lowercase=True,
        strip_accents="unicode",
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.98,
        sublinear_tf=True,
        max_features=50000,
    )
    model = OneVsRestClassifier(
        LogisticRegression(
            solver="liblinear",
            max_iter=2000,
            class_weight="balanced",
            random_state=seed,
        ),
        n_jobs=1,
    )
    return vectorizer, model


def run_fold(texts, y, train_idx, eval_idx, seed):
    inner_train, inner_val = train_test_split(train_idx, test_size=0.1, random_state=seed)

    vectorizer, model = build_model(seed)
    x_inner = vectorizer.fit_transform([texts[i] for i in inner_train])
    model.fit(x_inner, y[inner_train])

    val_probs = model.predict_proba(vectorizer.transform([texts[i] for i in inner_val]))
    threshold = max(THRESHOLDS, key=lambda t: metrics(y[inner_val], val_probs, float(t))["micro_f1"])

    # Refit on the full fold training data with the selected threshold.
    vectorizer, model = build_model(seed)
    x_train = vectorizer.fit_transform([texts[i] for i in train_idx])
    model.fit(x_train, y[train_idx])

    eval_probs = model.predict_proba(vectorizer.transform([texts[i] for i in eval_idx]))
    result = metrics(y[eval_idx], eval_probs, float(threshold))
    result["threshold"] = round(float(threshold), 2)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--seed", type=int, default=20260729)
    args = parser.parse_args()

    train_texts, train_labels = load_jsonl(TRAIN_FILE)
    val_texts, val_labels = load_jsonl(VALIDATION_FILE)
    texts = train_texts + val_texts
    labels = train_labels + val_labels

    mlb = MultiLabelBinarizer()
    y = mlb.fit_transform(labels)

    print("=" * 72)
    print(f"PAWCONNECT {args.folds}-FOLD CROSS-VALIDATION (TF-IDF + OvR LR)")
    print("=" * 72)
    print(f"Samples: {len(texts)}   Labels: {len(mlb.classes_)}   Seed: {args.seed}")

    folds = []
    splitter = KFold(n_splits=args.folds, shuffle=True, random_state=args.seed)

    for fold, (train_idx, eval_idx) in enumerate(splitter.split(texts), start=1):
        result = run_fold(texts, y, train_idx, eval_idx, args.seed)
        folds.append(result)
        print(
            f"Fold {fold}: micro-F1 {result['micro_f1']:.4f}  macro-F1 {result['macro_f1']:.4f}  "
            f"exact-match {result['exact_match_ratio']:.4f}  threshold {result['threshold']}"
        )

    metric_names = [k for k in folds[0] if k != "threshold"]
    aggregate = {
        name: {
            "mean": float(np.mean([f[name] for f in folds])),
            "std": float(np.std([f[name] for f in folds], ddof=1)),
        }
        for name in metric_names
    }

    print("-" * 72)
    for name, value in aggregate.items():
        print(f"{name:<20} {value['mean']:.4f} +/- {value['std']:.4f}")

    output = {
        "model": "TF-IDF (1-2 grams) + One-vs-Rest Logistic Regression (v4 hyperparameters)",
        "folds": args.folds,
        "seed": args.seed,
        "samples": len(texts),
        "labels": len(mlb.classes_),
        "threshold_selection": "per fold, on an inner 10% split of the fold's training data",
        "per_fold": folds,
        "mean_std": aggregate,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print()
    print("Results saved to:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
