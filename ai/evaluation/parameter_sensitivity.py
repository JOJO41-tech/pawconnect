"""Teacher item 4: parameter / weight sensitivity.

  (a) decision threshold   0.30-0.85 on the deployed v4 model
  (b) LR regularisation C  0.01-100, retrained on the v4 training split (threshold re-tuned on validation, as in training)
  (c) preferred weights    current vs equal vs rank-order-centroid vs 100 random +/-50 % draws, on BOTH the 1,000 generated
                           scenarios and the 60 real requests over the 85-animal catalogue (gold and Hybrid extraction)
  (d) fallback ratio       required/preferred blend in Alternative mode (0.5-1.0, current 0.7) and the lexicographic fix,
                           on the 25 original scenarios, the fallback-ordering traps and the generated fallback scenarios

For (a) and (b) each setting is scored on the synthetic v4 test split (label micro-F1) and on the 60-request benchmark
(ML-only and Hybrid field micro-F1, as in the paper).
Outputs: results/parameter_sensitivity/{threshold,C,weights,fallback_ratio}.csv and summary.json
Run from ai/:  python evaluation/parameter_sensitivity.py
"""
from __future__ import annotations

import copy, csv, json, math, random, sys
from pathlib import Path

import numpy as np
from scipy.stats import kendalltau
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.multiclass import OneVsRestClassifier

EV = Path(__file__).resolve().parent
AI = EV.parent
sys.path[:0] = [str(AI), str(EV)]
OUT = EV / "results" / "parameter_sensitivity"
OUT.mkdir(parents=True, exist_ok=True)

import app, ml_engine, scoring_engine
import evaluate_ablation as ab
import evaluate_recommendation_reasoning as err
from ranking import rank_animals
from scenario_generator import relevance as gen_relevance

SEED = 20260729
load = lambda p: [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
TR, VA, TE = (load(AI / "data" / f"pawconnect_v4_{s}.jsonl") for s in ("train", "validation", "test"))
BENCH = load(EV / "natural_language_challenge_60.jsonl")
MLB = ml_engine.mlb
Yte = MLB.transform([r["labels"] for r in TE])


def swap(model, feats, thr):
    for m in (app, ml_engine):
        m.model, m.features, m.THRESHOLD = model, feats, thr


ORIG = (ml_engine.model, ml_engine.features, ml_engine.THRESHOLD)


def bench(fn):
    tp = fp = fn_ = 0
    for b in BENCH:
        a, c, d = ab.calculate_micro_counts(b["expected"], fn(b["text"]) or {})
        tp += a; fp += c; fn_ += d
    p = tp / (tp + fp) if tp + fp else 0; r = tp / (tp + fn_) if tp + fn_ else 0
    return 2 * p * r / (p + r) if p + r else 0


def score_setting(model, feats, thr):
    swap(model, feats, thr)
    try:
        P = model.predict_proba(feats.transform([r["text"] for r in TE]))
        return {"synthetic_test_label_micro_f1": f1_score(Yte, (P >= thr).astype(int), average="micro", zero_division=0),
                "benchmark_ml_only_field_f1": bench(ab.ml_only), "benchmark_hybrid_field_f1": bench(ab.full_hybrid)}
    finally:
        swap(*ORIG)


def write(name, rows):
    with open(OUT / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader()
        w.writerows([{k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()} for r in rows])


summary = {}
# ---------------- (a) threshold ----------------
print("(a) threshold")
th_rows = []
for t in [round(x, 2) for x in np.arange(0.30, 0.86, 0.05)]:
    r = {"threshold": t, "is_deployed": t == round(ORIG[2], 2), **score_setting(ORIG[0], ORIG[1], t)}
    th_rows.append(r); print("  ", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})
write("threshold", th_rows)
summary["threshold"] = {"deployed": ORIG[2], "hybrid_f1_range": [min(r["benchmark_hybrid_field_f1"] for r in th_rows), max(r["benchmark_hybrid_field_f1"] for r in th_rows)],
                        "best_hybrid_threshold": max(th_rows, key=lambda r: r["benchmark_hybrid_field_f1"])["threshold"]}

# ---------------- (b) C ----------------
print("(b) C")
c_rows = []
Ytr, Yva = MLB.transform([r["labels"] for r in TR]), MLB.transform([r["labels"] for r in VA])
for C in [0.01, 0.1, 1.0, 10.0, 100.0]:
    vec = TfidfVectorizer(lowercase=True, strip_accents="unicode", ngram_range=(1, 2), min_df=2, max_df=0.98, sublinear_tf=True, max_features=50000)
    clf = OneVsRestClassifier(LogisticRegression(C=C, solver="liblinear", max_iter=2000, class_weight="balanced", random_state=SEED), n_jobs=1)
    clf.fit(vec.fit_transform([r["text"] for r in TR]), Ytr)
    pv = clf.predict_proba(vec.transform([r["text"] for r in VA]))
    thr = max([round(x, 2) for x in np.arange(0.30, 0.86, 0.05)], key=lambda t: f1_score(Yva, (pv >= t).astype(int), average="micro", zero_division=0))
    r = {"C": C, "is_deployed": C == 1.0, "tuned_threshold": thr, **score_setting(clf, vec, thr)}
    c_rows.append(r); print("  ", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})
write("C", c_rows)
summary["C"] = {"deployed": 1.0, "hybrid_f1_range": [min(r["benchmark_hybrid_field_f1"] for r in c_rows), max(r["benchmark_hybrid_field_f1"] for r in c_rows)]}

# ---------------- (c) weights ----------------
print("(c) weights")
KEYS = ["energy_level", "temperament", "apartment_friendly", "experience_level", "available_attention_hours", "child_friendly", "pet_friendly"]
CUR = dict(scoring_engine.WEIGHTS)
roc = [sum(1 / j for j in range(i, 8)) / 7 for i in range(1, 8)]
rng = random.Random(2026)
SETS = [("current", CUR), ("equal", {k: 1.0 for k in KEYS}), ("rank-order centroid", dict(zip(KEYS, roc)))] + \
       [(f"random_{i:03d}", {k: CUR[k] * rng.uniform(0.5, 1.5) for k in KEYS}) for i in range(100)]
dcg = lambda g: sum((2 ** x - 1) / math.log2(i + 2) for i, x in enumerate(g))
GEN = json.load(open(EV / "generated_ranking_scenarios.json"))
import importlib.util
spec = importlib.util.spec_from_file_location("e2e", EV / "evaluate_e2e_ranking.py")
sys.argv = ["e2e", str(EV / "animals_catalogue_snapshot_2026-09-30.csv"), str(OUT / "_e2e_tmp.json")]
import contextlib, io
with contextlib.redirect_stdout(io.StringIO()):
    e2e = importlib.util.module_from_spec(spec); spec.loader.exec_module(e2e)
(OUT / "_e2e_tmp.json").unlink(missing_ok=True)
REAL = []
for case in e2e.bench:
    gold = e2e.std(case["expected"], "gold", case["text"])
    REAL.append((gold, e2e.hy[case["id"]], {a["id"]: e2e.relevance(a, gold) for a in e2e.POOL}))


def eval_weights(w):
    scoring_engine.WEIGHTS.clear(); scoring_engine.WEIGHTS.update(w)
    gen_nd, gen_rank = [], []
    for sc in GEN:
        ids = [r["id"] for r in rank_animals(copy.deepcopy(sc["animals"]), copy.deepcopy(sc["preferences"]), 20)["recommendations"]]
        g = {a["id"]: gen_relevance(a, sc["preferences"]) for a in sc["animals"]}
        ideal = dcg(sorted(g.values(), reverse=True)[:5]); gen_nd.append(dcg([g[i] for i in ids[:5]]) / ideal if ideal else np.nan); gen_rank.append(ids)
    real = {}
    for label, pick in (("gold", 0), ("hybrid", 1)):
        nd, rk = [], []
        for gold, hyp, grade in REAL:
            prefs = gold if pick == 0 else hyp
            ids = [r["id"] for r in rank_animals(copy.deepcopy(e2e.POOL), copy.deepcopy(prefs), 20)["recommendations"]]
            ideal = dcg(sorted(grade.values(), reverse=True)[:5]); nd.append(dcg([grade[i] for i in ids[:5]]) / ideal if ideal else 0); rk.append(ids)
        real[label] = (np.mean(nd), rk)
    return float(np.nanmean(gen_nd)), gen_rank, real


base_gen, base_rank, base_real = eval_weights(CUR)
w_rows = []
for name, w in SETS:
    g, rk, real = eval_weights(w)
    def agree(a_list, b_list):
        taus, top1, jac = [], [], []
        for a, b in zip(a_list, b_list):
            if len(a) > 1 and set(a) == set(b):
                pos = {x: i for i, x in enumerate(b)}; t = kendalltau(range(len(a)), [pos[x] for x in a]).statistic
                if not np.isnan(t): taus.append(t)
            if a and b: top1.append(a[0] == b[0])
            A, B = set(a[:5]), set(b[:5])
            if A | B: jac.append(len(A & B) / len(A | B))
        return np.mean(taus), np.mean(top1), np.mean(jac)
    gt, g1, gj = agree(base_rank, rk); rt, r1, rj = agree(base_real["hybrid"][1], real["hybrid"][1])
    w_rows.append({"weights": name, **{f"w_{k}": round(w[k], 3) for k in KEYS},
                   "generated_ndcg5": g, "generated_delta": g - base_gen, "generated_kendall_tau": gt, "generated_top1_agree": g1, "generated_top5_jaccard": gj,
                   "real_gold_ndcg5": real["gold"][0], "real_hybrid_ndcg5": real["hybrid"][0], "real_hybrid_delta": real["hybrid"][0] - base_real["hybrid"][0],
                   "real_hybrid_kendall_tau": rt, "real_hybrid_top1_agree": r1, "real_hybrid_top5_jaccard": rj})
scoring_engine.WEIGHTS.clear(); scoring_engine.WEIGHTS.update(CUR)
write("weights", w_rows)
rand = [r for r in w_rows if r["weights"].startswith("random")]
summary["weights"] = {r["weights"]: {k: round(r[k], 4) for k in ("generated_ndcg5", "real_gold_ndcg5", "real_hybrid_ndcg5", "real_hybrid_top5_jaccard")} for r in w_rows[:3]}
summary["weights"]["random_100_range"] = {k: [round(min(r[k] for r in rand), 4), round(max(r[k] for r in rand), 4)]
                                          for k in ("generated_ndcg5", "generated_delta", "real_hybrid_ndcg5", "real_hybrid_delta", "real_hybrid_top5_jaccard", "real_hybrid_top1_agree")}
print("  ", json.dumps(summary["weights"]))

# ---------------- (d) fallback ratio ----------------
print("(d) fallback ratio")
orig_final = scoring_engine.calculate_final_compatibility
orig_sort_key_src = None


def make_final(alpha):
    def final(*, animal, preferred_percentage, has_preferred_constraints):
        mode = str(animal.get("recommendation_mode", "exact")).strip().lower()
        req = scoring_engine._required_percentage(animal)
        if mode == "alternative" and has_preferred_constraints:
            return scoring_engine._clamp_score(req * alpha + preferred_percentage * (1 - alpha))
        return orig_final(animal=animal, preferred_percentage=preferred_percentage, has_preferred_constraints=has_preferred_constraints)
    return final


ADV = json.load(open(EV / "results" / "adversarial_results.json"))


def o_family_pass():
    import importlib
    src = (EV / "evaluate_adversarial_traps.py").read_text(encoding="utf-8")
    ns = {"__file__": str(EV / "evaluate_adversarial_traps.py"), "__name__": "o_only"}
    exec(src.split("rows = []")[0], ns)  # builds scenarios without running the suite
    res = []
    for sc in ns["scenarios"]:
        if sc["family"] != "O":
            continue
        ids = [r["id"] for r in rank_animals(copy.deepcopy(sc["animals"]), copy.deepcopy(sc["prefs"]), 4)["recommendations"]]
        res.append(ids[:1] == [1])
    return sum(res), len(res)


FALLBACK_GEN = [sc for sc in GEN if rank_animals(copy.deepcopy(sc["animals"]), copy.deepcopy(sc["preferences"]), 20)["mode"] == "alternative"]


def required_order_violations(cases):
    """Alternative-mode lists where an animal meeting FEWER required constraints is ranked above one meeting more."""
    bad = tot = 0
    for animals, prefs in cases:
        res = rank_animals(copy.deepcopy(animals), copy.deepcopy(prefs), 20)
        if res["mode"] != "alternative":
            continue
        tot += 1
        fails = [len(r.get("failed_required_constraints", [])) for r in res["recommendations"]]
        bad += any(fails[i] > fails[j] for i in range(len(fails)) for j in range(i + 1, len(fails)))
    return bad, tot


def gen_fallback_ndcg():
    nd = []
    for sc in FALLBACK_GEN:
        ids = [r["id"] for r in rank_animals(copy.deepcopy(sc["animals"]), copy.deepcopy(sc["preferences"]), 20)["recommendations"]]
        g = {a["id"]: gen_relevance(a, sc["preferences"]) for a in sc["animals"]}
        ideal = dcg(sorted(g.values(), reverse=True)[:5]); nd.append(dcg([g[i] for i in ids[:5]]) / ideal if ideal else np.nan)
    return float(np.nanmean(nd))


cases25 = json.load(open(EV / "recommendation_challenge_25.json", encoding="utf-8"))
f_rows = []
settings = [(a, f"alpha={a:.1f}") for a in (0.5, 0.6, 0.7, 0.8, 0.9, 1.0)] + [("lex", "lexicographic (fewer failed required first, then 0.7 blend)")]
for a, label in settings:
    if a == "lex":
        scoring_engine.calculate_final_compatibility = make_final(0.7)
        orig_rank = scoring_engine.rank_candidates
        def lex_rank(candidates, preferred, preferred_confidence=None, _o=orig_rank):
            ranked = _o(candidates, preferred, preferred_confidence)
            return sorted(ranked, key=lambda x: len(x.get("failed_required_constraints", [])))  # stable: keeps score order within ties
        scoring_engine.rank_candidates = lex_rank
        import ranking as _rk; _rk.rank_candidates = lex_rank
    else:
        scoring_engine.calculate_final_compatibility = make_final(a)
    try:
        r25 = [err.evaluate_case(c) for c in cases25]
        passes = sum(bool(r.get("overall_pass")) for r in r25)
        op, on = o_family_pass()
        f_rows.append({"setting": label, "is_deployed": a == 0.7, "scenarios25_pass": passes, "scenarios25_total": len(r25),
                       "fallback_ordering_traps_pass": op, "fallback_ordering_traps_total": on,
                       "generated_fallback_scenarios": len(FALLBACK_GEN), "generated_fallback_ndcg5": gen_fallback_ndcg(),
                       **dict(zip(["generated_fallback_order_violations", "generated_fallback_lists"],
                                  required_order_violations([(sc["animals"], sc["preferences"]) for sc in FALLBACK_GEN]))),
                       **dict(zip(["scenarios25_fallback_order_violations", "scenarios25_fallback_lists"],
                                  required_order_violations([(c["animals"], c["preferences"]) for c in cases25])))})
        print("  ", f_rows[-1])
    finally:
        scoring_engine.calculate_final_compatibility = orig_final
        if a == "lex":
            scoring_engine.rank_candidates = orig_rank
            import ranking as _rk; _rk.rank_candidates = orig_rank
write("fallback_ratio", f_rows)
summary["fallback_ratio"] = f_rows
json.dump(summary, open(OUT / "summary.json", "w"), indent=1, default=float)
print("saved", OUT)
