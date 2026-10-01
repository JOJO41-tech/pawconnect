"""Teacher item 2: audit of the synthetic training data (v4, 10,000 samples) and the evaluation benchmarks.

Outputs (results/data_audit/):
  provenance.json            files, SHA-256, sample-id prefixes, source/review status, generator/seed status
  template_inventory.csv     every distinct sentence template (slot values masked) with counts and the label(s) it expresses
  template_summary.json      template counts, paraphrases per label, sentences per request
  class_distribution.csv     label counts and prevalence per split
  entity_distribution.csv    entity values (breed/size/gender/location/age) per split
  duplicates_report.json     exact, order-insensitive, slot-only and near (TF-IDF cosine) duplicates
  split_overlap_report.json  sentence / template / label-set / near-duplicate overlap between splits and with the 60-request benchmark
Run from ai/:  python evaluation/audit_synthetic_data.py
"""
import csv, hashlib, json, re, statistics
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
EV = Path(__file__).resolve().parent; AI = EV.parent; DATA = AI / "data"
OUT = EV / "results" / "data_audit"; OUT.mkdir(parents=True, exist_ok=True)
import sys; sys.path.insert(0, str(AI))
import entity_extractor as ee

def load(p): return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
SPLITS = {s: load(DATA / f"pawconnect_v4_{s}.jsonl") for s in ("train", "validation", "test")}
BENCH = load(EV / "natural_language_challenge_60.jsonl")
ALL = [r for s in SPLITS.values() for r in s]

# ---------------- provenance ----------------
gen_candidates = [p.name for p in AI.rglob("*.py") if re.search(r"generat|synth|template", p.name, re.I) and "evaluation" not in p.parts]
prov = {
    "dataset_version": "v4", "total_samples": len(ALL), "splits": {k: len(v) for k, v in SPLITS.items()},
    "files": {p.name: {"bytes": p.stat().st_size, "sha256": sha(p), "lines": sum(1 for l in open(p, encoding="utf-8") if l.strip())}
              for p in sorted(DATA.glob("pawconnect_v4_*.jsonl"))},
    "sample_id_prefixes": dict(Counter(r["sample_id"][:6] for r in ALL)),
    "part_split_design": {pre: dict(Counter(s for s, rows in SPLITS.items() for r in rows if r["sample_id"].startswith(pre))) for pre in ("PCV4P1", "PCV4P2")},
    "source_type": dict(Counter(r.get("source_type") for r in ALL)), "review_status": dict(Counter(r.get("review_status") for r in ALL)),
    "generator_script_in_repository": bool(gen_candidates), "generator_candidates": gen_candidates,
    "generation_seed_recorded": False,
    "model_training_seed": 20260729, "model_training_script": "train_pawconnect_ai_v4.py",
    "note": "The v4 corpus is the union of two 5,000-sample parts (PCV4P1, PCV4P2), each split 4,000/500/500. "
            "No generation script or generation seed is stored in the repository; see template_inventory.csv for the empirically recovered template bank.",
}
json.dump(prov, open(OUT / "provenance.json", "w"), indent=1)

# ---------------- templates ----------------
SLOT_PATTERNS = []
for b in sorted(ee.DOG_BREEDS + ee.CAT_BREEDS, key=len, reverse=True): SLOT_PATTERNS.append((re.compile(r"\b" + re.escape(b.lower()) + r"\b"), "<BREED>"))
for l in sorted(ee.LOCATIONS, key=len, reverse=True): SLOT_PATTERNS.append((re.compile(r"\b" + re.escape(l.lower()) + r"\b"), "<LOCATION>"))
NUMW = "|".join(sorted(map(re.escape, ee.NUMBER_WORDS), key=len, reverse=True))
SLOT_PATTERNS += [(re.compile(r"\b(\d+(\.\d+)?|" + NUMW + r")\b"), "<NUM>"), (re.compile(r"\b(male|female)\b"), "<GENDER>"),
                  (re.compile(r"\b(small|medium|large|medium-sized|small-sized|large-sized)\b"), "<SIZE>")]
def sentences(t): return [re.sub(r"\s+", " ", x.strip().lower()) for x in re.split(r"(?<=[.!?])\s+", t.strip()) if x.strip()]
def skeleton(s):
    for pat, rep in SLOT_PATTERNS: s = pat.sub(rep, s)
    return s

sent_by_split = {k: [sentences(r["text"]) for r in v] for k, v in SPLITS.items()}
skel_stats = defaultdict(lambda: {"occurrences": 0, "requests": 0, "raw_variants": set(), "by_split": Counter(), "label_hits": Counter()})
for k, rows in SPLITS.items():
    for r, ss in zip(rows, sent_by_split[k]):
        seen = set()
        for s in ss:
            sk = skeleton(s); st = skel_stats[sk]; st["occurrences"] += 1; st["raw_variants"].add(s); st["by_split"][k] += 1
            if sk not in seen:
                seen.add(sk); st["requests"] += 1; st["label_hits"].update(r["labels"])
inv = []
for sk, st in sorted(skel_stats.items(), key=lambda kv: -kv[1]["occurrences"]):
    expressed = sorted(l for l, c in st["label_hits"].items() if c / st["requests"] >= 0.99)
    inv.append({"template": sk, "occurrences": st["occurrences"], "requests": st["requests"], "raw_variants": len(st["raw_variants"]),
                "train": st["by_split"]["train"], "validation": st["by_split"]["validation"], "test": st["by_split"]["test"],
                "slots": " ".join(sorted(set(re.findall(r"<[A-Z]+>", sk)))), "labels_always_present(>=99%)": " ".join(expressed)})
with open(OUT / "template_inventory.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(inv[0])); w.writeheader(); w.writerows(inv)
labels_all = sorted({l for r in ALL for l in r["labels"]})
per_label_templates = {l: sum(1 for t in inv if l in t["labels_always_present(>=99%)"].split()) for l in labels_all}
spr = [len(ss) for v in sent_by_split.values() for ss in v]
tsum = {"distinct_raw_sentences": len({s for v in sent_by_split.values() for ss in v for s in ss}),
        "distinct_templates_after_slot_masking": len(inv),
        "templates_with_slots": sum(1 for t in inv if t["slots"]), "templates_without_label_signal": sum(1 for t in inv if not t["labels_always_present(>=99%)"]),
        "total_sentences": sum(spr), "sentences_per_request": {"mean": round(statistics.mean(spr), 2), "median": statistics.median(spr), "min": min(spr), "max": max(spr)},
        "templates_per_label(paraphrase variants that always carry the label)": per_label_templates,
        "top10_templates_share_of_sentences": round(sum(t["occurrences"] for t in inv[:10]) / sum(spr), 4)}
json.dump(tsum, open(OUT / "template_summary.json", "w"), indent=1)

# ---------------- class distribution ----------------
with open(OUT / "class_distribution.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["label"] + [f"{s}_count" for s in SPLITS] + [f"{s}_prevalence" for s in SPLITS] + ["total_count", "total_prevalence"])
    for l in labels_all:
        c = {s: sum(l in r["labels"] for r in rows) for s, rows in SPLITS.items()}
        w.writerow([l] + [c[s] for s in SPLITS] + [f"{c[s]/len(SPLITS[s]):.4f}" for s in SPLITS] + [sum(c.values()), f"{sum(c.values())/len(ALL):.4f}"])
card = [len(r["labels"]) for r in ALL]
labelsets = Counter(tuple(sorted(r["labels"])) for r in ALL)
with open(OUT / "entity_distribution.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["entity", "value", "train", "validation", "test", "total"])
    for e in ("breed", "size", "gender", "location", "age_years"):
        vals = Counter(); per = {s: Counter(str((r.get("entities") or {}).get(e)) for r in rows) for s, rows in SPLITS.items()}
        for s in per: vals.update(per[s])
        for v, n in vals.most_common(): w.writerow([e, v, per["train"][v], per["validation"][v], per["test"][v], n])

# ---------------- duplicates ----------------
texts = {k: [r["text"].strip() for r in v] for k, v in SPLITS.items()}
def dup_count(keys): c = Counter(keys); return sum(n - 1 for n in c.values() if n > 1)
all_txt = [t for v in texts.values() for t in v]
multiset = lambda ss: tuple(sorted(ss))
all_ms = [multiset(ss) for v in sent_by_split.values() for ss in v]
all_sk = [tuple(sorted(skeleton(s) for s in ss)) for v in sent_by_split.values() for ss in v]
vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True).fit(texts["train"])
Xtr = vec.transform(texts["train"])
def nn_sim(X):
    sims = []
    for i in range(0, X.shape[0], 500):
        S = (X[i:i + 500] @ Xtr.T).toarray(); sims.extend(S.max(1))
    return np.array(sims)
def within_train_nn():
    sims = []
    for i in range(0, Xtr.shape[0], 500):
        S = (Xtr[i:i + 500] @ Xtr.T).toarray()
        for j in range(S.shape[0]): S[j, i + j] = -1
        sims.extend(S.max(1))
    return np.array(sims)
nn = {"train (to other train)": within_train_nn(), "validation": nn_sim(vec.transform(texts["validation"])), "test": nn_sim(vec.transform(texts["test"])),
      "60-request benchmark": nn_sim(vec.transform([b["text"] for b in BENCH]))}
def dist(a): return {"mean": round(float(a.mean()), 4), "median": round(float(np.median(a)), 4), "min": round(float(a.min()), 4), "max": round(float(a.max()), 4),
                     ">=0.95": int((a >= .95).sum()), ">=0.90": int((a >= .90).sum()), ">=0.80": int((a >= .80).sum()), "n": int(len(a))}
dups = {"exact_duplicate_texts": dup_count(all_txt), "order_insensitive_duplicates(same sentences, any order)": dup_count(all_ms),
        "slot_only_duplicates(same templates, different slot values)": dup_count(all_sk),
        "identical_label_sets": {"distinct_label_sets": len(labelsets), "samples_sharing_a_label_set_with_another": sum(n for n in labelsets.values() if n > 1),
                                 "largest_label_set_group": labelsets.most_common(1)[0][1]},
        "labels_per_request": {"mean": round(statistics.mean(card), 2), "min": min(card), "max": max(card)},
        "nearest_train_neighbour_tfidf_cosine": {k: dist(v) for k, v in nn.items()}}
json.dump(dups, open(OUT / "duplicates_report.json", "w"), indent=1)

# ---------------- split overlap ----------------
train_sent = {s for ss in sent_by_split["train"] for s in ss}; train_sk = {skeleton(s) for s in train_sent}
train_sets = {tuple(sorted(r["labels"])) for r in SPLITS["train"]}; train_ms = {multiset(ss) for ss in sent_by_split["train"]}
train_skm = {tuple(sorted(skeleton(s) for s in ss)) for ss in sent_by_split["train"]}
def overlap(name, sent_lists, label_sets=None):
    sents = [s for ss in sent_lists for s in ss]
    o = {"requests": len(sent_lists), "sentence_level_overlap_with_train": round(sum(s in train_sent for s in sents) / len(sents), 4),
         "template_level_overlap_with_train": round(sum(skeleton(s) in train_sk for s in sents) / len(sents), 4),
         "requests_whose_every_sentence_occurs_in_train": sum(all(s in train_sent for s in ss) for ss in sent_lists),
         "requests_identical_to_a_train_request_up_to_sentence_order": sum(multiset(ss) in train_ms for ss in sent_lists),
         "requests_identical_to_a_train_request_up_to_slot_values": sum(tuple(sorted(skeleton(s) for s in ss)) in train_skm for ss in sent_lists)}
    if label_sets is not None: o["requests_whose_exact_label_set_occurs_in_train"] = sum(ls in train_sets for ls in label_sets)
    o["nearest_train_neighbour_tfidf_cosine"] = dist(nn[name]); return o
ov = {"validation_vs_train": overlap("validation", sent_by_split["validation"], [tuple(sorted(r["labels"])) for r in SPLITS["validation"]]),
      "test_vs_train": overlap("test", sent_by_split["test"], [tuple(sorted(r["labels"])) for r in SPLITS["test"]]),
      "benchmark60_vs_train": overlap("60-request benchmark", [sentences(b["text"]) for b in BENCH]),
      "validation_vs_test_exact_text_overlap": len(set(texts["validation"]) & set(texts["test"])),
      "train_vs_test_exact_text_overlap": len(set(texts["train"]) & set(texts["test"])),
      "interpretation": "Val/test requests are new combinations of the same sentence bank as train (every sentence already seen), so random splits and "
                        "standard cross-validation measure recombination, not generalisation to new wording. The 60-request benchmark shares no sentences with train."}
json.dump(ov, open(OUT / "split_overlap_report.json", "w"), indent=1)
print(json.dumps({"provenance": {k: prov[k] for k in ("total_samples", "splits", "generator_script_in_repository", "generation_seed_recorded")},
                  "templates": {k: tsum[k] for k in ("distinct_raw_sentences", "distinct_templates_after_slot_masking", "sentences_per_request", "top10_templates_share_of_sentences")},
                  "duplicates": {k: dups[k] for k in list(dups)[:4]}, "overlap_test": ov["test_vs_train"], "overlap_bench": ov["benchmark60_vs_train"]}, indent=1))

# ---------------- recovered generation grammar (generator script is lost) ----------------
CONNECTIVES = Counter(); base_of = {}
tset = {t["template"] for t in inv}
for t in tset:  # a template is a connective variant if it is <prefix> + another template
    rests = [r for r in tset if r != t and t.endswith(" " + r)]
    if rests:
        r = max(rests, key=len); CONNECTIVES[t[: -len(r)].strip()] += 1; base_of[t] = r
bases = sorted(tset - set(base_of))
lab_of = {t["template"]: t["labels_always_present(>=99%)"] for t in inv}
def group(lbls, sk):
    if "<" in sk: return "entity:" + re.findall(r"<([A-Z]+)>", sk)[0].lower()
    return lbls or "unlabelled"
base_groups = defaultdict(list)
for b in bases: base_groups[group(lab_of[b], b)].append(b)
# order of attribute groups inside requests
seq_groups = []
for ss in sent_by_split["train"]:
    g = []
    for s in ss:
        sk = skeleton(s); b = base_of.get(sk, sk); g.append(group(lab_of.get(b, ""), b))
    seq_groups.append(g)
pos = defaultdict(list)
for g in seq_groups:
    for i, x in enumerate(g): pos[x].append(i / max(len(g) - 1, 1))
order = sorted(pos, key=lambda x: statistics.mean(pos[x]))
rank = {x: i for i, x in enumerate(order)}
viol = sum(1 for g in seq_groups for i in range(len(g)) for j in range(i + 1, len(g)) if rank[g[i]] > rank[g[j]])
pairs = sum(len(g) * (len(g) - 1) // 2 for g in seq_groups)
conn_rate = sum(1 for ss in sent_by_split["train"] for s in ss if skeleton(s) in base_of) / sum(len(ss) for ss in sent_by_split["train"])
grammar = {"note": "Recovered from the data because the original generator script and seed are lost.",
           "base_sentence_templates": len(bases), "connective_prefixes": dict(CONNECTIVES),
           "share_of_sentences_with_a_connective_prefix": round(conn_rate, 4),
           "templates_total = base + base x connective variants observed": len(tset),
           "paraphrases_per_attribute_group": {k: len(v) for k, v in sorted(base_groups.items())},
           "attribute_group_order(mean relative position)": [{"group": x, "mean_position": round(statistics.mean(pos[x]), 3)} for x in order],
           "pairwise_order_violations_vs_single_fixed_order": f"{viol}/{pairs} ({100*viol/pairs:.2f}%)",
           "base_templates_by_group": {k: v for k, v in sorted(base_groups.items())}}
json.dump(grammar, open(OUT / "recovered_generation_grammar.json", "w"), indent=1)
print(json.dumps({k: grammar[k] for k in list(grammar)[:7]}, indent=1))
