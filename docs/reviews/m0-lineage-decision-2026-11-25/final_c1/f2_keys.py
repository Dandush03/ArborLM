# ruff: noqa
"""Final C1 audit (fix 4), step 2: independent key check from the item TEXT alone (stdlib only; imports nothing from studies/).

For items i < K of every lineage and level of a draw (f1_draw.py output): the program is extracted from the question text with MY extractor (the text between
the frame line 'Here is a Python program.' + blank line and the blank line before 'What exactly does it print?'; the frame must match exactly, else the item is
reported). Each program is run in its OWN fresh subprocess (`python -I -S -c <program>`, env = PATH + PYTHONHASHSEED only, 10 s timeout) under two
interpreters with different hash seeds. Checks: return code 0, no stderr, stdout exactly one line ending in a newline, the line non-empty, equal to the stored key,
and the two runs agree. Static checks on the extracted text (ast): exactly one print call, as the last top-level statement, not inside a loop or a function;
no import, no set display / set() / frozenset / set comprehension, no hash(), id(), globals(), locals(), vars(), input(), open(), eval/exec, no attribute access
other than the string/list methods used, no dict iteration. Usage:
  python3 f2_keys.py GEN_DIR K OUT_JSON PY_A:HASHSEED_A PY_B:HASHSEED_B [threads]
"""
import ast, glob, gzip, json, os, subprocess, sys, time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

PRE = "Here is a Python program.\n\n"
SUF = "\n\nWhat exactly does it print? It prints a single line."
OK_ATTRS = {"upper", "lower", "replace", "append", "count"}
BAD_CALLS = {"hash", "id", "globals", "locals", "vars", "input", "open", "eval", "exec", "set", "frozenset", "dir", "__import__", "compile", "sorted", "reversed"}


def extract(q):
    if not (q.startswith(PRE) and q.endswith(SUF)):
        return None
    return q[len(PRE):-len(SUF)]


def static(src):
    probs = []
    try:
        t = ast.parse(src)
    except SyntaxError as ex:
        return ["syntax:" + str(ex)]
    prints = [n for n in ast.walk(t) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "print"]
    if len(prints) != 1:
        probs.append(f"print_calls={len(prints)}")
    last = t.body[-1]
    if not (isinstance(last, ast.Expr) and isinstance(last.value, ast.Call) and isinstance(last.value.func, ast.Name) and last.value.func.id == "print"):
        probs.append("print_not_last_top_level")
    elif len(last.value.args) != 1 or last.value.keywords:
        probs.append("print_args")
    for n in ast.walk(t):
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            probs.append("import")
        if isinstance(n, (ast.Set, ast.SetComp, ast.DictComp, ast.Dict, ast.GeneratorExp, ast.Lambda, ast.Global, ast.Nonlocal, ast.Try, ast.With)):
            probs.append("node:" + type(n).__name__)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in BAD_CALLS:
            probs.append("call:" + n.func.id)
        if isinstance(n, ast.Attribute) and n.attr not in OK_ATTRS:
            probs.append("attr:" + n.attr)
        if isinstance(n, ast.While) and isinstance(n.test, ast.Constant):
            probs.append("while_constant")
    return sorted(set(probs))


def run(args):
    src, py, hs = args
    env = {"PATH": "/usr/bin:/bin", "PYTHONHASHSEED": hs}
    try:
        p = subprocess.run([py, "-I", "-S", "-c", src], capture_output=True, text=True, timeout=10, env=env)
        return p.returncode, p.stdout, p.stderr[-300:]
    except subprocess.TimeoutExpired:
        return "timeout", "", ""


def main():
    gen, K, outp = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    runs = [tuple(x.rsplit(":", 1)) for x in sys.argv[4:6]]
    threads = int(sys.argv[6]) if len(sys.argv) > 6 else 12
    vers = {}
    for py, _ in runs:
        vers[py] = subprocess.run([py, "-c", "import sys; print(sys.version.split()[0])"], capture_output=True, text=True).stdout.strip()
    items = []
    for fn in sorted(glob.glob(os.path.join(gen, "*.jsonl.gz"))):
        for l in gzip.open(fn, "rt"):
            r = json.loads(l)
            if r["i"] < K:
                items.append(r)
    t0 = time.time()
    per = defaultdict(lambda: Counter())
    bad, static_bad, frame_bad = [], [], []
    srcs = []
    for r in items:
        src = extract(r["q"])
        if src is None:
            frame_bad.append({"fid": r["fid"], "lv": r["lv"], "i": r["i"]})
        srcs.append(src)
    jobs = []
    for r, src in zip(items, srcs):
        if src is None:
            continue
        for py, hs in runs:
            jobs.append((src, py, hs))
    with ThreadPoolExecutor(threads) as ex:
        res = list(ex.map(run, jobs, chunksize=64))
    it = iter(res)
    for r, src in zip(items, srcs):
        k = (r["fid"], r["lv"])
        per[k]["n"] += 1
        if src is None:
            per[k]["frame_bad"] += 1
            continue
        sp = static(src)
        if sp:
            per[k]["static_flag"] += 1
            if len(static_bad) < 60:
                static_bad.append({"fid": r["fid"], "lv": r["lv"], "i": r["i"], "flags": sp})
            for f in sp:
                per[k]["flag:" + f] += 1
        outs = []
        for (py, hs) in runs:
            rc, out, err = next(it)
            outs.append(out)
            why = None
            if rc == "timeout":
                why = "timeout"
            elif rc != 0:
                why = "error"
            elif err:
                why = "stderr"
            elif not (out.endswith("\n") and out.count("\n") == 1):
                why = "not_one_line"
            elif out[:-1] == "":
                why = "empty_line"
            elif out[:-1] != r["key"]:
                why = "key_mismatch"
            if why:
                per[k][why] += 1
                if len(bad) < 60:
                    bad.append({"fid": r["fid"], "lv": r["lv"], "i": r["i"], "py": vers[py], "hs": hs, "why": why, "out": out[:200], "key": r["key"][:200], "err": err[-200:]})
        if outs[0] != outs[1]:
            per[k]["run_disagreement"] += 1
        if src != r["src"]:
            per[k]["text_program_differs_from_render"] += 1
    tot = Counter()
    for v in per.values():
        tot.update(v)
    out = {"gen": gen, "K": K, "interpreters": {py: {"version": vers[py], "hashseed": hs} for py, hs in runs}, "items": len(items), "subprocesses": len(jobs),
           "secs": round(time.time() - t0, 1), "totals": dict(tot),
           "per_lineage_level": {f"{a}|{b}": dict(v) for (a, b), v in sorted(per.items())}, "bad_examples": bad, "static_examples": static_bad, "frame_bad": frame_bad[:20]}
    json.dump(out, open(outp, "w"), indent=1, sort_keys=True)
    print(json.dumps({"items": len(items), "subprocesses": len(jobs), "totals": dict(tot), "secs": out["secs"], "interpreters": out["interpreters"]}, indent=1))


if __name__ == "__main__":
    main()
