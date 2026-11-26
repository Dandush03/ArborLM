# ruff: noqa
"""Stage-2 C1 audit, step 1: build the fresh fixture set with the BUILDER (core.build_item on the survivor lineages) and write it in the row format
that the final auditor's text-only solver (final_c1/f2_keys.py) reads. 50 items per level per lineage.

Fixture seed (from the stage-2 brief): S = int.from_bytes(sha256(b"400002|stage2-check|C1").digest()[:8], "big").
Per lineage and level (my labelling, stated): rng = core.stream(S, "<lineage id>", "<level>"), i.e. sha256("S|<lid>|<lv>")[:8] -> random.Random.
Not a run seed (fresh-shortcut|1..3) and not a dry-run seed (fresh-shortcut-dry-run). Usage (cwd = implementation worktree root):
  PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 uv run --locked python <this> OUT_DIR
"""
import gzip, hashlib, json, os, sys
sys.path.insert(0, os.getcwd())
from studies.m0.core import build_item, stream
from studies.m0.c1grammar import render
from studies.m0.lineages_c1_fix4 import all_written

PER = 50
S = int.from_bytes(hashlib.sha256(b"400002|stage2-check|C1").digest()[:8], "big")


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=False)
    surv = json.load(open("studies/m0/manifests/survivor_list_of_record.json"))["evaluations"]["C1"]
    w = all_written()
    meta = {"seed": S, "per_level": PER, "lineages": surv, "python": sys.version, "hashseed": os.environ.get("PYTHONHASHSEED"), "files": {}}
    for lid in surv:
        lin = w[lid]
        rows = []
        for lv in range(7):
            r = stream(S, lid, str(lv))
            for i in range(PER):
                it = build_item(lin, lv, r, "A", f"{lid}/L{lv}/{i}")
                rows.append({"lid": lid, "fid": lid, "lv": lv, "i": i, "id": it.id, "src": render(it.structured["program"]), "key": it.answer,
                             "q": it.question, "atype": it.answer_type, "k": it.k})
        fn = os.path.join(out, lid.replace("C1.", "") + ".jsonl.gz")
        payload = "".join(json.dumps(x, sort_keys=True) + "\n" for x in rows).encode()
        with gzip.GzipFile(fn, "wb", mtime=0) as f:
            f.write(payload)
        meta["files"][lid] = {"rows": len(rows), "sha256_uncompressed": hashlib.sha256(payload).hexdigest()}
    with open(os.path.join(out, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2, sort_keys=True)
        f.write("\n")
    print("seed", S, "lineages", len(surv), "items", sum(v["rows"] for v in meta["files"].values()))


if __name__ == "__main__":
    main()
