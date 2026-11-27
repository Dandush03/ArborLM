"""Item 1 (integrity) and the round-1 parts and targets, computed from the inputs of record with my own code."""
import hashlib
import json
import subprocess
import sys

sys.path.insert(0, "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_capacity_recompute_20261126/deliver")
import rc_common as rc  # noqa: E402

W = rc.W


def sha(rel):
    with open(f"{W}/{rel}", "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


out = {}
rec_path = "studies/m0/manifests/capacity_of_record.json"
out["record_sha256"] = sha(rec_path)
out["record_sha256_expected"] = "33c393fbd0770520c489c8bd8591a1a0febd3f4273961499619a1d6eaa12fb34"
rec = rc.load_json(rec_path)
out["record_input_hashes"] = {k: [v, sha(rec["inputs"][k]), v == sha(rec["inputs"][k])] for k, v in rec["inputs"]["sha256"].items()}
hr = rc.load_json("docs/reviews/m0-fresh-run-2026-11-26/HASH_RECORD_STAGES_2_TO_4.json")
code = {}
for name in ("candidate_list", "capacity_runner", "distinct_item_key", "map_of_record", "partition_code", "partition_of_record", "pool_builder"):
    p, h = hr[name]["path"], hr[name]["sha256"]
    code[name] = [p, h, sha(p), h == sha(p)]
for p, h in hr["second_solvers"].items():
    code[p] = [p, h, sha(p), h == sha(p)]
out["hash_record_vs_files"] = code
# file contents at the run commit c01b7f89 and the record commit f9f4ca74 versus the working tree
gitcmp = {}
for c in ("c01b7f89", "f9f4ca74"):
    for name, (p, h, *_rest) in code.items():
        blob = subprocess.run(["git", "-C", W, "show", f"{c}:{p}"], capture_output=True, check=True).stdout
        gitcmp[f"{c}:{p}"] = hashlib.sha256(blob).hexdigest() == h
    blob = subprocess.run(["git", "-C", W, "show", f"{c}:{rec_path}"], capture_output=True).stdout
    gitcmp[f"{c}:{rec_path}"] = hashlib.sha256(blob).hexdigest() if blob else "absent"
out["git_blobs_equal_hash_record"] = gitcmp
diff = subprocess.run(["git", "-C", W, "diff", "--stat", "c01b7f89", "f9f4ca74", "--", "studies", "src", "tests"], capture_output=True, text=True).stdout
out["diff_c01b7f89_f9f4ca74_studies_src_tests"] = diff
diff2 = subprocess.run(["git", "-C", W, "diff", "--stat", "7cd0ac5a", "c01b7f89", "--", "studies/m0/core.py", "studies/m0/vocab.py"], capture_output=True, text=True).stdout
out["diff_7cd0ac5a_c01b7f89_core_vocab"] = diff2
out["record_spec"] = rec["spec"]

parts = rc.round1_parts()
mine = {}
for (e, p), cls in sorted(parts.items()):
    G = len(cls)
    mine[f"{e}{p}"] = {"G": G, "D_G": rc.D(G), "clusters": {c: {"k": len(v), "D_lin": rc.D_lin(G, len(v)), "lineages": v} for c, v in sorted(cls.items())}}
out["round1_parts_mine"] = mine
cmp = {}
for e in ("R1", "R2", "M1", "C1"):
    for p in ("A", "B"):
        r = rec["parts"][e][p]
        m = mine[f"{e}{p}"]
        same_start = {c: sorted(v) for c, v in r["start"].items()} == {c: x["lineages"] for c, x in m["clusters"].items()}
        r1 = r["rounds"][0]
        same_targets = r1["G"] == m["G"] and r1["D_G"] == m["D_G"] and all(
            r1["clusters"][c]["D_lin"] == x["D_lin"] and r1["clusters"][c]["k"] == x["k"] for c, x in m["clusters"].items())
        cmp[f"{e}{p}"] = {"start_equal": same_start, "round1_G_D_Dlin_equal": same_targets, "G": m["G"], "lineages": sum(x["k"] for x in m["clusters"].values())}
out["round1_parts_vs_record"] = cmp
out["n_cells_round1"] = 7 * sum(sum(x["k"] for x in m["clusters"].values()) for m in mine.values())
json.dump(out, open(f"{rc.SCR}/deliver/a_integrity_parts.json", "x"), indent=1, sort_keys=True)
print(json.dumps({k: v for k, v in out.items() if k != "round1_parts_mine"}, indent=1, sort_keys=True))
