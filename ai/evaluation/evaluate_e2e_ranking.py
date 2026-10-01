"""End-to-end ranking evaluation: the 60 natural-language requests -> each system's extracted preferences
-> the SAME PawConnect ranker over the REAL shelter catalogue. Relevance comes from the GOLD annotations and is independent of the ranker's weights:
0 = unavailable or wrong species; 1 = right species but fails another gold required constraint;
2..5 = 2 + round(3 x share of gold preferences satisfied), counting each preference (and each
temperament trait) once, unweighted, with the same attribute-matching definitions the system uses.

usage (from ai/): python evaluation/evaluate_e2e_ranking.py CATALOGUE(.json|.csv) OUT.json
"""
import copy, csv, json, math, random, sys
from pathlib import Path
import numpy as np
AI = Path(__file__).resolve().parents[1]; EV = AI / "evaluation"
sys.path[:0] = [str(AI), str(EV)]
from ranking import rank_animals
from preference_standardizer import standardize_preferences
from filter_engine import evaluate_required_constraints
from scoring_engine import calculate_preferred_score
from scoring_engine import score_energy, score_temperament, score_boolean, score_experience, score_attention

def relevance(animal, prefs):
    req, pref = prefs["required"], prefs["preferred"]
    if str(animal.get("adoption_status", "available")).strip().lower() != "available": return 0
    if req.get("pet_type") and str(animal.get("type", "")).strip().lower() != req["pet_type"]: return 0
    if not evaluate_required_constraints(animal, req)["is_match"]: return 1
    matched = total = 0
    if pref.get("energy_level"):
        sc, w, _ = score_energy(pref, animal, {}); total += 1; matched += sc >= w > 0
    traits = pref.get("temperament") or []
    traits = [traits] if isinstance(traits, str) else traits
    temp = str(animal.get("temperament", "")).lower()
    for t in traits: total += 1; matched += str(t).lower() in temp
    for f in ("apartment_friendly", "child_friendly", "pet_friendly"):
        if f in pref:
            sc, w = score_boolean(f, pref, animal, 10.0, {}); total += 1; matched += sc >= w > 0
    if pref.get("experience_level"):
        sc, w = score_experience(pref, animal, {}); total += 1; matched += sc >= w > 0
    if pref.get("available_attention_hours") is not None:
        sc, w = score_attention(pref, animal, {}); total += 1; matched += sc >= w > 0
    return 2 + round(3 * matched / total) if total else 2

cat_path, out_path = Path(sys.argv[1]), Path(sys.argv[2])
if cat_path.suffix == ".csv":
    rows = list(csv.DictReader(open(cat_path, encoding="utf-8-sig")))
else:
    rows = json.load(open(cat_path))
def clean(a):
    a = {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in a.items()}
    for k in ("apartment_friendly", "child_friendly", "pet_friendly"):
        v = a.get(k)
        if isinstance(v, str): a[k] = {"1": True, "true": True, "yes": True, "0": False, "false": False, "no": False}.get(v.lower(), None)
    v = a.get("daily_attention_hours")
    if isinstance(v, str): a["daily_attention_hours"] = float(v) if v.replace(".", "", 1).isdigit() else None
    try: a["id"] = int(a["id"])
    except Exception: pass
    return a
ALL = [clean(a) for a in rows]
# Same pool the web route sends: available animals, newest 100
POOL = sorted([a for a in ALL if str(a.get("adoption_status", "")).lower() == "available"], key=lambda a: a["id"], reverse=True)[:100]

bench = [json.loads(l) for l in open(EV / "natural_language_challenge_60.jsonl")]
ml = {d["case_id"]: d["predicted"] for d in next(c for c in json.load(open(EV / "results/ablation_component_results.json")) if c["configuration"] == "ML-only")["details"]}
hy = {r["case_id"]: r["hybrid_preferences"] for r in json.load(open(EV / "results/hybrid_results.json"))}
ll = {r["case_id"]: r.get("structured_llm_output") or {} for r in json.load(open(EV / "results/llm_results_llama.json"))}

def std(flat, name, text):
    return standardize_preferences({k: v for k, v in flat.items() if v is not None}, model_name=name, original_prompt=text)

K = 5; LIM = 20
def dcg(g): return sum((2 ** x - 1) / math.log2(i + 2) for i, x in enumerate(g))

def aggregate_rank(prefs, pool):  # single compensatory score, no filter
    req = prefs["required"]; s = []
    for a in pool:
        ev = evaluate_required_constraints(a, req); ps = calculate_preferred_score(a, prefs["preferred"], {})
        e = 20 * len(ev["matched_constraints"]) + ps.get("earned_weight", 0); p = 20 * len(req) + ps.get("possible_weight", 0)
        s.append((e / p if p else 0, -a["id"], a))
    return [t[2]["id"] for t in sorted(s, key=lambda t: (t[0], t[1]), reverse=True)]

def filter_random(prefs, pool, seed):
    ex = [a["id"] for a in pool if evaluate_required_constraints(a, prefs["required"])["is_match"]]
    random.Random(seed).shuffle(ex); return ex

def bm25_rank(text, pool, k1=1.5, b=0.75):
    import re
    tok = lambda s: re.findall(r"[a-z]+", s.lower())
    docs = {a["id"]: tok(" ".join(str(a.get(f, "")) for f in ("type", "breed", "size", "gender", "temperament", "location", "energy_level", "experience_required")) + " "
                         + " ".join(f for f in ("apartment", "child", "kids", "pet") if a.get({"apartment": "apartment_friendly", "child": "child_friendly", "kids": "child_friendly", "pet": "pet_friendly"}[f])))
            for a in pool}
    N = len(docs); avg = sum(map(len, docs.values())) / N
    df = {}
    for d in docs.values():
        for w in set(d): df[w] = df.get(w, 0) + 1
    q = tok(text); sc = []
    for i, d in docs.items():
        s = 0
        for w in q:
            if w in df:
                f = d.count(w); s += math.log(1 + (N - df[w] + .5) / (df[w] + .5)) * f * (k1 + 1) / (f + k1 * (1 - b + b * len(d) / avg))
        sc.append((s, -i, i))
    return [t[2] for t in sorted(sc, reverse=True)]

def metrics(ids, grade, gold, pool_by_id):
    g = [grade[i] for i in ids]; best = max(grade.values())
    ideal = dcg(sorted(grade.values(), reverse=True)[:K])
    hits = [x == best for x in g]; nrel = sum(x == best for x in grade.values())
    ap, h = 0.0, 0
    for i, x in enumerate(hits[:10]):
        if x: h += 1; ap += h / (i + 1)
    rr = next((1 / (i + 1) for i, x in enumerate(hits) if x), 0.0)
    top = [pool_by_id[i] for i in ids[:K]]
    species_v = sum(bool(gold["required"].get("pet_type")) and str(a.get("type", "")).lower() != gold["required"]["pet_type"] for a in top)
    req_v = sum(not evaluate_required_constraints(a, gold["required"])["is_match"] for a in top)
    return {"ndcg@5": dcg(g[:K]) / ideal if ideal else 0.0, "map@10": ap / min(nrel, 10) if nrel else 0.0, "hr@1": float(bool(hits[:1] and hits[0])),
            "hr@5": float(any(hits[:K])), "mrr": rr, "species_viol@5": species_v / max(len(top), 1), "required_viol@5": req_v / max(len(top), 1),
            "empty": float(len(ids) == 0), "n_returned": len(ids[:K])}

pool_by_id = {a["id"]: a for a in POOL}
per = {}; skipped = []
for case in bench:
    cid, text = case["id"], case["text"]
    gold = std({k: v for k, v in case["expected"].items()}, "gold", text)
    grade = {a["id"]: relevance(a, gold) for a in POOL}
    if max(grade.values()) == 0: skipped.append(cid); continue
    sysprefs = {"Oracle (gold extraction)": gold, "Hybrid": hy[cid], "ML-only": std(ml[cid], "ml", text), "Llama 3.3 70B": std(ll[cid], "llm", text)}
    res = {}
    for name, p in sysprefs.items():
        r = rank_animals(copy.deepcopy(POOL), copy.deepcopy(p), LIM)
        res[name] = metrics([x["id"] for x in r["recommendations"]], grade, gold, pool_by_id)
        res[name]["mode"] = r["mode"]
    res["Aggregate score, no filter (Hybrid extraction)"] = metrics(aggregate_rank(hy[cid], POOL)[:LIM], grade, gold, pool_by_id)
    fr = [metrics(filter_random(hy[cid], POOL, s)[:LIM], grade, gold, pool_by_id) for s in range(20)]
    res["Filter + random order (Hybrid extraction)"] = {m: float(np.mean([f[m] for f in fr])) for m in fr[0]}
    res["BM25 keyword match"] = metrics(bm25_rank(text, POOL)[:LIM], grade, gold, pool_by_id)
    res["No ranking (newest first)"] = metrics([a["id"] for a in POOL][:LIM], grade, gold, pool_by_id)
    per[cid] = res

systems = list(next(iter(per.values())).keys())
M = ["ndcg@5", "map@10", "hr@1", "hr@5", "mrr", "species_viol@5", "required_viol@5", "empty"]
rng = np.random.default_rng(2026)
def boot(v):
    v = np.array(v); b = [v[rng.integers(0, len(v), len(v))].mean() for _ in range(5000)]
    return [float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))]
def perm(a, b, R=10000):
    d = np.array(a) - np.array(b); obs = abs(d.mean())
    s = rng.choice([-1, 1], size=(R, len(d))); return float(((np.abs((s * d).mean(1)) >= obs - 1e-12).sum() + 1) / (R + 1))
summary = {s: {m: float(np.mean([per[c][s][m] for c in per])) for m in M} for s in systems}
for s in systems: summary[s]["ndcg@5_CI95"] = boot([per[c][s]["ndcg@5"] for c in per])
tests = {}
for other in systems:
    if other == "Hybrid": continue
    tests[f"Hybrid vs {other}"] = {"delta_ndcg@5": summary["Hybrid"]["ndcg@5"] - summary[other]["ndcg@5"], "p_perm": perm([per[c]["Hybrid"]["ndcg@5"] for c in per], [per[c][other]["ndcg@5"] for c in per])}
ps = sorted((v["p_perm"], k) for k, v in tests.items()); m = len(ps)
for i, (p, k) in enumerate(ps): tests[k]["p_holm"] = min(1.0, max(p * (m - j) for j, (p2, _) in enumerate(ps[:i + 1])))
modes = {s: {md: sum(per[c][s].get("mode") == md for c in per) for md in ("exact", "alternative", "no_match")} for s in systems[:4]}
out = {"catalogue_total": len(ALL), "pool_available_used": len(POOL), "pool_species": {t: sum(str(a.get("type")).lower() == t for a in POOL) for t in ("dog", "cat")},
       "queries_scored": len(per), "queries_skipped_no_relevant": skipped, "k": K, "summary": summary, "paired_randomization_tests_ndcg@5": tests, "modes": modes, "per_query": per}
json.dump(out, open(out_path, "w"), indent=1)
print(json.dumps({k: v for k, v in out.items() if k != "per_query"}, indent=1))
