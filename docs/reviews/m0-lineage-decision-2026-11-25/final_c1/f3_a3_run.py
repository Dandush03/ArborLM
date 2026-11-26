# ruff: noqa
"""Final C1 audit (fix 4), step 3: run the AUDIT-3 rule script (audit3_c1/a3_shortcuts.py, as a subprocess, not imported) on my draw.

The audit-3 script keys its shape rules on OLD lineage ids. As the implementer did (map re-typed here, checked against c1_fix4_a3_run.A3_ALIAS by eye), each draw
file is re-labelled with the old id of the lineage it descends from and run; if the script fails on it (its shape parser no longer fits), it is run again under
the draw's own id (generic rules only) and the failure is recorded. One subprocess per lineage, 6 at a time. Usage:
  python f3_a3_run.py GEN_DIR A3_SCRIPT OUT_DIR
"""
import glob, gzip, json, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

# draw "lid" (the id the rule scripts know) -> old id for audit 3
A3_OLD = {
    "C1.string_build_f3": "C1.string_build", "C1.while_counter_f3": "C1.while_counter", "C1.fast_power_f3": "C1.fast_power_r2",
    "C1.euclid_gcd_traced_f3": "C1.euclid_gcd_traced", "C1.digit_peel_f3": "C1.digit_peel", "C1.binary_search_f3": "C1.binary_search",
    "C1.counter_list_f3": "C1.counter_list", "C1.list_build_f3": "C1.list_build", "C1.cond_chain_f3": "C1.cond_chain",
    "C1.turtle_walk_f3": "C1.turtle_walk_r2", "C1.bytecode_loop_f3": "C1.bytecode_loop_r2", "C1.merge_two_sorted_f3": "C1.merge_two_sorted_r2",
    "C1.sieve_marking_f3": "C1.sieve_marking_r2", "C1.bracket_matching_f3": "C1.bracket_matching", "C1.shared_lists_f3": "C1.shared_lists",
    "C1.union_find_links_f3": "C1.union_find_links", "C1.func_compose_f3": "C1.func_compose", "C1.fib_like_f3": "C1.fib_like",
    "C1.fib_shapes_recursive_f3": "C1.fib_shapes_recursive", "C1.nested_pairs_f3": "C1.nested_pairs", "C1.string_methods_f3": "C1.string_methods",
}


def run_one(args):
    fn, a3, out_dir, label, tag = args
    d = os.path.join(out_dir, "in", tag)
    os.makedirs(d, exist_ok=True)
    with gzip.open(fn, "rt") as fi, gzip.open(os.path.join(d, label.replace("C1.", "") + ".jsonl.gz"), "wt") as fo:
        for line in fi:
            row = json.loads(line)
            row["lid"] = label
            fo.write(json.dumps(row) + "\n")
    res = os.path.join(out_dir, tag + ".json")
    p = subprocess.run([sys.executable, "-I", a3, d, res], capture_output=True, text=True, timeout=3000)
    return p.returncode, (p.stderr or "")[-400:]


def one_lineage(args):
    fn, a3, out_dir = args
    lid = "C1." + os.path.basename(fn).replace(".jsonl.gz", "")
    old = A3_OLD.get(lid)
    rec = {"alias": old}
    tag = lid.replace("C1.", "")
    if old:
        rc, err = run_one((fn, a3, out_dir, old, tag + "__alias"))
        rec.update(alias_rc=rc, alias_err=err)
        if rc != 0:
            rc2, err2 = run_one((fn, a3, out_dir, lid, tag + "__own"))
            rec.update(own_rc=rc2, own_err=err2)
    else:
        rc, err = run_one((fn, a3, out_dir, lid, tag + "__own"))
        rec.update(own_rc=rc, own_err=err)
    return lid, rec


def main():
    gen, a3, out = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(out, exist_ok=True)
    files = sorted(glob.glob(os.path.join(gen, "*.jsonl.gz")))
    log = {}
    with ThreadPoolExecutor(6) as ex:
        for lid, rec in ex.map(one_lineage, [(f, a3, out) for f in files]):
            log[lid] = rec
            print(lid, {k: v for k, v in rec.items() if not k.endswith("err")}, flush=True)
    json.dump(log, open(os.path.join(out, "run_log.json"), "w"), indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
