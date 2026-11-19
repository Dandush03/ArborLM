# P10-I-S2 Part Q: fourth re-audit, at 3c2b1b6, before the freeze for registered attempt 2

- **Auditor.** The `arbor-auditor` subagent, model Claude Opus 5.5 (`claude-opus-5-5`), 2026-11-18. I wrote none of the audited code.
- **Object.** `git diff 039b1d4..3c2b1b6` (one commit, `3c2b1b6`), read by commit (`git archive 3c2b1b6`), never from the working tree.
- **Scratch.** `/Users/daniellaloush/dandush03/ArborLM-sealed/audit-s2-r4/`, outside every git working tree; deleted after this report. It held one fully frozen scratch clone: a registered-mode plan built by the code with its own import walk, a freeze record and a committed Decision 2.
- **Launches.** All stages went through `partq_registered.sh`, one fresh process each. Fakes covered the downloads and teachers only, via the implementer's `p10is2_e2e_world.install()` run by a fake `uv`; no `PYTHONPATH` was set.
- **Limits observed.** One process at a time, a `timeout` on every command, no pytest run, no sealed value, no registered seed on real data, no network, no git writes outside the scratch clone.
- **Out-of-lock packages: none used.** The F2 check below used **no package outside the lock and no tokenizer library**. It is my own pure-Python byte-level BPE, built from the student's `tokenizer.json` (a data file), and validated against P10-S2's recorded token ids.
- **Status.** This audit is independent engineering evidence. It is not Astra validation and not human approval. `Astra review: NOT_PERFORMED`.

## Verdict: READY TO FREEZE

This holds on one condition, stated in Decision 2 or fixed in code (R1). F1, A2 and F2 pass. F3 of `REAUDIT3` (the uncounted charges) still belongs in Decision 2.

## 1. F1, the Part Q manifest: FIXED

**The run.** All eight stages ran in my clone, each exiting 0, and ended in a label (`TEACHERS-QUALIFIED (DISJOINT DRAWS)`, synthetic data).

**After the analysis stage had ended:**
- the manifest lists **124 files: none missing, none with another hash**;
- it states its 6 exclusions under `excluded`.

**The 18 files on disk that are not listed** are exactly the excluded kinds, none of them a result:
- `charged_ledger.json` and `manifest.json` itself;
- the 8 runner stage manifests `<stage>/manifest.json`;
- the 8 completion records in `stages/`.

**Results that are listed:** `qualification.json`, `generation/result.json`, `generation/pools.json`, all 9 files of `outputs/bundle/`, and every batch and stage record. A stage-level `engineering_failures.json` or `item_errors/` would also be listed, since neither is excluded.

**What the exclusions hide.** Neither the per-stage manifests nor `sealed/` hold anything a reader of the manifest relies on: `sealed/` is empty in a registered run, and the runner manifests hold timings, statuses and the processes alive.

**One reader does rely on an excluded file (A1 below).** Part T's descriptive cost line (`partt_cost.teacher_inference`) reads Part Q's `charged_ledger.json` directly.

**The self-check.** `write_manifest` re-hashes after writing and raises `RegisteredTestStop` on any difference.
- On a healthy run it **cannot** trip from the study's own writes. In both `outputs` and `analysis` it is the last write to a listed file; everything written later is excluded (`stages/`, the charge ledger, the runner manifest, the heartbeat marker).
- But see R1.

## 2. A2, the reused process ID: FIXED

In each case a running marker for `analysis` was placed in a copy of the run directory, and the real `analysis` stage was then launched:

| Marker | Result |
|---|---|
| Dead PID, start time recorded | Runs (exit 0). The dead process is charged **30 s** as killed (a lower bound); the marker is removed |
| A live PID whose recorded start time differs (a reused PID) | Runs (exit 0), charged 30 s as killed |
| A live PID with **no** start time recorded | **REFUSED** "process … is still running" (exit 2); the marker is kept |
| A **genuinely live** process (its PID and its real `ps -o lstart` start time) | **REFUSED** (exit 2) |

## 3. F2, the shared ledger against the real tokenizer grid: PASS

- **How it was run.** I implemented my own byte-level BPE in pure Python from `downloads/student/tokenizer.json`:
  - vocab of 49,152 and 48,900 merges;
  - the `Digits(individual)` then `ByteLevel` GPT-2 pre-tokenizer, the regex emulated with `unicodedata`;
  - no normalizer, no post-processor.
- **Tokenization.** The WikiText-2 validation text (rows concatenated per A-B3) gives 265,682 tokens.
- **Validation of my BPE against P10-S2's recorded `windows.json`,** which the real tokenizer produced on the same text and grid: **144 of 144 recorded windows (all 44 marker-like) occur exactly at grid positions** (`ids[w0:w0+256]`, `w0` a multiple of 256). That is 36,864 tokens equal and token counts aligned across the whole text.
- **The grid, built by the study's own `real_world.window_grid` and `window_spans`** (byte spans, found once): 968 classified windows, **44 marker-like, 924 ordinary candidates**.
- **`step8.verify_study_ledger`** (exactly the check of the registered `inputs` stage, read-only) on the **live** `data/p10i-shared/panel_ledger.json`:
  - `verified: True`, marker-like 44, ordinary 100;
  - `check ok`, self-overlaps 0, ordinary windows overlapping other owners 0.
- **P10-I-S3's own reader** (`studies/p10i_s3/window_spans.py` at `c333fff`, read-only, no bytecode) on the live file:
  - `read_ledger`: 1,168 entries accepted;
  - `build_excluded`: state `read`, its 44-marker check passed;
  - all 144 of our windows inside its exclusions;
  - **0 overlaps** with its 1,024 panel entries.
  - That worktree already showed `M conftest.py` before my run; it was not mine.
- **Nothing was written.** The ledger's SHA-256 was `62f811161420…` before and after both checks. No run directory, plan, freeze folder or ledger was touched.
- **If you want the same check with the real tokenizer:** run, with the packages on the path as `partq_ledger.sh` sets them, a light `real_stages.build_world(cfg, repo, <scratch dir>, "registered", load_teachers=False, light=True)` followed by `window_candidates` and `step8.verify_study_ledger(cfg, <live ledger>, marker, ordinary)`. It writes nothing. My BPE result above already reproduces the real tokenizer on every recorded window.

## 4. Anything else in the diff

**R1 (REQUIRED, condition for the freeze; `real_stages.write_manifest`): any foreign file appearing while the manifest is written turns the outcome into an engineering failure.**
- The self-check compares two full hashes of the run directory. A foreign file appearing between them — a Finder `.DS_Store`, an editor swap file, a copy made into the directory — raises `RegisteredTestStop`. `execute` then calls `pipeline.fail`, which writes `engineering_failures.json`, and every later analysis derives **QUALIFICATION-ENGINEERING-FAILURE** (section 4.4 row 1) from it, permanently.
- The window lasts as long as two hashings of the run directory (the 1.2 GB bundle and about 27,000 batch files), so seconds, in both `outputs` and `analysis`.
- A stray file is not a "failed gate on study-produced data".
- Either:
  - **record in Decision 2** that nothing but the stage process writes in the run directory while `outputs` and `analysis` run (no Finder, no editor, no copying into it); or
  - **fix it in code**: ignore dot-files, and raise `StageRefused` instead of `RegisteredTestStop` on a mismatch. The stage then refuses and can be re-run, without an engineering-failure record.

**A1 (ADVISORY, Part T; `partt_cost.teacher_inference` and `partt_real.load_*`):** Part T reads Part Q files (`charged_ledger.json`, `generation/*.json`, `outputs/bundle`, `outputs/gloss_bank.json`) directly from the Part Q run directory, without checking each against the Part Q manifest (ruling L12 checks the manifest file's hash only). `charged_ledger.json` is not in the manifest at all. For Part T: verify every file read from the Part Q directory against the manifest, and pin the final charge ledger by hash at the Part T freeze.

**Re-launching a completed stage:** re-running a stage that is already COMPLETE fails at the end, because a COMPLETE runner manifest is never rewritten. It does not corrupt anything. It is unchanged from before and not a finding.

**Reminder from `REAUDIT3` F3:** record in Decision 2 the charges outside the 22.49 h total: 959.3 s (the first measuring attempt), the counting rehearsals, the ledger command, and attempt 1's 13.09 s.

## Scripts (verbatim; scratch deleted)

### f2_bpe.py
```python
"""F2 without any package outside the lock: the auditor's OWN byte-level BPE (pure Python, from the student's tokenizer.json, a data file:
vocab, merges, the Digits(individual) + ByteLevel(GPT-2 regex, emulated with unicodedata) pre-tokenizer, no normalizer, no post-processor),
validated against P10-S2's RECORDED token ids of its 144 GEN windows (windows.json, made by the real tokenizer on the same text and grid):
every recorded window must equal ids[w0:w0+256] at a grid position w0. Then the study's own window_grid / window_spans /
verify_study_ledger (read-only) on the LIVE shared ledger, with this tokenizer object injected. Writes nothing outside the scratch folder."""
import json, sys, time, unicodedata
from pathlib import Path
import pyarrow.parquet as pq
root = Path(sys.argv[1]); sys.path[:0] = [str(root), str(root / "src")]
D = Path("/Users/daniellaloush/dandush03/ArborLM/data/p10s2-pre-20261115")
T = json.loads((D / "downloads/student/tokenizer.json").read_text())
vocab = T["model"]["vocab"]; merges = [tuple(m.split(" ")) if isinstance(m, str) else tuple(m) for m in T["model"]["merges"]]
rank = {m: i for i, m in enumerate(merges)}
added = {a["content"]: a["id"] for a in T["added_tokens"]}
def bytes_to_unicode():
    bs = list(range(ord("!"), ord("~") + 1)) + list(range(ord("¡"), ord("¬") + 1)) + list(range(ord("®"), ord("ÿ") + 1))
    cs = bs[:]; n = 0
    for b in range(256):
        if b not in bs: bs.append(b); cs.append(256 + n); n += 1
    return dict(zip(bs, map(chr, cs)))
B2U = bytes_to_unicode(); U2B = {v: k for k, v in B2U.items()}
id2tok = {i: t for t, i in vocab.items()}
for a, i in added.items(): id2tok[i] = a
def tok_bytes(i):
    t = id2tok[i]
    return t.encode() if t in added else bytes(U2B[c] for c in t)
cat = lambda c: unicodedata.category(c)
isL = lambda c: cat(c)[0] == "L"; isN = lambda c: cat(c)[0] == "N"; isS = lambda c: c.isspace()
def gpt2_split(s):  # leftmost-first alternation of the GPT-2 pattern
    out, i, n = [], 0, len(s)
    while i < n:
        j = None
        for con in ("'s", "'t", "'re", "'ve", "'m", "'ll", "'d"):
            if s.startswith(con, i): j = i + len(con); break
        if j is None:
            k = i + 1 if s[i] == " " else i
            for pred in (isL, isN, lambda c: not isS(c) and not isL(c) and not isN(c)):
                m = k
                while m < n and pred(s[m]): m += 1
                if m > k: j = m; break
        if j is None and isS(s[i]):
            m = i
            while m < n and isS(s[m]): m += 1
            if m == n: j = m
            elif m - i >= 2: j = m - 1
            else: j = m  # \s+ (alternative 6)
        if j is None: j = i + 1  # cannot happen: every char matches some alternative
        out.append((i, j)); i = j
    return out
cache = {}
def bpe(piece):
    if piece in cache: return cache[piece]
    w = [B2U[b] for b in piece.encode()]
    while len(w) > 1:
        best = min(((rank.get((w[k], w[k + 1]), 1 << 30), k) for k in range(len(w) - 1)))
        if best[0] == 1 << 30: break
        a, b = w[best[1]], w[best[1] + 1]; nw, k = [], 0
        while k < len(w):
            if k < len(w) - 1 and w[k] == a and w[k + 1] == b: nw.append(a + b); k += 2
            else: nw.append(w[k]); k += 1
        w = nw
    r = [vocab[t] for t in w]; cache[piece] = (r, w); return cache[piece]
class Tok:
    vocab_size = len(id2tok)
    def token_bytes(self): return [tok_bytes(i) if i in id2tok else b"" for i in range(max(id2tok) + 1)]
    def encode_offsets(self, text):
        assert not any(a in text for a in added), "an added token occurs in the text"
        ids, offs = [], []
        # Digits(individual): every numeric char isolated
        pieces, start = [], 0
        for k, c in enumerate(text):
            if isN(c):
                if k > start: pieces.append((start, k))
                pieces.append((k, k + 1)); start = k + 1
        if start < len(text): pieces.append((start, len(text)))
        for a, b in pieces:
            for x, y in gpt2_split(text[a:b]):
                s = text[a + x:a + y]; r, toks = bpe(s)
                cb = [0]
                for ch in s: cb.append(cb[-1] + len(ch.encode()))
                pos = 0
                for i_, t in zip(r, toks):
                    nb = len(t)  # byte-level symbols: one char per byte
                    b0, b1 = pos, pos + nb; pos = b1
                    c0 = max(k for k in range(len(cb)) if cb[k] <= b0); c1 = min(k for k in range(len(cb)) if cb[k] >= b1)
                    ids.append(i_); offs.append((a + x + c0, a + x + c1))
        return ids, offs
rows = pq.read_table("/Users/daniellaloush/dandush03/ArborLM/data/wikitext2/validation-00000-of-00001.parquet", columns=["text"]).column(0).to_pylist()
text = "".join(rows); tok = Tok()
t0 = time.time(); ids, offs = tok.encode_offsets(text); print(f"own BPE: {len(ids)} tokens in {time.time()-t0:.0f} s")
rec = json.loads((D / "data/bundle/windows.json").read_text())["windows"]
grid = {tuple(ids[w0:w0 + 256]): w0 for w0 in range(0, len(ids) - 255, 256)}
hits = [grid.get(tuple(w["ids"])) for w in rec]
print(f"validation: P10-S2 recorded windows found at a grid position: {sum(h is not None for h in hits)} of {len(rec)} (markers {sum(1 for w, h in zip(rec, hits) if h is not None and w['stratum']=='marker')} of 44)")
from studies.p10is2.common import core
from studies.p10is2.partq import real_world, step8
cfg = core.load_config("Q", root / core.CONFIG_Q)
g = real_world.window_grid(tok, text, int(cfg["panels"]["general_window_tokens"]), 64)
spans = real_world.window_spans(g, tok.token_bytes(), rows)
marker = [s for s in spans if s.kind == "marker"]; ordinary = [s for s in spans if s.kind == "ordinary"]
print(f"grid: {len(g)} classified windows; marker-like {len(marker)}; ordinary candidates {len(ordinary)}")
led = Path("/Users/daniellaloush/dandush03/ArborLM/data/p10i-shared/panel_ledger.json")
import hashlib; print("live ledger sha256:", hashlib.sha256(led.read_bytes()).hexdigest()[:12])
try:
    print("verify_study_ledger (the registered inputs stage's check):", step8.verify_study_ledger(cfg, led, marker, ordinary))
except core.StageRefused as e:
    print("verify_study_ledger REFUSED:", e)
print("live ledger sha256 after:", hashlib.sha256(led.read_bytes()).hexdigest()[:12])
```

### f2_s3reader.py
```python
"""P10-I-S3's OWN reader (studies/p10i_s3/window_spans.py, imported read-only, no bytecode) on the LIVE shared ledger: read_ledger, then
build_excluded with P10-S2's recorded windows (its no-tokenizer route; refuses unless the ledger's marker entries equal P10-S2's 44)."""
import hashlib, sys, tomllib
from pathlib import Path
import pyarrow.parquet as pq
s3 = Path(sys.argv[1]); led = Path("/Users/daniellaloush/dandush03/ArborLM/data/p10i-shared/panel_ledger.json")
sys.path[:0] = [str(s3), str(s3 / "src")]
from studies.p10i_s3 import window_spans as ws
print("ledger sha256:", hashlib.sha256(led.read_bytes()).hexdigest()[:12])
rows = pq.read_table("/Users/daniellaloush/dandush03/ArborLM/data/wikitext2/validation-00000-of-00001.parquet", columns=["text"]).column(0).to_pylist()
layout = ws.RowLayout(rows); entries = ws.read_ledger(led, layout); print("S3 read_ledger: entries", len(entries))
cfg_s2 = tomllib.loads((s3 / "configs/p10s2_transfer.toml").read_text())
rec = ws.p10s2_windows_from_records(rows, Path("/Users/daniellaloush/dandush03/ArborLM/data/p10s2-pre-20261115/data/bundle"), s3 / "results/p10s2-datagen-2026-11-16/bundle_manifest.json", cfg_s2)
doc = ws.build_excluded(rows, rec, ledger_path=led, ledger_absent=False)
ex = {tuple(s) for s in doc["spans"]}
ours = [w for w in entries if w.get("owner") == "P10IS2-partq"]
print("S3 build_excluded:", doc["ledger"]["state"], "| our windows", len(ours), "all inside S3's exclusions:", all(t in ex for w in ours for t in layout.to_row_spans(w["start"], w["end"])))
s3p = [w for w in entries if str(w.get("source", "")).startswith("P10-I-S3 panel")]
print("S3 panel entries:", len(s3p), "| overlaps with our 144:", sum(1 for a in ours for b in s3p if a["start"] < b["end"] and b["start"] < a["end"]))
print("ledger sha256 after:", hashlib.sha256(led.read_bytes()).hexdigest()[:12])
```

### e2e4.py
```python
"""REAUDIT4, items 1-2. Own fully frozen scratch clone of 3c2b1b6 (git archive + git init, registered-mode plan built by the code, freeze
record, committed Decision 2); all eight stages through partq_registered.sh, fresh process each; fakes only for downloads and teachers
(the implementer's p10is2_e2e_world.install() via a fake uv; no PYTHONPATH). Then: the Part Q manifest checked AFTER the analysis ended;
then the running-marker cases (A2) on the analysis stage of a second run directory."""
import hashlib, json, os, subprocess, sys, time
from pathlib import Path
src, base, py = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
GITC = ["-c", "commit.gpgsign=false", "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
def git(r, *a): return subprocess.run(["git", "-C", str(r), *GITC, *a], capture_output=True, text=True, check=True).stdout.strip()
SETUP = r'''
import sys; from pathlib import Path
r=Path(sys.argv[1]); run=Path(sys.argv[2]); led=Path(sys.argv[3]); base=Path(sys.argv[4])
sys.path[:0]=[str(r), str(r/'src'), str(r/'tests')]
import p10is2_e2e_world as world
from studies.p10is2.common import core, plan as planmod
from studies.p10is2.common.panel_ledger import RowMap
from studies.p10is2.partq import plan as qplan, real_stages, step8, pkgmanifest
from arborlm.io import write_json, file_sha256
cp=r/core.CONFIG_Q; cp.write_text(world.scaled_config_text(cp.read_text(), led)); cfg=core.load_config('Q', cp)
w=world.make_world(cfg, r, base/'w'); _g, m, o = real_stages.window_candidates(w, cfg)
step8.write_study_ledger(cfg, 'test', led, m, o, row_map=RowMap.from_rows(w.wikitext_rows['validation']))
d=base/'durable'/'fakepkg-1.0.dist-info'; d.mkdir(parents=True, exist_ok=True); (d/'METADATA').write_text('Name: fakepkg\nVersion: 1.0\n')
data=base/'in.bin'; data.write_bytes(b'abc')
inputs={'data': {'path': str(data), 'sha256': file_sha256(data)}, pkgmanifest.KEY: pkgmanifest.build_manifest(d.parent, None)}
(r/core.FREEZE_DIR).mkdir(parents=True, exist_ok=True); (r/core.PLAN_Q).unlink(missing_ok=True)
rec=qplan.build_candidate(r, run, cfg, inputs=inputs, walk=planmod.import_walk(r, 'Q')); write_json(r/core.PLAN_Q, core.jsonable(rec))
write_json(r/core.FREEZE_RECORD_Q, {'kind':'freeze_record','plan_file_sha256': file_sha256(r/core.PLAN_Q)})
'''
r = base / "clone"; run = base / "run"
subprocess.run(f"rm -rf '{r}' '{run}' && mkdir -p '{r}' && git -C '{src}' archive 3c2b1b6 | tar -x -C '{r}'", shell=True, check=True)
(r / "studies/p10is2/freeze/partq_freeze_record.json").unlink(missing_ok=True)
git(r, "init", "-q"); git(r, "add", "-A"); git(r, "commit", "-q", "-m", "base")
subprocess.run([py, "-B", "-c", SETUP, str(r), str(run), str(base / "ledger.json"), str(base)], check=True, capture_output=True, text=True, cwd=r)
git(r, "add", "-A"); git(r, "commit", "-q", "-m", "freeze"); c = git(r, "rev-parse", "HEAD")
dd = r / "results/p10is2-partq-freeze-20261201"; dd.mkdir(parents=True); (dd / "DECISION_2_PARTQ.md").write_text(f"freeze {c}\nDECISION: RUN\n"); git(r, "add", "-A"); git(r, "commit", "-q", "-m", "d2")
bindir = base / "bin"; bindir.mkdir(exist_ok=True)
(bindir / "uv").write_text('#!/bin/sh\nwhile [ "$1" != "python" ]; do shift; done\nshift\nshift\nunset PYTHONPATH\nexec "$E2E_PY" "$E2E_HOOK" "$@"\n'); os.chmod(bindir / "uv", 0o755)
env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "OMP_NUM_THREADS")}
env.update(PATH=f"{bindir}:{env['PATH']}", E2E_PY=py, E2E_HOOK=str(r / "tests/p10is2_e2e_hook.py"), E2E_SRC=str(r / "src"), E2E_ROOT=str(r), E2E_TESTS=str(r / "tests"), PYTHONDONTWRITEBYTECODE="1")
def launch(st):
    p = subprocess.run(["sh", str(r / "studies/p10is2/launch/partq_registered.sh"), st, str(run), c], cwd=r, env=env, capture_output=True, text=True, timeout=900)
    errs = [l for l in p.stderr.splitlines() if "Warning" not in l and "_conversion" not in l]
    return p.returncode, (errs[-1][:170] if errs else "")
STAGES = ["inputs", "partition", "qfit", "qcheck", "generation", "regeneration", "outputs", "analysis"]
for st in STAGES:
    print(f"[1] {st}:", launch(st))
print("[1] label:", json.loads((run / "qualification.json").read_text())["label"])
m = json.loads((run / "manifest.json").read_text()); files = m["files"]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
missing = [k for k in files if not (run / k).is_file()]; differ = [k for k in files if (run / k).is_file() and sha(run / k) != files[k]]
allf = sorted(str(f.relative_to(run)) for f in run.rglob("*") if f.is_file())
unlisted = [k for k in allf if k not in files]
print(f"[1] manifest after the analysis ENDED: {len(files)} listed; missing {missing}; other hash {differ}")
print(f"[1] files on disk not listed ({len(unlisted)}): {unlisted}")
print(f"[1] 'excluded' stated: {len(m.get('excluded', []))} entries; qualification.json listed: {'qualification.json' in files}; outputs/bundle listed: {sum(k.startswith('outputs/bundle/') for k in files)} files; generation/result.json, pools.json listed: {'generation/result.json' in files}, {'generation/pools.json' in files}")
# A2 cases on the analysis stage (re-run in a copy of the run directory, so the first run's records stay)
import shutil
def fresh_run(tag):
    rr = base / f"run_{tag}"
    shutil.rmtree(rr, ignore_errors=True); shutil.copytree(run, rr)
    for f in ("stages/analysis.complete.json", "analysis/manifest.json", "qualification.json"): (rr / f).unlink(missing_ok=True)
    return rr
def launch_in(rr, st):
    # the plan names `run`; to keep the plan, swap directories for the duration of the launch
    tmp = base / "run_hold"; os.rename(run, tmp); os.rename(rr, run)
    try: return launch(st)
    finally: os.rename(run, rr); os.rename(tmp, run)
def ps_start(pid): return subprocess.run(["ps", "-o", "lstart=", "-p", str(pid)], capture_output=True, text=True).stdout.strip() or None
sleeper = subprocess.Popen([py, "-c", "import time; time.sleep(120)"])
time.sleep(0.5)
cases = [
    ("dead pid, start recorded", {"pid": 999999, "pid_start": "Mon Jan  1 00:00:00 2000"}),
    ("live pid reused (start time differs)", {"pid": sleeper.pid, "pid_start": "Mon Jan  1 00:00:00 2000"}),
    ("live pid, no start time recorded", {"pid": sleeper.pid}),
    ("genuinely live (pid and its real start time)", {"pid": sleeper.pid, "pid_start": ps_start(sleeper.pid)}),
]
for label, rec in cases:
    rr = fresh_run("a2")
    (rr / "stages").mkdir(exist_ok=True)
    marker = rr / "stages/analysis.running.json"
    marker.write_text(json.dumps({"stage": "analysis", "mode": "registered", "start_utc": "x", "start_epoch": time.time() - 30, **rec}))
    rc, err = launch_in(rr, "analysis")
    killed = [e for e in json.loads((rr / "charged_ledger.json").read_text())["entries"] if e.get("worker") == "killed-process-lower-bound"]
    print(f"[2] {label}: exit {rc} {err}; charged as killed: {[round(e['seconds']) for e in killed]}; marker left: {marker.is_file()}")
sleeper.kill(); sleeper.wait(timeout=30)
```

`Astra review: NOT_PERFORMED`. Claude review is not Astra review. This audit is not human approval.
