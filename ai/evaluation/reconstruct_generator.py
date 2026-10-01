"""Teacher item 2 (script + seed): RECONSTRUCTED generator for the synthetic v4 training data.

The original generation script and seed were lost. This script recovers the generation grammar from the 10,000
released samples and re-implements it, so the corpus can be regenerated (statistically, not byte-identically).

  python evaluation/reconstruct_generator.py extract      -> results/data_audit/recovered_generation_spec.json
  python evaluation/reconstruct_generator.py generate --seed 20260930 --n 10000 --out data/reconstructed_v4
  python evaluation/reconstruct_generator.py validate     -> results/data_audit/reconstruction_validation.json

Recovered grammar (holds for 10,000/10,000 original samples):
  * every label is carried by exactly one family of paraphrase templates, and a request's label set equals the union of
    the labels carried by its sentences (0 exceptions);
  * label sentences appear in a fixed attribute order:
    pet type > home > yard > temperament (1-4) > activity > experience > time > children > other pets > grooming > shedding > noise;
  * entity sentences (age, size, breed, location, gender) are inserted at random positions after the first sentence;
  * a discourse prefix ("Ideally," "Also," "Most importantly," "For everyday life," "Another important point is that")
    is added to about 16% of non-initial sentences, lower-casing the following word.
"""
import argparse, collections, json, random, re, statistics, sys
from pathlib import Path
EV = Path(__file__).resolve().parent; AI = EV.parent; DATA = AI / "data"; OUT = EV / "results" / "data_audit"
sys.path.insert(0, str(AI)); import entity_extractor as ee
OUT.mkdir(parents=True, exist_ok=True); SPEC = OUT / "recovered_generation_spec.json"
ORDER = ["pet", "home", "yard", "temper", "activity", "exp", "time", "children", "pets", "groom", "shed", "noise"]
GROUP = {"prefers_cat": "pet", "prefers_dog": "pet", "apartment_friendly": "home", "house_friendly": "home", "yard_available": "yard",
         "independent": "temper", "friendly": "temper", "calm": "temper", "affectionate": "temper", "playful": "temper", "protective": "temper",
         "low_energy": "activity", "moderate_activity": "activity", "active": "activity", "beginner_owner": "exp", "experienced_owner": "exp",
         "plenty_time": "time", "limited_time": "time", "good_with_children": "children", "good_with_pets": "pets", "low_grooming": "groom",
         "low_shedding": "shed", "quiet": "noise", "vocal": "noise"}
PREFIXES = ["Ideally,", "Also,", "Most importantly,", "For everyday life,", "Another important point is that"]
PREF_RE = re.compile(r"^(ideally,|also,|most importantly,|for everyday life,|another important point is that)\s+", re.I)
ENT_RE = {"age_years": re.compile(r"^I would prefer a pet that is (\d+) years old\.$"), "size": re.compile(r"^I would prefer a (small|medium|large)-sized pet\.$"),
          "breed": re.compile(r"^My preferred breed is (.+)\.$"), "location": re.compile(r"^I am looking for a pet located in (.+)\.$"),
          "gender": re.compile(r"^I would prefer a (male|female) pet\.$")}
def load(p): return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
def split_sents(t): return [x.strip() for x in re.split(r"(?<=[.!?])\s+", t.strip()) if x.strip()]
def strip_prefix(s):
    m = PREF_RE.match(s)
    if not m: return None, s
    rest = s[m.end():]; return m.group(1), rest[:1].upper() + rest[1:]

def extract():
    rows = [r for s in ("train", "validation", "test") for r in load(DATA / f"pawconnect_v4_{s}.jsonl")]
    core_req, core_lab = collections.Counter(), collections.defaultdict(collections.Counter)
    parsed = []
    for r in rows:
        items = []
        for i, s in enumerate(split_sents(r["text"])):
            p, c = strip_prefix(s); ent = next(((k, m.group(1)) for k, rx in ENT_RE.items() if (m := rx.match(c))), None)
            items.append((i, p, c, ent))
        parsed.append((r, items))
        for c in {c for _, _, c, e in items if e is None}: core_req[c] += 1; core_lab[c].update(r["labels"])
    carried = {c: sorted(l for l, n in core_lab[c].items() if n == core_req[c]) for c in core_req}
    # label -> paraphrase templates (a template carrying 2 labels is keyed by its primary group value)
    def key(c):
        L = carried[c]
        if "yard_available" in L: return "yard_available"
        if "limited_time" in L: return "limited_time"
        return L[0]
    templates = collections.defaultdict(collections.Counter)
    for c in core_req: templates[key(c)][c] = core_req[c]
    S = {sp: collections.Counter() for sp in ("dog", "cat")}; groups = {sp: collections.defaultdict(collections.Counter) for sp in ("dog", "cat")}
    temper_n = {f"{sp}|{t}": collections.Counter() for sp in ("dog", "cat") for t in ("limited", "not_limited")}
    temper_tr = {k: collections.Counter() for k in temper_n}; yard = {f"{sp}|{h}": collections.Counter() for sp in ("dog", "cat") for h in ("apartment_friendly", "house_friendly", "none")}
    ent_p = {sp: collections.Counter() for sp in ("dog", "cat")}; ent_v = {sp: collections.defaultdict(collections.Counter) for sp in ("dog", "cat")}
    pref_n = collections.Counter(); later = 0; prefixed = 0; violations = 0
    for r, items in parsed:
        keys = [key(c) for _, _, c, e in items if e is None]; sp = "dog" if "prefers_dog" in keys else "cat"; S[sp]["n"] += 1
        seq = [GROUP[k] for k in keys]; violations += any(ORDER.index(a) > ORDER.index(b) for a, b in zip(seq, seq[1:]))
        home = next((k for k in keys if GROUP[k] == "home"), "none"); tl = "limited" if "limited_time" in keys else "not_limited"
        for g in ORDER[1:]:
            vals = [k for k in keys if GROUP[k] == g]
            if g == "temper":
                traits = [k for k in keys if GROUP[k] == "temper" and not (tl == "limited" and k == "independent")]
                temper_n[f"{sp}|{tl}"][len(traits)] += 1; temper_tr[f"{sp}|{tl}"]["+".join(sorted(traits))] += 1
            elif g == "yard": yard[f"{sp}|{home}"][vals[0] if vals else "none"] += 1
            else: groups[sp][g][vals[0] if vals else "none"] += 1
        for _, _, _, e in items:
            if e: ent_p[sp][e[0]] += 1; ent_v[sp][e[0]][e[1]] += 1
        for i, p, _, e in items:
            if i > 0 and e is None: later += 1; prefixed += p is not None; pref_n[(p or "").lower()] += p is not None
    spec = {"species_prob": {sp: S[sp]["n"] / len(rows) for sp in S}, "group_order": ORDER, "prefix_rate_non_initial": prefixed / later,
            "prefix_weights": {p: pref_n[p.lower()] for p in PREFIXES}, "templates": {k: dict(v) for k, v in templates.items()},
            "carried_labels": carried, "groups": {sp: {g: dict(c) for g, c in groups[sp].items()} for sp in groups},
            "temperament_count(species|time)": {k: dict(v) for k, v in temper_n.items()}, "temperament_trait_sets(species|time)": {k: dict(v) for k, v in temper_tr.items()},
            "yard(species|home)": {k: dict(v) for k, v in yard.items() if v},
            "dependencies": ["yard sentence only when home=house", "limited_time always co-occurs with an 'independent' temperament sentence",
                             "entity and pet-type sentences are never prefixed", "pet-type sentence is always first"],
            "entity_presence": {sp: {e: ent_p[sp][e] / S[sp]["n"] for e in ENT_RE} for sp in ent_p},
            "entity_values": {sp: {e: dict(ent_v[sp][e]) for e in ENT_RE} for sp in ent_v},
            "entity_templates": {"age_years": "I would prefer a pet that is {} years old.", "size": "I would prefer a {}-sized pet.", "breed": "My preferred breed is {}.",
                                 "location": "I am looking for a pet located in {}.", "gender": "I would prefer a {} pet."},
            "checks": {"samples": len(rows), "label_set_equals_union_of_template_labels": sum(set(r["labels"]) == set().union(*[carried[c] for _, _, c, e in it if e is None]) for r, it in parsed),
                       "group_order_violations": violations, "distinct_core_templates": len(core_req), "entity_templates": len(ENT_RE)}}
    json.dump(spec, open(SPEC, "w"), indent=1)
    import csv
    with open(OUT / "template_inventory_core.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["group", "label_key", "template", "labels_carried", "requests_using_it"])
        for k in sorted(templates, key=lambda k: (ORDER.index(GROUP[k]), k)):
            for c, n in sorted(templates[k].items(), key=lambda kv: -kv[1]): w.writerow([GROUP[k], k, c, " ".join(carried[c]), n])
        for e, t in spec["entity_templates"].items(): w.writerow(["entity", e, t.replace("{}", "<" + e.upper() + ">"), "(entity field, no label)", sum(ent_p[sp][e] for sp in ent_p)])
        for p_ in PREFIXES: w.writerow(["discourse_prefix", "-", p_ + " <sentence>", "(none)", pref_n[p_.lower()]])
    print(json.dumps(spec["checks"], indent=1)); return spec

def wchoice(rng, d): k = list(d); return rng.choices(k, weights=[d[x] for x in k])[0]
def generate(seed, n, out):
    spec = json.load(open(SPEC)); rng = random.Random(seed); rows = []
    for i in range(n):
        sp = rng.choices(["dog", "cat"], weights=[spec["species_prob"]["dog"], spec["species_prob"]["cat"]])[0]
        chosen = {g: wchoice(rng, spec["groups"][sp][g]) for g in ORDER[1:] if g not in ("temper", "yard")}
        chosen["yard"] = wchoice(rng, spec["yard(species|home)"][f"{sp}|{chosen['home']}"])
        tl = "limited" if chosen["time"] == "limited_time" else "not_limited"
        ts = wchoice(rng, spec["temperament_trait_sets(species|time)"][f"{sp}|{tl}"]); traits = [t for t in ts.split("+") if t]
        if tl == "limited": traits.append("independent")
        rng.shuffle(traits)
        keys = ["prefers_" + sp]
        for g in ORDER[1:]:
            if g == "temper": keys += traits
            elif chosen[g] != "none": keys.append(chosen[g])
        sents = [wchoice(rng, spec["templates"][k]) for k in keys]
        is_label = [True] * len(sents)
        ents = {e: None for e in ENT_RE}
        for e in ENT_RE:
            if rng.random() < spec["entity_presence"][sp][e]:
                v = wchoice(rng, spec["entity_values"][sp][e]); ents[e] = int(v) if e == "age_years" else v
                pos = rng.randint(1, len(sents)); sents.insert(pos, spec["entity_templates"][e].format(v)); is_label.insert(pos, False)
        for j in range(1, len(sents)):
            if is_label[j] and rng.random() < spec["prefix_rate_non_initial"]:
                p = wchoice(rng, spec["prefix_weights"]); s = sents[j]; sents[j] = f"{p} {s[:1].lower()}{s[1:]}"
        labels = sorted(set().union(*[spec["carried_labels"][s] for s in (strip_prefix(x)[1] for x in sents) if s in spec["carried_labels"]]))
        rows.append({"sample_id": f"RGV4-{i+1:05d}", "text": " ".join(sents), "labels": labels, "entities": ents, "source_type": "reconstructed_synthetic", "seed": seed})
    out = Path(out); out.mkdir(parents=True, exist_ok=True); rng.shuffle(rows)
    cut = {"train": rows[:int(.8 * n)], "validation": rows[int(.8 * n):int(.9 * n)], "test": rows[int(.9 * n):]}
    for k, v in cut.items():
        with open(out / f"reconstructed_v4_{k}.jsonl", "w", encoding="utf-8") as f:
            for r in v: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("wrote", {k: len(v) for k, v in cut.items()}, "to", out)

def validate(seed=20260930):
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.multiclass import OneVsRestClassifier
    from sklearn.preprocessing import MultiLabelBinarizer
    from sklearn.metrics import f1_score
    tmp = EV / "results" / "data_audit" / "reconstructed_sample"; generate(seed, 10000, tmp)
    orig = {s: load(DATA / f"pawconnect_v4_{s}.jsonl") for s in ("train", "validation", "test")}
    rec = {s: load(tmp / f"reconstructed_v4_{s}.jsonl") for s in ("train", "validation", "test")}
    O = [r for v in orig.values() for r in v]; R = [r for v in rec.values() for r in v]
    labs = sorted({l for r in O for l in r["labels"]})
    prev = {l: (sum(l in r["labels"] for r in O) / len(O), sum(l in r["labels"] for r in R) / len(R)) for l in labs}
    wc = lambda D: statistics.mean(len(r["text"].split()) for r in D); sc = lambda D: statistics.mean(len(split_sents(r["text"])) for r in D)
    osent = {s.lower() for r in O for s in split_sents(r["text"])}; rsent = {s.lower() for r in R for s in split_sents(r["text"])}
    def fit_eval(train, test):
        mlb = MultiLabelBinarizer(classes=labs); vec = TfidfVectorizer(lowercase=True, strip_accents="unicode", ngram_range=(1, 2), min_df=2, max_df=0.98, sublinear_tf=True, max_features=50000)
        m = OneVsRestClassifier(LogisticRegression(solver="liblinear", max_iter=2000, class_weight="balanced", random_state=20260729))
        m.fit(vec.fit_transform([r["text"] for r in train]), mlb.fit_transform([r["labels"] for r in train]))
        return float(f1_score(mlb.transform([r["labels"] for r in test]), (m.predict_proba(vec.transform([r["text"] for r in test])) >= 0.45).astype(int), average="micro"))
    res = {"seed": seed, "label_prevalence_original_vs_reconstructed": {l: [round(a, 4), round(b, 4)] for l, (a, b) in prev.items()},
           "max_abs_prevalence_difference": round(max(abs(a - b) for a, b in prev.values()), 4),
           "labels_per_request": [round(statistics.mean(len(r["labels"]) for r in O), 2), round(statistics.mean(len(r["labels"]) for r in R), 2)],
           "words_per_request": [round(wc(O), 2), round(wc(R), 2)], "sentences_per_request": [round(sc(O), 2), round(sc(R), 2)],
           "distinct_sentences": [len(osent), len(rsent)], "reconstructed_sentences_found_in_original_bank": round(len(rsent & osent) / len(rsent), 4),
           "original_sentences_reproduced": round(len(osent & rsent) / len(osent), 4),
           "micro_f1_train_original_test_original": round(fit_eval(orig["train"], orig["test"]), 4),
           "micro_f1_train_reconstructed_test_original": round(fit_eval(rec["train"], orig["test"]), 4)}
    json.dump(res, open(OUT / "reconstruction_validation.json", "w"), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != "label_prevalence_original_vs_reconstructed"}, indent=1))

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["extract", "generate", "validate"]); ap.add_argument("--seed", type=int, default=20260930)
    ap.add_argument("--n", type=int, default=10000); ap.add_argument("--out", default=str(DATA / "reconstructed_v4")); a = ap.parse_args()
    if a.cmd == "extract": extract()
    elif a.cmd == "generate": generate(a.seed, a.n, a.out)
    else: validate(a.seed)
