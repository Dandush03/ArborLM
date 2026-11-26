"""Pair audit: apply each lineage's new solver (studies/m0/solvers2/solver2_<file>.py, loaded by file path) to (question, structured)
of the fresh items in work/items_<EVAL>.jsonl and compare str(answer) == str(key) exactly. The solver gets a deep copy of `structured`
and never the key. Per-item wall limit 20 s (SIGALRM) counted as a solver error. Writes deliver/agree_<EVAL>_<tag>.json and prints a summary.
Usage: python apply_solvers.py <EVAL> <tag>   (tag names the interpreter used, e.g. py312 or py315)"""
import copy, importlib.util, json, signal, sys, time, collections, traceback, hashlib
W = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f"
OUT = "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_pair_audit_20261126"
FILES = ["r1", "r2a", "r2b", "m1a", "m1b", "m1c", "c1"]
ev, tag = sys.argv[1], sys.argv[2]
owner, fn_of = {}, {}
for f in FILES:
    p = f"{W}/studies/m0/solvers2/solver2_{f}.py"
    spec = importlib.util.spec_from_file_location(f"pairaudit_solver2_{f}", p)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    for lid, fn in mod.SOLVERS.items():
        assert lid not in owner, ("two solvers for", lid)
        owner[lid] = f"studies/m0/solvers2/solver2_{f}.py"; fn_of[lid] = fn

class Alarm(Exception):
    pass

def on_alarm(*_):
    raise Alarm()

signal.signal(signal.SIGALRM, on_alarm)
res = collections.OrderedDict(); t0 = time.time(); slow = []
for line in open(f"{OUT}/work/items_{ev}.jsonl"):
    r = json.loads(line); lid = r["id"]
    d = res.setdefault(lid, {"solver": owner.get(lid), "items": 0, "mismatches": [], "errors": [], "seconds": 0.0,
                             "levels": collections.Counter()})
    d["items"] += 1; d["levels"][r["level"]] += 1
    if lid not in fn_of:
        d["errors"].append({"level": r["level"], "index": r["index"], "error": "no solver for lineage"}); continue
    q, st = r["question"], copy.deepcopy(r["structured"])
    t1 = time.time()
    try:
        signal.alarm(20)
        a = fn_of[lid](q, st)
        signal.alarm(0)
    except BaseException as e:  # noqa: BLE001 - record, never hide
        signal.alarm(0)
        d["errors"].append({"level": r["level"], "index": r["index"], "error": f"{type(e).__name__}: {e}"[:300]})
        continue
    finally:
        d["seconds"] += time.time() - t1
    if not isinstance(a, str):
        d["errors"].append({"level": r["level"], "index": r["index"], "error": f"non-str answer {type(a).__name__}"})
    if str(a) != str(r["key"]):
        d["mismatches"].append({"level": r["level"], "index": r["index"], "answer": str(a), "key": str(r["key"])})
for d in res.values():
    d["levels"] = {str(k): v for k, v in sorted(d["levels"].items())}
    d["seconds"] = round(d["seconds"], 2)
items_sha = hashlib.sha256(open(f"{OUT}/work/items_{ev}.jsonl", "rb").read()).hexdigest()
summary = {"eval": ev, "interpreter": sys.version.split()[0], "items_file_sha256": items_sha,
           "items": sum(d["items"] for d in res.values()), "mismatches": sum(len(d["mismatches"]) for d in res.values()),
           "errors": sum(len(d["errors"]) for d in res.values()), "lineages": res}
with open(f"{OUT}/deliver/agree_{ev}_{tag}.json", "x") as fo:
    fo.write(json.dumps(summary, indent=2, sort_keys=True) + "\n")
for lid, d in res.items():
    print(f"{lid}: items {d['items']} mismatches {len(d['mismatches'])} errors {len(d['errors'])} ({d['seconds']}s)")
print(f"TOTAL {ev} [{tag} {sys.version.split()[0]}]: items {summary['items']} mismatches {summary['mismatches']} errors {summary['errors']} wall {time.time()-t0:.1f}s")
