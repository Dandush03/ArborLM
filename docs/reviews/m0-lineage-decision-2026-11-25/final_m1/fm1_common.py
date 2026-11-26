# ruff: noqa
"""Final M1 audit (fix 4), shared loader. Auditor: arbor-auditor (Claude Opus 5.5). Imports only the generators of the
implementation worktree (studies.m0.core and the fix-4 loader); no arborlm.*_analysis module, no implementer summary script.
Fresh audit seeds (throwaway integers, not registered study seeds) go through core.stream with the label "final-m1-a5".
Run from the implementation worktree with PYTHONPATH=<worktree>, PYTHONDONTWRITEBYTECODE=1."""
import json
import sys

from studies.m0.core import ALL_LEVELS, build_item, stream

SEEDS = {"keys": 2611251, "rules": 2611252, "levels": 2611253, "capacity": 2611254, "repro": 2611255, "samples": 2611256}


def survivors():
    """The 29 lineages the manifest marks SURVIVES, built from the fix-4 loader; checked against the manifest."""
    from studies.m0.lineages_m1_fix4 import load_registered
    man = json.load(open("studies/m0/manifests/m1_fix4_survivors.json"))
    reg = {x.id: x for x in load_registered()}
    want = sorted(man["survivors"])
    assert sorted(reg) == want, (sorted(set(reg) ^ set(want)))
    return reg


def stem(lid):
    s = lid.split(".", 1)[1]
    for suf in ("_r4", "_r3", "_r2"):
        s = s.removesuffix(suf)
    return s


def items(lin, level, n, seed, tag):
    rng = stream(seed, "final-m1-a5", tag, lin.id, str(level))
    return [build_item(lin, level, rng, "A", f"a5/{i}") for i in range(n)]


if __name__ == "__main__":
    reg = survivors()
    lv = [int(x) for x in sys.argv[1].split(",")] if len(sys.argv) > 1 else [0, 3, 6]
    per = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    for lid, lin in sorted(reg.items()):
        for L in lv:
            for it in items(lin, L, per, SEEDS["samples"], "show"):
                print(f"== {lid} L{L} ans={it.answer}\n{it.question}\n")
