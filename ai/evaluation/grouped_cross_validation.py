"""Teacher item 3: grouped cross-validation of the TF-IDF + One-vs-Rest LR preference classifier.

Why grouping matters here: all 10,000 synthetic requests are built from the same 430-sentence bank (72 label
templates = 24 labels x 3 paraphrases, 5 entity templates, 5 prefixes), so random K-fold puts identical sentences in
train and test. Three schemes are reported with identical hyper-parameters to train_pawconnect_ai_v4.py:

  S1 random 5-fold                       (reference; comparable to the earlier CV)
  S2 GroupKFold by label profile, 5-fold (no identical label set appears in both train and test)
  S3 paraphrase-template grouped, 3-fold (for fold k, the k-th paraphrase of EVERY label is held out:
                                           training requests never contain it, test requests are rendered only with it)

For every fold: threshold tuned on an inner 10% split of the training fold (never on test), metrics on the test fold,
and the fold model is also run on the 60-request benchmark through both the ML-only and full Hybrid pipelines.
Outputs (results/grouped_cv/): per_fold_metrics.csv, summary.json, raw_predictions_S1/S2/S3.csv
Run from ai/:  python evaluation/grouped_cross_validation.py
"""
import csv, json, random, re, statistics, sys
from pathlib import Path
import numpy as np
from scipy import stats as st
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import GroupKFold, KFold, train_test_split
from sklearn.multiclass import OneVsRestClassifier
from sklearn.preprocessing import MultiLabelBinarizer
EV = Path(__file__).resolve().parent; AI = EV.parent; DATA = AI / "data"; sys.path[:0] = [str(AI), str(EV)]
OUT = EV / "results" / "grouped_cv"; OUT.mkdir(parents=True, exist_ok=True)
SEED = 20260729
import reconstruct_generator as rg
spec_path = rg.SPEC
if not spec_path.exists(): rg.extract()
SPEC = json.load(open(spec_path))

rows = [r for s in ("train", "validation", "test") for r in rg.load(DATA / f"pawconnect_v4_{s}.jsonl")]
texts = [r["text"] for r in rows]; labels = [sorted(set(r["labels"])) for r in rows]
mlb = MultiLabelBinarizer(); Y = mlb.fit_transform(labels)

# ---------- paraphrase variant bookkeeping ----------
variants = {k: sorted(v) for k, v in SPEC["templates"].items()}          # label key -> 3 paraphrases (fixed alphabetical order)
core2 = {c: (k, i) for k, vs in variants.items() for i, c in enumerate(vs)}
def render(text, allowed, rng):
    """Re-render a request so every label sentence uses a paraphrase index in `allowed` (prefix/entity sentences kept)."""
    out = []
    for s in rg.split_sents(text):
        p, c = rg.strip_prefix(s)
        if c in core2:
            k, i = core2[c]
            if i not in allowed: c = variants[k][rng.choice(sorted(allowed))]
            s = c if p is None else f"{p} {c[:1].lower()}{c[1:]}"
        out.append(s)
    return " ".join(out)

def model_fit(tr_texts, tr_Y):
    vec = TfidfVectorizer(lowercase=True, strip_accents="unicode", ngram_range=(1, 2), min_df=2, max_df=0.98, sublinear_tf=True, max_features=50000)
    m = OneVsRestClassifier(LogisticRegression(solver="liblinear", max_iter=2000, class_weight="balanced", random_state=SEED), n_jobs=1)
    m.fit(vec.fit_transform(tr_texts), tr_Y); return vec, m
def metrics(Yt, P, thr):
    Yp = (P >= thr).astype(int)
    return {"micro_precision": precision_score(Yt, Yp, average="micro", zero_division=0), "micro_recall": recall_score(Yt, Yp, average="micro", zero_division=0),
            "micro_f1": f1_score(Yt, Yp, average="micro", zero_division=0), "macro_f1": f1_score(Yt, Yp, average="macro", zero_division=0),
            "exact_match": accuracy_score(Yt, Yp)}

# ---------- benchmark evaluation with a fold model plugged into the real pipelines ----------
import ml_engine, app, evaluate_ablation as ab
BENCH = [json.loads(l) for l in open(EV / "natural_language_challenge_60.jsonl")]
def bench_scores(vec, m, thr):
    saved = [(mod, {k: getattr(mod, k) for k in ("model", "features", "mlb", "THRESHOLD")}) for mod in (ml_engine, app)]
    for mod, _ in saved: mod.model, mod.features, mod.mlb, mod.THRESHOLD = m, vec, mlb, thr
    try:
        out = {}
        for name, fn in (("ML-only", ab.ml_only), ("Hybrid", ab.full_hybrid)):
            tp = fp = fn_ = 0
            for b in BENCH:
                a, bb, c = ab.calculate_micro_counts(b["expected"], fn(b["text"]) or {}); tp += a; fp += bb; fn_ += c
            p = tp / (tp + fp) if tp + fp else 0; r = tp / (tp + fn_) if tp + fn_ else 0; out[name] = 2 * p * r / (p + r) if p + r else 0
        return out
    finally:
        for mod, d in saved:
            for k, v in d.items(): setattr(mod, k, v)

def run_fold(scheme, fold, tr_idx, te_idx, tr_texts, te_texts, raw):
    inner_tr, inner_va = train_test_split(np.arange(len(tr_idx)), test_size=0.10, random_state=SEED + fold)
    vec, m = model_fit([tr_texts[i] for i in inner_tr], Y[tr_idx][inner_tr])
    Pv = m.predict_proba(vec.transform([tr_texts[i] for i in inner_va]))
    thr = max(np.round(np.arange(0.30, 0.86, 0.05), 2), key=lambda t: f1_score(Y[tr_idx][inner_va], (Pv >= t).astype(int), average="micro", zero_division=0))
    vec, m = model_fit(tr_texts, Y[tr_idx])                                   # refit on the whole training fold
    P = m.predict_proba(vec.transform(te_texts)); res = metrics(Y[te_idx], P, thr)
    res.update({"scheme": scheme, "fold": fold, "train_n": len(tr_idx), "test_n": len(te_idx), "threshold": float(thr)})
    b = bench_scores(vec, m, float(thr)); res["benchmark60_ML_only_field_F1"] = b["ML-only"]; res["benchmark60_Hybrid_field_F1"] = b["Hybrid"]
    for j, i in enumerate(te_idx):
        raw.append({"scheme": scheme, "fold": fold, "sample_id": rows[i]["sample_id"], "text_evaluated": te_texts[j], "true_labels": " ".join(labels[i]),
                    "predicted_labels": " ".join(l for l, p in zip(mlb.classes_, P[j]) if p >= thr),
                    "probabilities": json.dumps({l: round(float(p), 4) for l, p in zip(mlb.classes_, P[j])})})
    print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in res.items()}, flush=True)
    return res

results = []; idx = np.arange(len(rows))
raw = []
for f, (tr, te) in enumerate(KFold(5, shuffle=True, random_state=SEED).split(idx), 1):
    results.append(run_fold("S1 random 5-fold", f, tr, te, [texts[i] for i in tr], [texts[i] for i in te], raw))
with open(OUT / "raw_predictions_S1.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(raw[0])); w.writeheader(); w.writerows(raw)
raw = []; groups = ["+".join(l) for l in labels]
for f, (tr, te) in enumerate(GroupKFold(5).split(idx, groups=groups), 1):
    assert not ({groups[i] for i in tr} & {groups[i] for i in te})
    results.append(run_fold("S2 GroupKFold by label profile", f, tr, te, [texts[i] for i in tr], [texts[i] for i in te], raw))
with open(OUT / "raw_predictions_S2.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(raw[0])); w.writeheader(); w.writerows(raw)
raw = []; splits = list(KFold(5, shuffle=True, random_state=SEED + 1).split(idx))
for k in range(3):
    tr, te = splits[k]; rng = random.Random(SEED + k); allowed_tr = {0, 1, 2} - {k}
    tr_t = [render(texts[i], allowed_tr, rng) for i in tr]; te_t = [render(texts[i], {k}, rng) for i in te]
    held = {variants[key][k] for key in variants}
    assert not any(c in held for t in tr_t for c in (rg.strip_prefix(s)[1] for s in rg.split_sents(t)))
    results.append(run_fold("S3 paraphrase-template grouped 3-fold (fold k holds out paraphrase k)", k + 1, tr, te, tr_t, te_t, raw))
with open(OUT / "raw_predictions_S3.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(raw[0])); w.writeheader(); w.writerows(raw)

keys = ["micro_precision", "micro_recall", "micro_f1", "macro_f1", "exact_match", "benchmark60_ML_only_field_F1", "benchmark60_Hybrid_field_F1"]
with open(OUT / "per_fold_metrics.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=["scheme", "fold", "train_n", "test_n", "threshold"] + keys); w.writeheader()
    for r in results: w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items() if k in w.fieldnames})
summary = {}
for sch in dict.fromkeys(r["scheme"] for r in results):
    R = [r for r in results if r["scheme"] == sch]; n = len(R); summary[sch] = {"folds": n}
    for k in keys:
        v = [r[k] for r in R]; m = statistics.mean(v); sd = statistics.stdev(v) if n > 1 else 0.0; h = st.t.ppf(.975, n - 1) * sd / n ** .5 if n > 1 else 0
        summary[sch][k] = {"mean": round(m, 4), "sd": round(sd, 4), "ci95_t": [round(m - h, 4), round(m + h, 4)]}
summary["note"] = ("S3 holds out one paraphrase per label (label-sentence wording unseen in training); entity templates and discourse prefixes "
                   "have a single form and therefore remain seen. Benchmark columns: field-level micro-F1 on the 60 author-written requests.")
json.dump(summary, open(OUT / "summary.json", "w"), indent=1)
print(json.dumps(summary, indent=1))
