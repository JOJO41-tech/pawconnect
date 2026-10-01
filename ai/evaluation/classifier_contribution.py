"""Part of teacher item 4: how much does the trained TF-IDF + OvR LR classifier contribute to the Hybrid?

Replaces the classifier with constant "null" models (every label probability 0, or every probability 1) and compares:
  * 60-request benchmark: ML-only and Hybrid field micro-F1 (paper scoring)
  * synthetic v4 test split (1,000): Hybrid label micro-F1
Output: results/parameter_sensitivity/classifier_contribution.csv
Run from ai/:  python evaluation/classifier_contribution.py
"""
import csv, json, sys
from pathlib import Path
import numpy as np
from sklearn.metrics import f1_score

EV = Path(__file__).resolve().parent; AI = EV.parent; sys.path[:0] = [str(AI), str(EV)]
import app, ml_engine
import evaluate_ablation as ab

OUT = EV / "results" / "parameter_sensitivity"; OUT.mkdir(parents=True, exist_ok=True)
bench = [json.loads(l) for l in open(EV / "natural_language_challenge_60.jsonl", encoding="utf-8")]
test = [json.loads(l) for l in open(AI / "data" / "pawconnect_v4_test.jsonl", encoding="utf-8")]
mlb = ml_engine.mlb; Y = mlb.transform([r["labels"] for r in test]); ORIG = ml_engine.model


class Constant:
    def __init__(self, v): self.v = v
    def predict_proba(self, X): return np.full((X.shape[0], len(mlb.classes_)), self.v)


def field_f1(fn):
    tp = fp = fn_ = 0
    for b in bench:
        a, c, d = ab.calculate_micro_counts(b["expected"], fn(b["text"]) or {}); tp += a; fp += c; fn_ += d
    p = tp / (tp + fp) if tp + fp else 0; r = tp / (tp + fn_) if tp + fn_ else 0
    return 2 * p * r / (p + r) if p + r else 0, tp, fp, fn_


rows = []
for name, model in (("trained classifier (deployed v4)", ORIG), ("null classifier: all probabilities 0", Constant(0.0)),
                    ("null classifier: all probabilities 1", Constant(1.0))):
    app.model = ml_engine.model = model
    try:
        hf, htp, hfp, hfn = field_f1(ab.full_hybrid); mf, *_ = field_f1(ab.ml_only)
        pred = mlb.transform([[l.replace(" ", "_") for l in app.run_prediction(r["text"])["labels"] if l.replace(" ", "_") in mlb.classes_] for r in test])
        syn = f1_score(Y, pred, average="micro", zero_division=0)
    finally:
        app.model = ml_engine.model = ORIG
    rows.append({"classifier": name, "benchmark60_hybrid_field_f1": round(hf, 4), "benchmark60_hybrid_tp_fp_fn": f"{htp}/{hfp}/{hfn}",
                 "benchmark60_ml_only_field_f1": round(mf, 4), "synthetic_test_hybrid_label_micro_f1": round(syn, 4)})
    print(rows[-1])
with open(OUT / "classifier_contribution.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
