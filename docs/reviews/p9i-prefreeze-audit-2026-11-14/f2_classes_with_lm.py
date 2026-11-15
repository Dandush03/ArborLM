"""F2 (auditor, Opus 5.5): a5's 20,000-table class check extended with language-modelling rises, including
non-finite ones. Imports a5_classes_enumeration.py by path (it re-runs its own 20,000 tables first, without
rises) and re-uses its reference ``aud`` and its table generator, then draws 20,000 new tables (seed 900002)
each with a rise for every (BB, size, B101 seed) drawn from finite values around 0.05 and +inf, -inf, nan,
sometimes missing.

Checks against my reference: (i) classes, dense comparisons, contrasts and selection equal a5's ``aud`` and
equal the implementer's result with no rises (rises never change a class or the selection); (ii) the BB
language-modelling label: DEGRADED iff some present rise is non-finite or > 0.05 (lead's ruling on X2),
absent iff no rise is present. Prints sha256 digests of the implementer's full outputs for the tables whose
rises are all finite and for the others, so the same script run against the dd8b205 tree
(PYTHONPATH=<clone>) shows finite equality across code versions.

Usage: PYTHONPATH=<tree> uv run --locked python <this>
"""
import hashlib
import importlib.util
import json
import math
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("a5", HERE / "a5_classes_enumeration.py")
assert spec and spec.loader
a5 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a5)
print("\n######## f2 (above: a5 re-executed on import)\n")
C = a5.C
print("classes module:", C.__file__)

RISES = [-0.5, 0.0, 0.01, 0.0499999, 0.05, math.nextafter(0.05, 1.0), 0.0500001, 0.08, 1.0, math.inf, -math.inf, math.nan]


def theirs_full(tab, lm):
    t = {k: C.Measure(acc, a5.CH[k[1]], dep) for k, (acc, dep) in tab.items()}
    return C.analyze_classes(t, lm, {})


def digest_of(res) -> str:
    return json.dumps(res, sort_keys=True, default=str, allow_nan=True)


rng = random.Random(900002)
N = 20000
fails: list[str] = []
h_fin, h_non = hashlib.sha256(), hashlib.sha256()
n_fin = n_non = n_deg = n_pres = n_absent = n_lm_tables_non = 0
for i in range(N):
    tab = a5.random_table(rng, "mixed" if i % 4 == 0 else "ok")
    lm = {}
    for s in a5.SIZES:
        for sd in a5.SEEDS:
            if rng.random() < 0.9:
                lm[("BB", s, sd)] = rng.choice(RISES)
    finite = all(math.isfinite(v) for v in lm.values())
    full = theirs_full(tab, lm)
    nolm = a5.theirs(tab, {})
    withlm = a5.theirs(tab, lm)
    ref = a5.aud(tab, lm)
    for k in ("classes", "dense", "contrast", "selection"):
        if withlm[k] != nolm[k] or withlm[k] != ref[k]:
            fails.append(f"table {i}: {k} differs")
    for s in a5.SIZES:
        note = full["annotations"].get("BB", {}).get(str(s))
        if note is None:
            continue  # BB not classified at this size (cells missing) -> no annotation at all
        rises = [lm[("BB", s, sd)] for sd in a5.SEEDS if ("BB", s, sd) in lm]
        got = note.get("language_modelling")
        if not rises:
            n_absent += 1
            if got is not None:
                fails.append(f"table {i} size {s}: label without rises")
            continue
        want_deg = any((not math.isfinite(r)) or r > 0.05 for r in rises)
        want = "LANGUAGE MODELLING DEGRADED" if want_deg else "LANGUAGE MODELLING PRESERVED"
        n_deg += want_deg
        n_pres += not want_deg
        if got is None or got["label"] != want or got["degraded"] is not want_deg:
            fails.append(f"table {i} size {s}: rises {rises} got {got and got['label']} want {want}")
    if finite:
        n_fin += 1
        h_fin.update(digest_of(full).encode())
    else:
        n_non += 1
        h_non.update(digest_of(full).encode())
print(f"{N} tables with rises: {n_fin} all-finite, {n_non} with a non-finite rise; BB labels checked: {n_deg} DEGRADED, {n_pres} PRESERVED, {n_absent} sizes with no rise")
print(f"disagreements with my reference / with the no-rise result: {len(fails)}")
for f in fails[:10]:
    print("  ", f)
print(f"digest of implementer outputs, all-finite tables: {h_fin.hexdigest()}")
print(f"digest of implementer outputs, tables with a non-finite rise: {h_non.hexdigest()}")
sys.exit(1 if fails else 0)
