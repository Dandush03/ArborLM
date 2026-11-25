# ruff: noqa
"""Audit 3 (C1), step 2: execute every drawn program MYSELF in fresh subprocesses (one per lineage file and run), with a per-program
2 s alarm and a 300 s subprocess timeout, under two interpreters and two hash seeds; compare with the generator's key.

Runner: full builtins, stdout captured by redirecting sys.stdout (independent of the repo's print-capturing runner); the printed text
must be exactly one line ending in a newline.  Usage (stdlib only):
  python a2_exec.py GEN_DIR OUT_JSON PY1 [PY2 ...]
Each interpreter is run twice: PYTHONHASHSEED=0 and PYTHONHASHSEED=98765.
"""
import gzip, json, os, subprocess, sys, glob

RUNNER = r'''
import io, json, signal, sys, contextlib
def _al(s, f):
    raise TimeoutError("alarm")
signal.signal(signal.SIGALRM, _al)
srcs = json.load(sys.stdin)
out = []
for src in srcs:
    buf = io.StringIO()
    try:
        signal.setitimer(signal.ITIMER_REAL, 2.0)
        with contextlib.redirect_stdout(buf):
            exec(compile(src, "<item>", "exec"), {"__name__": "__item__"})
        signal.setitimer(signal.ITIMER_REAL, 0)
        out.append({"o": buf.getvalue(), "e": None})
    except BaseException as ex:
        signal.setitimer(signal.ITIMER_REAL, 0)
        out.append({"o": buf.getvalue(), "e": type(ex).__name__ + ": " + str(ex)[:200]})
json.dump(out, sys.stdout)
'''


def main():
    gen, outp, pys = sys.argv[1], sys.argv[2], sys.argv[3:]
    report = {"runs": [], "per_lineage": {}}
    files = sorted(glob.glob(os.path.join(gen, "*.jsonl.gz")))
    for fn in files:
        rows = [json.loads(l) for l in gzip.open(fn, "rt")]
        srcs = [r["src"] for r in rows]
        lid = rows[0]["lid"]
        res_all = {}
        for py in pys:
            for hs in ("0", "98765"):
                p = subprocess.run([py, "-I", "-c", RUNNER], input=json.dumps(srcs), capture_output=True, text=True, timeout=300,
                                   env={"PYTHONHASHSEED": hs, "PATH": "/usr/bin:/bin"})
                if p.returncode != 0:
                    raise SystemExit(f"runner failed {py} {fn}: {p.stderr[-400:]}")
                res_all[(py, hs)] = json.loads(p.stdout)
        st = {"n": len(rows), "errors": 0, "not_one_line": 0, "key_mismatch": 0, "run_disagree": 0, "q_src_mismatch": 0, "examples": []}
        for k, r in enumerate(rows):
            outs = [res_all[x][k] for x in res_all]
            texts = {o["o"] for o in outs}
            if any(o["e"] for o in outs):
                st["errors"] += 1
                st["examples"].append(("err", r["lv"], r["i"], outs[0]["e"]))
                continue
            if len(texts) != 1:
                st["run_disagree"] += 1
                st["examples"].append(("disagree", r["lv"], r["i"], sorted(texts)))
                continue
            t = texts.pop()
            if not (t.endswith("\n") and t.count("\n") == 1):
                st["not_one_line"] += 1
                st["examples"].append(("lines", r["lv"], r["i"], t))
                continue
            if t[:-1] != r["key"]:
                st["key_mismatch"] += 1
                st["examples"].append(("key", r["lv"], r["i"], t[:-1], r["key"]))
            frame = f"Here is a Python program.\n\n{r['src']}\n\nWhat exactly does it print? It prints a single line."
            if r["q"] != frame:
                st["q_src_mismatch"] += 1
        st["examples"] = st["examples"][:5]
        report["per_lineage"][lid] = st
        print(lid, {k: v for k, v in st.items() if k != "examples"}, flush=True)
    report["runs"] = [f"{py} PYTHONHASHSEED={hs}" for py in pys for hs in ("0", "98765")]
    tot = {k: sum(v[k] for v in report["per_lineage"].values()) for k in ("n", "errors", "not_one_line", "key_mismatch", "run_disagree", "q_src_mismatch")}
    report["total"] = tot
    print("TOTAL", tot)
    json.dump(report, open(outp, "w"), indent=1)


if __name__ == "__main__":
    main()
