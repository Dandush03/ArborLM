# ruff: noqa
"""Final C1 audit (fix 4), step 9 helper: build, in THIS process, one small pool per surviving lineage with core.generate_pool as written (part_lineages substituted
to return that lineage, as in f6_capacity.py), all seven levels, and print one SHA-256 over core.pool_hash of every pool plus each lineage's pool hash (JSON).
Run twice in fresh processes with different PYTHONHASHSEED; the outputs must be identical. Usage: uv run --locked python <this> SEED PER_LINEAGE
"""
import json, os, sys, hashlib
sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from f1_draw import SURVIVORS


def main():
    seed, size = int(sys.argv[1]), int(sys.argv[2])
    import studies.m0.core as core
    from studies.m0.lineages_c1_fix4 import all_written
    w = all_written()
    out = {}
    taken = set()
    for lid in SURVIVORS:
        lin = w[lid]
        core.part_lineages = lambda e, p, s=400004, _l=lin: [_l]
        pool = core.generate_pool("C1", "A", "final-c1-repro", seed, size, {lv: 1.0 for lv in range(7)}, taken)
        out[lid] = core.pool_hash(pool)
    allh = hashlib.sha256(json.dumps(out, sort_keys=True).encode()).hexdigest()
    print(json.dumps({"all": allh, "per_lineage": out, "hashseed": os.environ.get("PYTHONHASHSEED"), "python": sys.version.split()[0]}, sort_keys=True))


if __name__ == "__main__":
    main()
