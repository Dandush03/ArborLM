# ruff: noqa
"""Cross-evaluation map (M0), step 1: render a few items of every SURVIVES lineage of the four fix-4 manifests, plus K0.

Reads the read-only worktree on branch claude/m0-impl (uncommitted fix-4 files, read as they are). Throwaway seeds only:
random.Random(f"xeval-map-sample|{lid}|{level}") -- a string seed, never a registered study seed. Nothing is written
outside this script's stdout.

Run (from the deliver folder):
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<impl worktree> uv run --locked --project <impl worktree> python s01_samples.py <impl worktree> > s01_samples.out.txt
"""
import json, random, sys
from pathlib import Path

W = Path(sys.argv[1])
MAN = W / "studies/m0/manifests"
LEVELS = (0, 3, 6)


def survivors():
    out = {}
    d = json.loads((MAN / "r1_fix4_survivors.json").read_text())
    out["R1"] = list(d["surviving_shapes"])
    d = json.loads((MAN / "r2_fix4_survivors.json").read_text())
    out["R2"] = list(d["surviving_lineages"])
    d = json.loads((MAN / "m1_fix4_survivors.json").read_text())
    out["M1"] = list(d["survivors"])
    d = json.loads((MAN / "c1_fix4_survivors.json").read_text())
    out["C1"] = list(d["surviving_lineages"]["list"])
    return out


def sets():
    from studies.m0.lineages_r1_fix4_clusters import candidates_v4
    from studies.m0.r2_fix4_set import fix4_set
    from studies.m0.lineages_m1_fix4 import load_all as m1_all
    from studies.m0.lineages_c1_fix4 import all_written

    return {
        "R1": {x.id: x for x in candidates_v4()},
        "R2": dict(fix4_set()),
        "M1": {x.id: x for x in m1_all()},
        "C1": dict(all_written()),
    }


def build(lin, lv, r):
    from studies.m0.core import Retry

    for _ in range(500):
        try:
            return lin.build(lv, r)
        except Retry:
            continue
    raise RuntimeError(f"{lin.id} L{lv}: 500 retries")


def show(ev, lin):
    from studies.m0.c1grammar import render

    print(f"=== {lin.id}  (family {lin.family}; module {lin.build.__module__}.{lin.build.__name__})")
    for lv in LEVELS:
        r = random.Random(f"xeval-map-sample|{lin.id}|{lv}")
        b = build(lin, lv, r)
        q = b.question
        if ev == "C1" and isinstance(b.structured, dict) and "program" in b.structured:
            q = "[program]\n" + render(b.structured["program"]) + "\n[question] " + b.question.split("\n")[-1]
        q = q if len(q) <= 1400 else q[:1400] + " ...[cut]"
        print(f"--- L{lv}  answer={b.answer!r}  type={b.answer_type}\n{q}")
    print()


def main():
    surv = survivors()
    S = sets()
    for ev in ("R1", "R2", "M1", "C1"):
        print(f"######## {ev}: {len(surv[ev])} survivors")
        for lid in sorted(surv[ev]):
            if lid not in S[ev]:
                print(f"=== {lid}: NOT FOUND in the fix-4 set loader")
                continue
            show(ev, S[ev][lid])
    from studies.m0 import core, lineages_k0  # noqa: F401

    ks = sorted(core.REGISTRY.get("K0", []), key=lambda x: x.id)
    print(f"######## K0: {len(ks)} lineages")
    for lin in ks:
        show("K0", lin)


if __name__ == "__main__":
    main()
