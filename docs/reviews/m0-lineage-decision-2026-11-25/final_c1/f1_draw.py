# ruff: noqa
"""Final C1 audit (fix 4), step 1: draw items of the 27 SURVIVING lineages with MY throwaway seeds (not registered study seeds).

Stream: sha256("finalc1|<seed>|<fix-4 id>|<level>") -> random.Random. The builders are called directly (lineage.build), with my own retry loop (500 cap,
as core.build_item). Every Retry is classified (R-19): the shared finish of lineages_c1 is wrapped IN THIS PROCESS ONLY (no file is edited) so that a Retry
raised inside finish is labelled by re-running the rendered program myself (exec under an alarm): program error <type>, or which answer property failed
(empty / not lower case / not stripped / double space / final full stop). A Retry raised by the builder itself before finish is labelled "builder".
Rows are written in the format of audit4_c1/s2_gen.py, with "lid" set to the id the rule scripts know (the implementer's RULE_ALIAS, re-typed here) and "fid"
the fix-4 id. Usage (cwd = the audited worktree):
  PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 uv run --locked python <this> --seed S --per-level N --out DIR [--workers K] [--ids a,b]
"""
import argparse, contextlib, gzip, hashlib, io, json, os, random, signal, sys, time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.getcwd())

SURVIVORS = ["C1.binary_search_f3", "C1.bracket_matching_f3", "C1.bytecode_loop_f3", "C1.circle_elimination_r2", "C1.cond_chain_f3", "C1.counter_list_f3",
             "C1.digit_peel_f3", "C1.euclid_gcd_traced_f3", "C1.fast_power_f4", "C1.fib_like_f3", "C1.fib_shapes_recursive_f3", "C1.func_branch_f4",
             "C1.func_compose_f4", "C1.list_build_f3", "C1.merge_two_sorted_f3", "C1.nested_pairs_f3", "C1.postfix_evaluation", "C1.recursive_calls_r2",
             "C1.run_length_scan", "C1.shared_lists_f3", "C1.sieve_marking_f4", "C1.slices_f4", "C1.string_build_f3", "C1.string_methods_f3",
             "C1.turtle_walk_f3", "C1.union_find_links_f3", "C1.while_counter_f3"]
ALIAS = {"C1.sieve_marking_f4": "C1.sieve_marking_f3", "C1.fast_power_f4": "C1.fast_power_f3", "C1.func_branch_f4": "C1.func_branch",
         "C1.func_compose_f4": "C1.func_compose_f3", "C1.slices_f4": "C1.slices"}


def rng_for(seed, lid, lv):
    d = hashlib.sha256(f"finalc1|{seed}|{lid}|{lv}".encode()).digest()
    return random.Random(int.from_bytes(d[:8], "big"))


def my_run(src):
    buf = io.StringIO()
    def _al(s, f):
        raise TimeoutError
    old = signal.signal(signal.SIGALRM, _al)
    try:
        signal.setitimer(signal.ITIMER_REAL, 2.0)
        with contextlib.redirect_stdout(buf):
            exec(compile(src, "<p>", "exec"), {"__name__": "__p__"})
        signal.setitimer(signal.ITIMER_REAL, 0)
    except BaseException as ex:
        signal.setitimer(signal.ITIMER_REAL, 0)
        return None, type(ex).__name__
    finally:
        signal.signal(signal.SIGALRM, old)
    return buf.getvalue(), None


REASONS = Counter()


def install_wrapper():
    import studies.m0.lineages_c1 as l1
    import studies.m0.lineages_c1_common as cm
    from studies.m0.core import Retry
    from studies.m0.c1grammar import render
    if getattr(l1._finish, "_final_c1_wrapped", False):  # a worker handles several lineages: wrap once (first trial double-counted)
        return
    orig = l1._finish

    def wrapped(prog, *a, **k):
        try:
            return orig(prog, *a, **k)
        except Retry:
            out, err = my_run(render(prog))
            if err:
                REASONS["finish:program_error:" + err] += 1
            else:
                ans = out[:-1] if out.endswith("\n") else out
                why = [w for w, c in (("empty", ans == ""), ("not_lower", ans != ans.lower()), ("not_stripped", ans != ans.strip()),
                                      ("double_space", "  " in ans), ("final_stop", ans.endswith("."))) if c]
                REASONS["finish:answer:" + "+".join(why or ["unknown"])] += 1
            raise
    wrapped._final_c1_wrapped = True
    l1._finish = wrapped
    cm._finish = wrapped


def work(args):
    lid, seed, per_level, out = args
    install_wrapper()
    from studies.m0.core import Retry
    from studies.m0.c1grammar import render
    from studies.m0.lineages_c1_fix4 import all_written
    lin = all_written()[lid]
    rows, rstat = [], {}
    for lv in range(7):
        REASONS.clear()
        r = rng_for(seed, lid, lv)
        total_retries = 0
        for i in range(per_level):
            tries = 0
            while True:
                tries += 1
                if tries > 500:
                    raise RuntimeError(f"{lid} L{lv}: 500 retries")
                try:
                    b = lin.build(lv, r)
                    break
                except Retry:
                    continue
            total_retries += tries - 1
            rows.append({"lid": ALIAS.get(lid, lid), "fid": lid, "lv": lv, "i": i, "src": render(b.structured["program"]), "key": b.answer, "q": b.question,
                         "retries": tries - 1, "atype": b.answer_type})
        fin = sum(REASONS.values())
        rstat[lv] = {"retries": total_retries, "builder": total_retries - fin, **dict(REASONS)}
    with gzip.open(os.path.join(out, ALIAS.get(lid, lid).replace("C1.", "") + ".jsonl.gz"), "wt") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
    return lid, len(rows), rstat


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--per-level", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--ids", default="")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    ids = a.ids.split(",") if a.ids else SURVIVORS
    t = time.time()
    stats = {}
    with ProcessPoolExecutor(a.workers) as ex:
        for lid, n, rs in ex.map(work, [(l, a.seed, a.per_level, a.out) for l in ids]):
            stats[lid] = rs
            print(lid, n, "retries", sum(v["retries"] for v in rs.values()), flush=True)
    with open(os.path.join(a.out, "meta.json"), "w") as f:
        json.dump({"ids": ids, "seed": a.seed, "per_level": a.per_level, "python": sys.version, "alias": ALIAS, "retry_reasons": stats,
                   "hashseed": os.environ.get("PYTHONHASHSEED")}, f, indent=1, sort_keys=True)
    print("secs", round(time.time() - t, 1))


if __name__ == "__main__":
    main()
