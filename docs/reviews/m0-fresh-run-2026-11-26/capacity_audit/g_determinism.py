"""Item 6: determinism of capacity.run_stage4 across workers (1, 16), PYTHONHASHSEED (0, 1) and start method (fork,
spawn), on toy lineages and a tiny real case, under the audit label. The demand constants are cut to DEV=4, POOL=20,
TUNING=1 in the parent (targets are computed there). The audit label and a guard that refuses the label "capacity"
are installed in the parent AND in every worker (AuditSource.__setstate__ runs in the worker before any cell).
Usage: python g_determinism.py <workers> <fork|spawn|none> <tag>. Prints the SHA-256 of the record (cap.dumps)."""
import hashlib, json, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from a_common import AUDIT_LABEL, SCR, load_lineages, load_solvers


def install_guard():
    from studies.m0.registration import capacity as cap
    cap.LABEL = AUDIT_LABEL
    if not getattr(cap.stream, "_audit_guard", False):
        orig = cap.stream
        def guarded(seed, *labels):
            if labels and labels[0] == "capacity":
                raise RuntimeError("guard: registered label")
            return orig(seed, *labels)
        guarded._audit_guard = True
        cap.stream = guarded
    return cap


def toy_build_a(level, rng):
    from studies.m0.core import Built
    k = rng.randrange(40 + 30 * level)
    return Built(f"Ben has {k} kettles.", {"i": k}, str(k), "number", None)


def toy_build_b(level, rng):
    from studies.m0.core import Built, Retry
    if rng.random() < 0.5:
        raise Retry()
    k = rng.randrange(400)
    return Built(f"Ada has {k} drums.", {"i": k}, str(k), "number", None)


def toy_solver(q, st):
    return str(st["i"])


class AuditSource:
    REAL = ["R1.compass_turns", "R2.cheapest_network", "R2.min_heap_ops", "M1.shopping_r3", "C1.postfix_evaluation"]

    def __init__(self):
        self._l = None
        self._s = None
        install_guard()

    def __getstate__(self):
        return {}

    def __setstate__(self, st):
        self._l = None
        self._s = None
        install_guard()

    def _load(self):
        from studies.m0.core import Lineage
        lins = load_lineages()
        sol = load_solvers()
        self._l = {x: lins[x] for x in self.REAL}
        self._s = {x: sol[x] for x in self.REAL}
        self._l["R1.toy_a"] = Lineage("R1.toy_a", "R1", "toy", toy_build_a)
        self._l["R1.toy_b"] = Lineage("R1.toy_b", "R1", "toy", toy_build_b)
        self._s["R1.toy_a"] = toy_solver
        self._s["R1.toy_b"] = toy_solver

    def lineage(self, lid):
        if self._l is None:
            self._load()
        return self._l[lid]

    def solver(self, lid):
        if self._s is None:
            self._load()
        return self._s[lid]


def main():
    workers, ctx, tag = int(sys.argv[1]), sys.argv[2], sys.argv[3]
    cap = install_guard()
    cap.DEV, cap.POOL, cap.TUNING = 4, 20, 1
    clusters = {"T1": ["R1.compass_turns", "R1.toy_a"], "T2": ["R1.toy_b"], "R2x": ["R2.cheapest_network", "R2.min_heap_ops"],
                "M1x": ["M1.shopping_r3"], "C1x": ["C1.postfix_evaluation"]}
    part = {"T1": "A", "T2": "A", "R2x": "B", "M1x": "A", "C1x": "B"}
    cands = {"candidates": {"R1": ["R1.compass_turns", "R1.toy_a", "R1.toy_b"], "R2": ["R2.cheapest_network", "R2.min_heap_ops"],
                            "M1": ["M1.shopping_r3"], "C1": ["C1.postfix_evaluation"]}}
    mp = {"clusters": [{"cluster_id": c, "members": m} for c, m in clusters.items()]}
    rec = cap.run_stage4(cands, {"cluster_part": part}, mp, AuditSource(), workers=workers,
                         mp_context=None if ctx == "none" else ctx)
    blob = cap.dumps(rec)
    out = f"{SCR}/work/g_det_{tag}.json"
    with open(out, "xb") as f:
        f.write(blob)
    # no count of a real lineage is printed: only the digest of the whole record and the number of rounds per part
    print(tag, "workers", workers, "ctx", ctx, "PYTHONHASHSEED", os.environ.get("PYTHONHASHSEED"),
          "record sha256", hashlib.sha256(blob).hexdigest(),
          "rounds", {e + p: len(r["rounds"]) for e, pp in rec["parts"].items() for p, r in pp.items()})


if __name__ == "__main__":
    main()
