# ruff: noqa: E501
"""C1 fix 4: run the audit-3 rule script (``audit3_c1/a3_shortcuts.py``, as a subprocess; it is not imported) on the fix-4 draw.

The audit-3 script keys its shape rules on the ids of the OLD lineages (``C1.string_build``, ``C1.fast_power_r2``, ...). For each lineage that has an old counterpart the draw is written under that old id
(``A3_ALIAS``) and the script is run on it; if the script's shape parser fails on the changed program, the draw is run again under its own id (generic rules only: most frequent key, best single
generic literal rule) and the failure is recorded. Lineages with no old counterpart run with their own id. One directory and one subprocess per lineage.

  uv run --locked python -m studies.m0.c1_fix4_a3_run --gen <draw dir> --a3 <path to a3_shortcuts.py> --out <dir> [--timeout 900]
"""

from __future__ import annotations

import argparse
import glob
import gzip
import json
import os
import subprocess
import sys

A3_ALIAS = {
    "C1.string_build_f3": "C1.string_build",
    "C1.while_counter_f3": "C1.while_counter",
    "C1.fast_power_f3": "C1.fast_power_r2",
    "C1.euclid_gcd_traced_f3": "C1.euclid_gcd_traced",
    "C1.digit_peel_f3": "C1.digit_peel",
    "C1.binary_search_f3": "C1.binary_search",
    "C1.counter_list_f3": "C1.counter_list",
    "C1.list_build_f3": "C1.list_build",
    "C1.cond_chain_f3": "C1.cond_chain",
    "C1.turtle_walk_f3": "C1.turtle_walk_r2",
    "C1.bytecode_loop_f3": "C1.bytecode_loop_r2",
    "C1.merge_two_sorted_f3": "C1.merge_two_sorted_r2",
    "C1.sieve_marking_f3": "C1.sieve_marking_r2",
    "C1.bracket_matching_f3": "C1.bracket_matching",
    "C1.shared_lists_f3": "C1.shared_lists",
    "C1.union_find_links_f3": "C1.union_find_links",
    "C1.coin_change_table_f3": "C1.coin_change_table",
    "C1.partition_pass_f3": "C1.partition_pass",
    "C1.cellular_update_f3": "C1.cellular_update_r2",
    "C1.majority_vote_scan_f3": "C1.majority_vote_scan_r2",
    "C1.func_compose_f3": "C1.func_compose",
    "C1.fib_like_f3": "C1.fib_like",
    "C1.fib_shapes_recursive_f3": "C1.fib_shapes_recursive",
    "C1.nested_pairs_f3": "C1.nested_pairs",
    "C1.string_methods_f3": "C1.string_methods",
}


def run_one(py: str, a3: str, src_file: str, new_lid: str, out_dir: str, tag: str, timeout: int) -> tuple[int, str]:
    d = os.path.join(out_dir, "in", tag)
    os.makedirs(d, exist_ok=True)
    name = new_lid.replace("C1.", "")
    with gzip.open(src_file, "rt") as fi, gzip.open(os.path.join(d, name + ".jsonl.gz"), "wt") as fo:
        for line in fi:
            row = json.loads(line)
            row["lid"] = new_lid
            fo.write(json.dumps(row) + "\n")
    res = os.path.join(out_dir, tag + ".json")
    p = subprocess.run([py, "-I", a3, d, res], capture_output=True, text=True, timeout=timeout, check=False)
    return p.returncode, (p.stderr or "")[-300:]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen", required=True)
    ap.add_argument("--a3", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--timeout", type=int, default=900)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    log: dict[str, dict[str, object]] = {}
    for fn in sorted(glob.glob(os.path.join(a.gen, "*.jsonl.gz"))):
        lid = "C1." + os.path.basename(fn).replace(".jsonl.gz", "")
        old = A3_ALIAS.get(lid)
        tag = lid.replace("C1.", "")
        rec: dict[str, object] = {"alias": old}
        if old:
            rc, err = run_one(sys.executable, a.a3, fn, old, a.out, tag + "__alias", a.timeout)
            rec["alias_rc"] = rc
            rec["alias_err"] = err
            if rc != 0:
                rc2, err2 = run_one(sys.executable, a.a3, fn, lid, a.out, tag + "__own", a.timeout)
                rec["own_rc"], rec["own_err"] = rc2, err2
        else:
            rc, err = run_one(sys.executable, a.a3, fn, lid, a.out, tag + "__own", a.timeout)
            rec["own_rc"], rec["own_err"] = rc, err
        log[lid] = rec
        print(lid, rec, flush=True)
    with open(os.path.join(a.out, "run_log.json"), "w") as f:
        json.dump(log, f, indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
