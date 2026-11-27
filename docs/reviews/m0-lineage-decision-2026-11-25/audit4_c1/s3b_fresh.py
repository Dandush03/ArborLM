# ruff: noqa
"""Audit 4 (C1), step 3b: ONE FRESH SUBPROCESS PER PROGRAM (python -I -c <program>, 10 s timeout, env limited to PATH and PYTHONHASHSEED) for a
sample of the draw: items i < K of every lineage and level. Runs (3.12.14, PYTHONHASHSEED=0) and (3.15.1, PYTHONHASHSEED=31337).
Output must be exactly one line ending in a newline and equal to the key. Usage: python3 s3b_fresh.py GEN_DIR K PY312 PY315
"""
import glob, gzip, json, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor


def one(args):
    src, py, hs = args
    try:
        p = subprocess.run([py, "-I", "-c", src], capture_output=True, text=True, timeout=10, env={"PATH": "/usr/bin:/bin", "PYTHONHASHSEED": hs})
        return p.returncode, p.stdout, p.stderr[-200:]
    except subprocess.TimeoutExpired:
        return "timeout", "", ""


def main():
    gen, K, py12, py15 = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
    jobs, meta = [], []
    for fn in sorted(glob.glob(os.path.join(gen, "*.jsonl.gz"))):
        for l in gzip.open(fn, "rt"):
            r = json.loads(l)
            if r["i"] < K:
                for py, hs in ((py12, "0"), (py15, "31337")):
                    jobs.append((r["src"], py, hs))
                    meta.append((r["lid"], r["lv"], r["i"], r["key"], py, hs))
    bad = []
    with ThreadPoolExecutor(12) as ex:
        for m, (rc, out, err) in zip(meta, ex.map(one, jobs)):
            if rc != 0 or not (out.endswith("\n") and out.count("\n") == 1) or out[:-1] != m[3]:
                bad.append({"meta": m, "rc": rc, "out": out[:200], "err": err})
    print(json.dumps({"processes": len(jobs), "programs": len(jobs) // 2, "bad": len(bad), "examples": bad[:10]}, indent=1))


if __name__ == "__main__":
    main()
