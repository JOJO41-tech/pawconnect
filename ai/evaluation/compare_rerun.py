"""Compare a fresh rerun of Tasks 1, 2 and 5 with the previous outputs.

Usage (from ai/):  python evaluation/compare_rerun.py <backup_dir>
<backup_dir> holds the previous results (data_audit/, adversarial_tables/, latency/, *.json) moved aside before the rerun.
Tasks 2 and 5 are deterministic, so every file should be IDENTICAL (JSON files are compared after sorting keys).
Task 1 is a timing measurement, so it prints old vs new mean/median instead.
"""
import csv, json, sys
from pathlib import Path

EV = Path(__file__).resolve().parent; RES = EV / "results"
old = Path(sys.argv[1]).resolve()

def same(a: Path, b: Path) -> bool:
    if a.suffix == ".json":
        try: return json.loads(a.read_text(encoding="utf-8")) == json.loads(b.read_text(encoding="utf-8"))
        except Exception: pass
    return a.read_bytes().replace(b"\r\n", b"\n") == b.read_bytes().replace(b"\r\n", b"\n")

n_ok = n_bad = 0
for task, rel in [("Task 2", "data_audit"), ("Task 5", "adversarial_tables"), ("Task 5", "adversarial_results.json"),
                  ("Task 5", "adversarial_constraints_summary.json"), ("Task 5", "language_trap_results.json")]:
    src = old / rel
    if not src.exists(): continue
    files = sorted(p for p in src.rglob("*") if p.is_file()) if src.is_dir() else [src]
    for f in files:
        r = f.relative_to(old); new = RES / r
        if not new.exists(): print(f"{task}  NOT REGENERATED  {r}  (old file, no current script writes it)"); continue
        ok = same(f, new); n_ok += ok; n_bad += (not ok)
        print(f"{task}  {'IDENTICAL' if ok else 'DIFFERENT'}  {r}")
print(f"\nTasks 2 and 5: {n_ok} identical, {n_bad} different")

lo, ln = old / "latency" / "latency_summary.csv", RES / "latency" / "latency_summary.csv"
if lo.exists() and ln.exists():
    rd = lambda p: {r["system"]: r for r in csv.DictReader(open(p, encoding="utf-8"))}
    o, n = rd(lo), rd(ln)
    print("\nTask 1 latency (ms)          previous run            this rerun")
    for s in ["ML-only", "Hybrid", "Llama 3.3 70B"]:
        if s in o or s in n:
            f = lambda d: f"mean {float(d['mean_ms']):9.3f}  median {float(d['median_ms']):9.3f}  n={d['timed_runs']}" if d else "-"
            print(f"{s:14s}  {f(o.get(s))}   |   {f(n.get(s))}")
