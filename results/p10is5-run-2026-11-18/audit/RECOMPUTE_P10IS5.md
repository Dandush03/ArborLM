# P10-I-S5 registered run: independent recomputation (ADR-0028, engineering part), 2026-11-19

**Auditor:** `arbor-auditor` subagent, model Claude Opus 5.5 (`claude-opus-5-5`). I wrote none of the study's code and none of its analysis. This is independent engineering evidence; it is not Astra validation and not a human approval. `Astra review: NOT_PERFORMED`.
**Object:** run directory `/Users/daniellaloush/dandush03/ArborLM/experiments/P10IS5-run-20261118` (read-only), freeze commit `45a2c84ec28ccd1f2807c1eb363e1ba4bbbb196f`, Decision 2 commit `3a64e7c` in worktree `agent-a71d1c708f3f74022` (read with `git show`, `git log`, `git diff`, `git status` only). The SSD files under `/Users/daniellaloush/ArborLM-ssd.noindex` were not read, written or deleted.

## Verdict

**REPRODUCED WITH CORRECTIONS.** Every registered label and every number of `analysis.json` and `REPORT.md` is reproduced by my own code from the raw pass and block records: **963 quantities compared with `analysis.json`, largest difference 0 (bit-equal)**; **839 numbers of `REPORT.md` compared, 0 differences beyond the printed rounding**. The run is the frozen code, the prediction is the one stage P wrote after Decision 2, all 120 passes are exact, all five blocks are valid by the frozen figures, the spare was unused, there was no pollution and no rebuild. The corrections (section 5) are disclosures the registered report lacks, not changes of any label: the first-request maxima, the loose load ceiling, the background VM, two quiet-related facts of M and of block 5.

| Line | Registered (frozen code) | Recomputed |
|---|---|---|
| EQ-A | BYTES CONFIRMED EXACTLY, 120 passes | BYTES CONFIRMED EXACTLY: 120 of 120 passes counter = 16,384 × pages, 0 bytes written, 3,428,843,520 B read in all |
| EQ-B | CONTIGUOUS REQUEST CHEAPER PER PAGE, m_t 0.10, cheaper 5 of 5 | the same: ρ(3) = 0.444, 0.377, 0.444, 0.442, 0.430 (all ≤ 0.90); cheaper 5, dearer 0, proportional 0 |
| EQ-D | COST TABLE REGISTERED, HARNESS-LIMITED at (8,1), (16,1), (16,3), (32,1), (32,3) | the same; 5 valid repeats; largest CV 12.7 % at (32, 3) |
| Scientific | SCIENTIFIC NOT EVALUABLE (PREREQUISITES NOT MET) | not recomputed: a registered constant with its two reasons, printed in its own section |

## Environment and commands

macOS 27.2.1 arm64; my scripts run in one process each, under `timeout`, with no network: `recompute.py` with the torch 2.8.0 of the earlier audit environment (`/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/audit-p10is5/code/.venv/bin/python -I`, used only for `torch.randperm` and `torch.randint` to rebuild the tiling and sample tiles; no `studies.*` import), `colima_check.py` with the system `python3 -I` (standard library). Scripts and outputs: `/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/p10is5_recompute/` (`recompute_out.json`, `colima_check_out.txt`). I did not open `studies/p10is5/analysis.py` or `report.py` for this recomputation; no difference needed explaining.

```
timeout 900 .../audit-p10is5/code/.venv/bin/python -I recompute.py /Users/daniellaloush/dandush03/ArborLM/experiments/P10IS5-run-20261118 \
    /Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a71d1c708f3f74022 45a2c84ec28ccd1f2807c1eb363e1ba4bbbb196f recompute_out.json
timeout 300 python3 -I colima_check.py /Users/daniellaloush/dandush03/ArborLM/experiments/P10IS5-run-20261118
```

## 1. The numbers

- **Statistics** by ruling 10 written afresh: nearest-rank percentiles (rank ⌈q·n⌉), median = rank ⌈n/2⌉, CV with the n − 1 standard deviation over the mean; pooled = all requests of a cell over its valid repeats; pages per second = pages / `wall_ns`.
- **EQ-A:** for each of the 120 pass records, counter bytes = 16,384 × pages (= predicted bytes), `counter_end − counter_start` = counter bytes, written bytes 0, `parity_ok` true with 0 bad pages, memory guard not exceeded, attempt 1, role regular. 0 failures. No `.started` marker without a record (no interrupted pass).
- **Request lists from my own tiling** (ruling 3: `torch.randperm(4096)` seeded 287001, dealt repeat → k → s, 7/20/20/64 tiles; ruling 4: segment order seeded by SHA-256(`p10is5|order|<seed>|<k>|<s>`)): **0 mismatches** against the prediction file for all 144 passes (spare included) and **0 mismatches** against the `request_list` of all 120 pass records.
- **Prediction file:** SHA-256 `5abd4917…540c` equals `prediction_manifest.json`; every pass's `expected_digest` equals my digest of its page hashes in that file (0 mismatches). I regenerated 24 tiles of the file by ruling 1 (`torch.randint` from SHA-256(`p10is5|store|280101|<t>`), big-endian modulo 2⁶³) and compared 1,508 page hashes with the prediction: **0 differ**. **Time order:** Decision 2 committed 21:33:02 −0500; prediction and manifest written 21:33:32; E2's quiet check before the cold check at 02:43:55Z (21:43:55 local); cold check 4,294,967,296 B counted for 4,294,967,296 B, COLD; first block from 02:44:34Z. So P wrote the prediction after Decision 2 and before any E2 read.
- **EQ-B:** c_r(1) median, p90, p99, maximum per repeat and pooled, ρ_r(3), ρ_r(8), ρ_r(64): all equal to `analysis.json`. Label by the registered rule at m_t = 0.10: CHEAPER (5 of 5). The decision is far from its margin: the largest ρ(3) is 0.444 against the threshold 0.90.
- **EQ-D:** for the 24 cells, per repeat the median, p90, p99, maximum and pages per second (600 values), and per cell the pooled median, median of medians, range, CV, median pages per second, E2's own h(k) and the HARNESS-LIMITED tag (h(k) > ¼ of the pooled median): all equal. Tags: (8,1), (16,1), (16,3), (32,1), (32,3).
- **Arithmetic-only table:** for k = 1, 2, 4, 8, 16, 32: ⌈2/min(k,2)⌉ × L(min(k,2), 3) and ⌈6/k′⌉ × L(k′, 1) with k′ = 1, 2, 4, 4, 4, 4: 199.7 / 454.8, 101.8 / 270.4, then 101.8 / 187.2 for k ≥ 4 µs; equal.
- **Count:** 963 quantities compared with `analysis.json` (EQ-B 46, EQ-D 24 × 8 cell values + 600 per-repeat values + 24 tags, arithmetic 12, pages per second of the 120 passes), largest relative difference 0.0; 839 numbers parsed from `REPORT.md` tables, 0 differences beyond rounding (0.1 µs, 0.1 %, 0.001 for ρ, 1 page/s).

## 2. Validity and identity

- **Blocks:** five regular blocks, each `complete`, 24 pass keys, 24 distinct cells, every counter exact. Quiet at start and end re-evaluated by my own code against the **frozen** ceilings (load 3.03 + 0.5 = 3.53; read 64,915 B/s; write 514,886 B/s; read 6.49 ops/s; write 52.07 ops/s; HIDIdleTime ≥ 600 s; no other study process; AC power, no low power, no thermal warning): all ten readings pass and agree with the recorded `ok`. Readings (start / end): loads 1.73/1.59, 1.88/1.30, 1.12/1.51, 1.56/0.87, 1.14/1.20; write B/s 149,256–186,795; read B/s 3,814–18,521; read ops ≤ 3.6/s; write ops ≤ 21.7/s; HIDIdleTime 19,649–21,936 s. **5 valid repeats.**
- **State:** COMPLETE; spare unused (`spare_used` null; no repeat-6 record); pollutions 0; rebuilds 0; quiet sessions failed 0; no engineering stop; one cold check, COLD, not rebuilt.
- **Config against records:** at the freeze commit `[fixed_after_r1_and_m]` and `[caps]` are non-provisional; load_p95 3.03 and the four rate figures equal R1's `idle_figures` exactly; m_t 0.10 and timing_spread false equal M's margin; m_t by the rule from M's CV_R 0.01261: max(0.10, 0.0252) = 0.10. R1 outcome R1 PASSED; M outcome MARGIN DETERMINED.
- **Plan and freeze:** SHA-256 of `studies/p10is5/freeze/plan.json` at the freeze commit = `3ee2a47016705bb7b6f5348c49215f1fb0d637fdcf26b538d5dd4dc8e4bee2ca` = the freeze record's `plan_file_sha256` = K's `candidate.plan_file_sha256`; K COMPLETE on every stage, caps and figures not provisional; the freeze record's rehearsal hash equals `K/k.json` now. The plan's R1 and M record hashes equal the files now; its run directory is this one.
- **Frozen code:** every one of the plan's `frozen_files` hashes equals the file at the freeze commit (0 mismatches). One commit after the freeze, `3a64e7c` (Decision 2), changing only `results/p10is5-freeze-2026-11-18/DECISION_2.md`; `git status` of the worktree is clean now. (A file changed during E2 would have refused every pass worker with exit 75; no pass record is missing.)

## 3. Ledgers

- **Charged hours** (`hours_ledger.json`, grouped as the code groups them): rehearsal (R0 15.6 s + R1 18.7 s + M 125.8 s + K 128.2 s) = **288.4 s of 560.5 s**; e1 (E1 8.9 s + P 5.8 s) = **14.8 s of 600.1 s**; e2 **166.2 s of 800.3 s**; total **469.3 s of 1,960.6 s** (0.130 h, as the report prints). Waiting for quiet and the cold waits are not charged, by design; the analysis and report stages are not charged (seconds).
- **Bytes written:** **5,494,538,240 B of 10,000,000,000 B (54.9 %)** = R0's probes 58,720,256 + control file 67,108,864 + rehearsal file 1,073,741,824 + the file 4,294,967,296: exactly the planned total, no rebuild. Record files are tallied separately (28,096,760 B, printed in the report, not charged).

## 4. What weakens the result

**(a) The quiet-load ceiling (3.53).** R1's sixty idle loads fell from 3.64 to 1.49 (median 1.54); the first samples, taken while an unrelated test run's load decayed, set the 95th percentile at 3.03. Re-deriving the figures from samples 10–59 only (descriptive, not a registered rule): load p95 1.82 (ceiling 2.32), read 31,400 B/s, write 514,886 B/s, read 6.5 ops/s, write 51.9 ops/s. **Every E2 block reading also passes these stricter figures** (highest load 1.88, highest read rate 18,521 B/s, write rates and ops unchanged in relation). So the loose ceiling admitted no E2 block that a settled window would have refused. It stays a disclosure, and the window was rightly not retaken.

**(b) The Colima VM (about 20:31–22:44 local = 01:31–03:44Z).** Times from the block records: M ran 01:13–01:40Z (blocks 1–4 before the VM, block 5 at 01:38–01:40Z), K 02:15–02:32Z, E2 02:44–03:22Z: **all of K, E1, P and E2 ran with the VM up**. Evidence:
- **It is visible once, and the quiet rule caught it:** M's block 5 ended **not quiet** (`failed: ['disk_activity']`): write 34.3 MB/s and read 2.15 MB/s in the 30 s after the block, which is the VM's start-up. During E2 the VM's steady activity is not distinguishable: E2's block write rates (149–187 KB/s) lie between M's pre-VM block readings (99–336 KB/s) and K's (162–248 KB/s), all far under the 515 KB/s ceiling, and above R1's idle median of 129 KB/s; loads 0.87–1.88 against M's 1.12–2.16 before the VM.
- **The ~2.6 ms maxima are not the VM.** In 19 of the 20 depth-1 passes of E2 the maximum is request 0, the first request of the pass process, at 2.60–2.94 ms; M's passes **before the VM** show the same, 19 of 20 at request 0, 2.64–3.05 ms, and K the same. It is a first-request cost of each pass process (the first read on fresh descriptors), present with and without the VM. Requests above 2 ms: E2 1,401 of 30,720 (mostly at depths 16–32 and size 64, where queueing makes them expected), M 1,073 of 7,680, K 1,093 of 7,680.
- **Timing spread:** at depth 1 the CV of the per-repeat medians is 6.9 % (1 page), 2.0 % (3), 6.4 % (8), 1.2 % (64) in E2, against 1.3 / 1.1 / 2.0 / 2.4 % in M and 1.2 / 5.0 / 2.1 / 5.2 % in K (K also with the VM). E2's larger spread at 1 page comes from repeat 2 (86.9 µs against 73.4–78.4 µs) and at 8 pages from a two-level pattern (125 µs in repeats 1 and 4, about 140 µs in 2, 3 and 5). With no E2 block outside the VM period there is no within-E2 comparison, and K's spread under the VM is not uniformly larger than M's; **I find no evidence that the VM moved a registered label, and I cannot exclude that it added spread to EQ-D's figures.** EQ-A is unaffected by construction (a per-process counter); EQ-B's label is far from its margin (ρ(3) ≤ 0.444 against 0.90) and would not change under any plausible disturbance.
- **What the report should say:** a non-study VM (Colima, about 40–70 % of one core and some disk activity, by the lead's observation) ran throughout K, E1, P and E2. It is not a process of another study by the registered markers, so the quiet rule could not exclude it. Every block's readings passed the frozen ceilings and also the stricter ceilings above. EQ-A and EQ-B are not sensitive to it. EQ-D's latencies and pages per second describe the device **with that background load present**, and their repeat spread may include it.

**Further facts the report does not state:**
- **(c) Block 5 waited.** Its start reading failed twice (`attempts: 3`), so it began 03:19:40Z, 21 min after block 4 ended (02:58:09Z). Which condition failed is **not recorded** (the gate keeps only the count). The block's own readings at start and end passed.
- **(d) M's block 5 was not quiet at its end**, and M's record lists no invalid block (`invalid_blocks_recorded_not_replaced` lists only incomplete blocks). M's CV_R, by the lead's ruling, uses every counter-exact pass; without block 5, CV_R is about 0.012 and m_t stays at its floor of 0.10. No effect on any label.
- **(e) Maxima and p99:** at n = 64 (s = 64) the nearest-rank p99 is the maximum, so the p99 column of every 64-page cell is the first-request cost too; at n = 160 (s = 8) p99 is the second-largest request (for example 2,214.5 µs at (1, 8) repeat 2).
- **(f) E2's depth-1 medians (75.8 µs pooled for one page) are lower than M's and K's (about 98 µs).** These are different files (the 4 GiB file against the 1 GiB rehearsal file) and different n; the report makes no comparison and should make none.

## 5. Corrections for the outcome record (the registered report is not edited)

1. Add the disclosure of the Colima VM (4b), with its times, and the statement of which lines it can and cannot affect.
2. Add the load-ceiling disclosure (Decision 2 item 2), with the descriptive check that every E2 block also passes ceilings derived from the settled part of R1's window (4a).
3. State that the maxima (and the p99 of the 64-page cells, and the upper tail at n = 160) are dominated by the first request of each pass process, seen equally before the VM, and are a harness effect, not a steady-state device latency (4b, 4e).
4. State that block 5 began after two failed quiet readings, whose failing condition was not recorded (4c).
5. State that M's block 5 was not quiet at its end and that M's record does not list it, with no effect on m_t (4d).
6. No number, label or table entry needs changing.

## Scripts, verbatim

### recompute.py

```python
"""Independent recomputation of the P10-I-S5 registered run (ADR-0028), by the arbor-auditor. Written from the ADR and the raw records only:
it does NOT import studies.p10is5 (no analysis, report or layout code). Reads the run directory and, read-only, the frozen worktree via `git show`.
Usage: python recompute.py <run_dir> <worktree> <freeze_commit> <out_json>"""
import hashlib, json, math, os, re, subprocess, sys
import torch

RUN, WT, F, OUT = sys.argv[1:5]
PAGE, TP = 16384, 64
SIZES, DEPTHS = (1, 3, 8, 64), (1, 2, 4, 8, 16, 32)
GRID = [(k, s) for k in DEPTHS for s in SIZES]
N = {1: 400, 3: 400, 8: 160, 64: 64}
TL = {1: 7, 3: 20, 8: 20, 64: 64}
res = {"checks": {}, "diffs": []}
cmp_count = [0]
maxdiff = {"rel": 0.0, "where": None}

def J(p): return json.load(open(os.path.join(RUN, p)))
def git(*a): return subprocess.run(["git", "-C", WT, *a], capture_output=True, check=True).stdout
def sha(b): return hashlib.sha256(b).hexdigest()
def nr(v, q):  # nearest rank, ruling 10
    s = sorted(v); r = max(1, math.ceil(q * len(s) - 1e-12)); return float(s[min(r, len(s)) - 1])
def med(v): return nr(v, 0.5)
def cv(v):
    n = len(v); m = sum(v) / n
    return math.sqrt(sum((x - m) ** 2 for x in v) / (n - 1)) / m
def seed_of(t): return int.from_bytes(hashlib.sha256(t.encode()).digest()[:8], "big") % 2**63
def compare(name, mine, theirs, tol_rel=1e-9, tol_abs=1e-6):
    cmp_count[0] += 1
    if theirs is None or mine is None:
        if theirs != mine: res["diffs"].append([name, mine, theirs])
        return
    d = abs(float(mine) - float(theirs)); rel = d / max(abs(float(theirs)), 1e-12)
    if rel > maxdiff["rel"]: maxdiff.update(rel=rel, where=name, mine=mine, theirs=theirs)
    if d > tol_abs and rel > tol_rel: res["diffs"].append([name, mine, theirs])

# ---------- frozen inputs ----------
cfg_txt = git("show", f"{F}:configs/p10is5_ssd.toml").decode()
import tomllib
cfg = tomllib.loads(cfg_txt)
fx = cfg["fixed_after_r1_and_m"]
plan_bytes = git("show", f"{F}:studies/p10is5/freeze/plan.json")
plan = json.loads(plan_bytes)
frec = json.loads(git("show", f"{F}:studies/p10is5/freeze/freeze_record.json"))
res["checks"]["plan_sha256_at_freeze"] = sha(plan_bytes)
res["checks"]["freeze_record_plan_sha"] = frec["plan_file_sha256"]
k = J("K/k.json"); res["checks"]["K_candidate"] = k["candidate"]; res["checks"]["K_provisional"] = [k.get("caps_provisional"), k.get("figures_provisional")]
res["checks"]["K_stages"] = {n: v["status"] for n, v in k["stages"].items()}
res["checks"]["freeze_record_rehearsal_sha_vs_K_file"] = [frec["rehearsal"]["sha256"], sha(open(os.path.join(RUN, "K/k.json"), "rb").read())]
r1 = J("r1/r1.json"); m = J("M/m.json")
res["checks"]["config_vs_records"] = {
    "provisional": [fx["provisional"], cfg["caps"]["provisional"]],
    **{key: [fx[key], r1["idle_figures"][key]] for key in ("load_p95", "read_bytes_per_s_p95", "write_bytes_per_s_p95", "read_ops_per_s_p95", "write_ops_per_s_p95")},
    "m_t": [fx["m_t"], m["summary"]["margin"]["m_t"]], "timing_spread": [fx["timing_spread"], m["summary"]["margin"]["timing_spread"]],
    "R1_outcome": r1["outcome"], "M_outcome": m["outcome"], "M_cv_r": m["summary"]["cv"]["cv_r"],
}
# m_t from M's cv_r by the rule
res["checks"]["m_t_by_rule"] = max(cfg["thresholds"]["m_floor"], cfg["thresholds"]["m_cv_multiple"] * m["summary"]["cv"]["cv_r"])
# plan's records hash vs files now
res["checks"]["plan_records_hash_now"] = {n: [ref["sha256"] == sha(open(ref["path"], "rb").read()), ref["path"]] for n, ref in plan["records"].items()}
res["checks"]["plan_run_dir"] = plan["run_dir"]
# frozen file hashes in the plan vs the tree at F
ls = git("ls-tree", "-r", "--name-only", F, "--", "studies/p10is5").decode().split()
bad = []
for path, h in plan["frozen_files"].items():
    try:
        if sha(git("show", f"{F}:{path}")) != h: bad.append(path)
    except subprocess.CalledProcessError:
        bad.append(path + " (absent)")
res["checks"]["plan_frozen_files_vs_freeze_commit_mismatches"] = bad
res["checks"]["commits_after_freeze"] = git("log", "--format=%h %ci %s", f"{F}..HEAD").decode().strip().splitlines()
res["checks"]["files_changed_after_freeze"] = git("diff", "--name-only", F, "HEAD").decode().split()
res["checks"]["worktree_status_now"] = git("status", "--porcelain").decode().splitlines()

# ---------- my own request lists (rulings 3, 4) ----------
seeds = cfg["seeds"]
perm = torch.randperm(4096, generator=torch.Generator().manual_seed(int(seeds["tile_assignment"]))).tolist()
dealt, pos = {}, 0
for r in range(1, 7):
    for kk in DEPTHS:
        for s in SIZES:
            dealt[(r, kk, s)] = perm[pos:pos + TL[s]]; pos += TL[s]
rseed = {i + 1: v for i, v in enumerate(seeds["request_order"])}; rseed[6] = seeds["spare_request_order"]
def my_pass(r, kk, s):
    segs = [(t, i) for t in dealt[(r, kk, s)] for i in range(64 // s)]
    order = torch.randperm(len(segs), generator=torch.Generator().manual_seed(seed_of(f"p10is5|order|{rseed[r]}|{kk}|{s}"))).tolist()[:N[s]]
    return [[j, j % kk, (segs[x][0] * TP + segs[x][1] * s) * PAGE, s * PAGE] for j, x in enumerate(order)]

# ---------- prediction ----------
pred_path = os.path.join(RUN, "E2/prediction.json")
pred_bytes = open(pred_path, "rb").read()
man = J("E2/prediction_manifest.json")
res["checks"]["prediction_sha_vs_manifest"] = [sha(pred_bytes), man["sha256"]]
pred = json.loads(pred_bytes)
mism = 0
for r in range(1, 7):
    for kk, s in GRID:
        pp = pred["passes"][f"r{r}|k{kk}|s{s}"]
        mism += (pp["requests"] != my_pass(r, kk, s)) + (pp["predicted_bytes"] != N[s] * s * PAGE)
res["checks"]["prediction_vs_my_enumeration_mismatches"] = mism
# page hashes: regenerate a sample of tiles (ruling 1) and compare with the prediction's page hashes
store_seed = int(seeds["store_contents"])
tile_hash = {}
for r in range(1, 7):
    for kk, s in GRID:
        pp = pred["passes"][f"r{r}|k{kk}|s{s}"]
        for (j, th, off, ln), hs in zip(pp["requests"], pp["page_sha256"]):
            for i, h in enumerate(hs):
                tile_hash[off // PAGE + i] = h
import random
rng = random.Random(937777)
sample_tiles = rng.sample(sorted({p // TP for p in tile_hash}), 24)
bad_pages = checked = 0
for t in sample_tiles:
    g = torch.Generator().manual_seed(seed_of(f"p10is5|store|{store_seed}|{t}"))
    b = bytes(torch.randint(0, 256, (1048576,), dtype=torch.uint8, generator=g).tolist())
    for i in range(TP):
        p = t * TP + i
        if p in tile_hash:
            checked += 1; bad_pages += sha(b[i * PAGE:(i + 1) * PAGE]) != tile_hash[p]
res["checks"]["prediction_page_hashes_regenerated"] = {"tiles": len(sample_tiles), "pages_checked": checked, "differ": bad_pages}

# ---------- passes and blocks ----------
passes = {}
for fn in sorted(os.listdir(os.path.join(RUN, "E2/passes"))):
    if fn.endswith(".json"):
        p = J("E2/passes/" + fn); passes[p["key"]] = p
blocks = [J("E2/blocks/" + fn) for fn in sorted(os.listdir(os.path.join(RUN, "E2/blocks")))]
res["checks"]["n_pass_records"] = len(passes)
res["checks"]["started_markers_without_record"] = [fn for fn in os.listdir(os.path.join(RUN, "E2/passes")) if fn.endswith(".started") and not os.path.exists(os.path.join(RUN, "E2/passes", fn[:-8] + ".json"))]
eqa_fail, req_mism, dig_mism, wall_bad = [], 0, 0, 0
for key, p in passes.items():
    if p["counter_bytes"] != N[p["s"]] * p["s"] * PAGE or p["predicted_bytes"] != N[p["s"]] * p["s"] * PAGE or p["written_bytes"] != 0 or p["counter_end"]["bytes_read"] - p["counter_start"]["bytes_read"] != p["counter_bytes"]:
        eqa_fail.append(key)
    req_mism += p["request_list"] != my_pass(p["repeat"], p["k"], p["s"])
    exp = pred["passes"][f"r{p['repeat']}|k{p['k']}|s{p['s']}"]["page_sha256"]
    h = hashlib.sha256()
    for row in exp:
        for x in row: h.update(x.encode())
    dig_mism += h.hexdigest() != p["expected_digest"]
    t1 = [a + b for a, b in zip(p["t0_ns"], p["latency_ns"])]
    if p["wall_ns"] < max(t1) - min(p["t0_ns"]): wall_bad += 1
    compare(f"pps {key}", p["pages"] / (p["wall_ns"] / 1e9), p["pages_per_second"])
    if not (p["parity_ok"] is True and p["parity_bad_pages"] == 0 and not p["memory_guard_exceeded"] and p["counter_status"] == "OK" and p["attempt"] == 1 and p["role"] == "regular"): eqa_fail.append(key + " (flags)")
res["checks"]["EQ-A"] = {"passes": len(passes), "failing": eqa_fail, "label": "BYTES CONFIRMED EXACTLY" if not eqa_fail else "BYTES NOT CONFIRMED", "bytes_read_total": sum(p["counter_bytes"] for p in passes.values())}
res["checks"]["request_lists_vs_my_enumeration_mismatches"] = req_mism
res["checks"]["expected_digest_vs_prediction_mismatches"] = dig_mism
res["checks"]["wall_shorter_than_request_span"] = wall_bad

# quiet validity by the frozen figures
ceil = {"load": fx["load_p95"] + cfg["quiet"]["load_margin"], "read_bytes": fx["read_bytes_per_s_p95"], "write_bytes": fx["write_bytes_per_s_p95"], "read_ops": fx["read_ops_per_s_p95"], "write_ops": fx["write_ops_per_s_p95"]}
res["checks"]["ceilings"] = ceil
qrows, valid = [], []
for b in blocks:
    ok = True
    row = {"block": b["key"], "complete": b["complete"], "n_pass_keys": len(b["pass_keys"]), "cells": len({(passes[x]["k"], passes[x]["s"]) for x in b["pass_keys"]}), "start_attempts": b["quiet_start"].get("attempts")}
    for side in ("quiet_start", "quiet_end"):
        q = b[side]; rd = q["readings"]; a = rd["activity"]
        cond = rd["load"] <= ceil["load"] and all(a[x] <= ceil[x] for x in ("read_bytes", "write_bytes", "read_ops", "write_ops")) and rd["other_processes"] == [] and rd["hid_idle_seconds"] >= 600 and rd["power"] == {"low_power": False, "on_ac": True, "thermal_warning": False}
        row[side] = {"utc": q["utc"], "load": rd["load"], **{x: round(a[x], 1) for x in ("read_bytes", "write_bytes", "read_ops", "write_ops")}, "hid": round(rd["hid_idle_seconds"]), "mine_ok": cond, "recorded_ok": q["ok"]}
        ok &= cond and q["ok"]
    ok &= b["complete"] and row["cells"] == 24 and all(passes[x]["counter_bytes"] == passes[x]["predicted_bytes"] for x in b["pass_keys"])
    row["valid"] = ok
    qrows.append(row)
    if ok: valid.append(b)
res["blocks"] = qrows
st = J("E2/state.json"); res["checks"]["state"] = {k2: st[k2] for k2 in ("status", "spare_used", "rebuilds", "pollutions", "quiet_sessions_failed", "engineering_stop")}
res["checks"]["cold_checks"] = [[c["first"]["counter_bytes"], c["first"]["bytes"], c["outcome"], c["rebuilt"]] for c in J("E2/cold_checks.json")["checks"]]

# ---------- EQ-B, EQ-D, arithmetic ----------
cell = {}
for bi, b in enumerate(valid, 1):
    for x in b["pass_keys"]:
        p = passes[x]; cell.setdefault((p["k"], p["s"]), {})[p["repeat"]] = p
an = J("analysis/analysis.json")["result"]
mt = fx["m_t"]
rho3, eqb = [], {}
for r, p in sorted(cell[(1, 1)].items()):
    c1 = med(p["latency_ns"])
    st1 = {"median": c1, "p90": nr(p["latency_ns"], .9), "p99": nr(p["latency_ns"], .99), "max": max(p["latency_ns"])}
    rho = {s: med(cell[(1, s)][r]["latency_ns"]) / (s * c1) for s in (3, 8, 64)}
    eqb[r] = {**st1, "rho": rho}; rho3.append(rho[3])
    th = an["EQ-B"]["per_repeat"][str(r)]
    for q in ("median", "p90", "p99", "max"): compare(f"EQ-B r{r} c1 {q}", st1[q], th["c1"][q])
    for s in (3, 8, 64): compare(f"EQ-B r{r} rho({s})", rho[s], th["rho"][str(s)])
pool = [x for p in cell[(1, 1)].values() for x in p["latency_ns"]]
for q, v in (("median", med(pool)), ("p90", nr(pool, .9)), ("p99", nr(pool, .99)), ("max", max(pool))): compare(f"EQ-B pooled {q}", v, an["EQ-B"]["pooled_c1"][q])
ch, de, pr = sum(x <= 1 - mt for x in rho3), sum(x >= 1 + mt for x in rho3), sum(abs(x - 1) < mt for x in rho3)
label_b = "CONTIGUOUS REQUEST CHEAPER PER PAGE" if ch >= 4 else "CONTIGUOUS REQUEST DEARER PER PAGE" if de >= 4 else "COST PROPORTIONAL TO PAGES" if pr >= 4 else "NOT SEPARATED AT MARGIN"
if len(valid) < 4 or fx["timing_spread"]: label_b = "ENGINEERING NOT EVALUABLE"
res["EQ-B"] = {"label": label_b, "counts": [ch, de, pr], "rho3": rho3, "rho3_max": max(rho3), "margin": mt, "per_repeat": {r: {**{q: v[q] for q in ("median", "p90", "p99", "max")}, "rho": v["rho"]} for r, v in eqb.items()}}
harness = {int(kk): v for kk, v in J("E2/harness_figure.json")["figure"].items()}
eqd = {}
for kk, s in GRID:
    reps = cell[(kk, s)]
    meds = [med(p["latency_ns"]) for _, p in sorted(reps.items())]
    pooled = [x for p in reps.values() for x in p["latency_ns"]]
    pm = med(pooled)
    h = harness[kk]["median_ns"] if harness[kk]["status"] == "MEASURED" else None
    tag = h is not None and h > cfg["thresholds"]["harness_limited_fraction"] * pm
    row = {"pooled_median": pm, "median_of_medians": med(meds), "range": [min(meds), max(meds)], "cv": cv(meds), "pps_median": med([p["pages"] / (p["wall_ns"] / 1e9) for p in reps.values()]), "h": h, "limited": tag, "per_repeat": {}}
    th = an["EQ-D"]["rows"][f"k{kk}|s{s}"]
    for q, t in (("pooled_median", "pooled_median"), ("median_of_medians", "median_of_medians"), ("cv", "cv"), ("pps_median", "pages_per_second_median"), ("h", "harness_ns")): compare(f"EQ-D k{kk} s{s} {q}", row[q], th[t])
    compare(f"EQ-D k{kk} s{s} range0", row["range"][0], th["range"][0]); compare(f"EQ-D k{kk} s{s} range1", row["range"][1], th["range"][1])
    cmp_count[0] += 1
    if tag != th["limited"]: res["diffs"].append([f"EQ-D k{kk} s{s} tag", tag, th["limited"]])
    for r, p in sorted(reps.items()):
        L = p["latency_ns"]; pr_ = {"median": med(L), "p90": nr(L, .9), "p99": nr(L, .99), "max": max(L), "pps": p["pages"] / (p["wall_ns"] / 1e9)}
        row["per_repeat"][r] = pr_
        tr = th["per_repeat"][str(r)]
        for q, t in (("median", "median"), ("p90", "p90"), ("p99", "p99"), ("max", "max"), ("pps", "pages_per_second")): compare(f"EQ-D k{kk} s{s} r{r} {q}", pr_[q], tr[t])
    eqd[f"k{kk}|s{s}"] = row
res["EQ-D"] = {"label": "COST TABLE REGISTERED" if len(valid) >= 4 else "ENGINEERING NOT EVALUABLE", "limited": [c for c, v in eqd.items() if v["limited"]], "cv_max": max((v["cv"], c) for c, v in eqd.items())}
arith = []
for kk in DEPTHS:
    k2 = min(kk, 2); k1 = max(d for d in DEPTHS if d <= min(kk, 6))
    a2 = math.ceil(2 / k2) * eqd[f"k{k2}|s3"]["pooled_median"]; a1 = math.ceil(6 / k1) * eqd[f"k{k1}|s1"]["pooled_median"]
    arith.append([kk, a2, a1])
    th = next(x for x in an["arithmetic"] if x["k"] == kk)
    compare(f"arith k{kk} two3", a2, th["two_3page_ns"]); compare(f"arith k{kk} six1", a1, th["six_1page_ns"])
res["arithmetic"] = arith
res["labels_registered"] = {x: an[x]["label"] for x in ("EQ-A", "EQ-B", "EQ-D", "scientific")}
res["n_valid_mine"] = len(valid)

# ---------- REPORT.md table numbers (rounded to 0.1 us / units) ----------
rep = open(os.path.join(RUN, "report/REPORT.md")).read()
def num(x): return float(x.replace(",", "").replace("%", ""))
rcmp = rdiff = 0
for line in rep.splitlines():
    m1 = re.match(r"\| (\d+) \| (\d+) \| (\d) \| ([\d,.]+) \| ([\d,.]+) \| ([\d,.]+) \| ([\d,.]+) \| ([\d,]+) \|$", line)
    if m1:
        kk, s, r = int(m1[1]), int(m1[2]), int(m1[3]); v = eqd[f"k{kk}|s{s}"]["per_repeat"][r]
        for got, want, unit in ((num(m1[4]), v["median"] / 1e3, .05), (num(m1[5]), v["p90"] / 1e3, .05), (num(m1[6]), v["p99"] / 1e3, .05), (num(m1[7]), v["max"] / 1e3, .05), (num(m1[8]), v["pps"], .5)):
            rcmp += 1; rdiff += abs(got - want) > unit + 1e-9
    m2 = re.match(r"\| (\d+) \| (\d+) \| ([\d,.]+) \| ([\d,.]+) \| ([\d,.]+) to ([\d,.]+) \| ([\d.]+)% \| ([\d,]+) \| ([\d,.]+) \| (HARNESS-LIMITED)? \|$", line)
    if m2:
        kk, s = int(m2[1]), int(m2[2]); v = eqd[f"k{kk}|s{s}"]
        for got, want, unit in ((num(m2[3]), v["pooled_median"] / 1e3, .05), (num(m2[4]), v["median_of_medians"] / 1e3, .05), (num(m2[5]), v["range"][0] / 1e3, .05), (num(m2[6]), v["range"][1] / 1e3, .05), (num(m2[7]), 100 * v["cv"], .05), (num(m2[8]), v["pps_median"], .5), (num(m2[9]), v["h"] / 1e3, .05)):
            rcmp += 1; rdiff += abs(got - want) > unit + 1e-9
        rcmp += 1; rdiff += (m2[10] is not None) != v["limited"]
    m3 = re.match(r"\| (\d) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| ([\d,.]+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \|$", line)
    if m3:
        r = int(m3[1]); v = eqb[r]
        for got, want, unit in ((num(m3[2]), v["median"] / 1e3, .05), (num(m3[3]), v["p90"] / 1e3, .05), (num(m3[4]), v["p99"] / 1e3, .05), (num(m3[5]), v["max"] / 1e3, .05), (num(m3[6]), v["rho"][3], .0005), (num(m3[7]), v["rho"][8], .0005), (num(m3[8]), v["rho"][64], .0005)):
            rcmp += 1; rdiff += abs(got - want) > unit + 1e-9
    m4 = re.match(r"\| (\d+) \| (\d) x L\((\d+), 3\) = ([\d,.]+) \| (\d) x L\((\d+), 1\) = ([\d,.]+) \|$", line)
    if m4:
        kk = int(m4[1]); a = next(x for x in arith if x[0] == kk)
        for got, want in ((num(m4[4]), a[1] / 1e3), (num(m4[7]), a[2] / 1e3)):
            rcmp += 1; rdiff += abs(got - want) > .05 + 1e-9
res["report_md"] = {"numbers_compared": rcmp, "differences_beyond_rounding": rdiff}

# ---------- ledgers ----------
hl = J("hours_ledger.json"); grp = {"R0": "rehearsal", "R1": "rehearsal", "M": "rehearsal", "K": "rehearsal", "E1": "e1", "P": "e1", "E2": "e2", "analysis": "e2"}
by = {}
for e in hl["entries"]: by[grp.get(e["stage"], e["stage"])] = by.get(grp.get(e["stage"], e["stage"]), 0) + e["seconds"]
by_stage = {}
for e in hl["entries"]: by_stage[e["stage"]] = by_stage.get(e["stage"], 0) + e["seconds"]
res["ledgers"] = {"hours_by_group_s": by, "hours_by_stage_s": by_stage, "total_s": sum(by.values()), "caps_s": {x: cfg["caps"][x] * 3600 for x in ("rehearsal_hours", "e1_hours", "e2_hours", "total_hours")},
                  "write_total": sum(e["bytes"] for e in J("write_ledger.json")["entries"]), "write_entries": [[e["label"], e["bytes"]] for e in J("write_ledger.json")["entries"]], "cap": cfg["budget"]["cap_bytes"]}
res["compared_quantities"] = cmp_count[0]; res["largest_relative_difference"] = maxdiff
json.dump(res, open(OUT, "w"), indent=1, default=str)
print(json.dumps({k2: res[k2] for k2 in ("compared_quantities", "largest_relative_difference", "report_md", "labels_registered", "n_valid_mine")}, default=str))
print("DIFFS", res["diffs"][:10])
print(json.dumps(res["checks"], default=str)[:6000])
print(json.dumps({"EQ-B": {k2: res["EQ-B"][k2] for k2 in ("label", "counts", "rho3_max")}, "EQ-D": res["EQ-D"], "ledgers": {k2: res["ledgers"][k2] for k2 in ("hours_by_group_s", "hours_by_stage_s", "total_s", "caps_s", "write_total", "cap")}}, default=str))
for b in res["blocks"]: print(json.dumps(b))
```

### colima_check.py

```python
"""Descriptive evidence on the Colima VM period (20:31-22:44 local = 01:31Z-03:44Z on 2026-11-19): block times, quiet readings and the depth-1 timing of M, K and E2.
Own code; reads the run directory only. Usage: python colima_check.py <run_dir>"""
import json, math, os, sys
RUN = sys.argv[1]
def J(p): return json.load(open(os.path.join(RUN, p)))
def nr(v, q):
    s = sorted(v); r = max(1, math.ceil(q * len(s) - 1e-12)); return s[min(r, len(s)) - 1]
def cv(v):
    n = len(v); m = sum(v) / n; return math.sqrt(sum((x - m) ** 2 for x in v) / (n - 1)) / m
for st in ("M", "K", "E2"):
    blocks = [J(f"{st}/blocks/{f}") for f in sorted(os.listdir(os.path.join(RUN, st, "blocks")))]
    passes = {}
    for f in os.listdir(os.path.join(RUN, st, "passes")):
        if f.endswith(".json"):
            p = J(f"{st}/passes/{f}"); passes[p["key"]] = p
    print(f"== {st}: blocks {[b['quiet_start']['utc'][9:15] + '-' + b['quiet_end']['utc'][9:15] + 'Z' for b in blocks]}")
    print("   loads start/end", [(b["quiet_start"]["readings"]["load"], b["quiet_end"]["readings"]["load"]) for b in blocks])
    print("   write B/s start/end", [(round(b["quiet_start"]["readings"]["activity"]["write_bytes"]), round(b["quiet_end"]["readings"]["activity"]["write_bytes"])) for b in blocks])
    print("   read B/s start/end", [(round(b["quiet_start"]["readings"]["activity"]["read_bytes"]), round(b["quiet_end"]["readings"]["activity"]["read_bytes"])) for b in blocks])
    for s in (1, 3, 8, 64):
        ps = sorted((p for p in passes.values() if p["k"] == 1 and p["s"] == s), key=lambda p: p["repeat"])
        meds = [nr(p["latency_ns"], .5) / 1e3 for p in ps]
        mx = [(round(max(p["latency_ns"]) / 1e3), p["latency_ns"].index(max(p["latency_ns"]))) for p in ps]
        big = [sum(1 for x in p["latency_ns"] if x > 2_000_000) for p in ps]
        print(f"   k1 s{s}: medians_us {[round(x, 1) for x in meds]} CV {cv(meds):.3f}; max_us(index) {mx}; requests >2 ms per pass {big}")
    allbig = sum(1 for p in passes.values() for x in p["latency_ns"] if x > 2_000_000); alln = sum(len(p["latency_ns"]) for p in passes.values())
    firsts = sum(1 for p in passes.values() if p["k"] == 1 and max(p["latency_ns"]) > 2_000_000 and p["latency_ns"].index(max(p["latency_ns"])) == 0)
    print(f"   requests >2 ms: {allbig} of {alln}; depth-1 passes whose max (>2 ms) is request 0: {firsts} of {sum(1 for p in passes.values() if p['k'] == 1)}")
w = J("r1/steps/idle.json") if os.path.exists(os.path.join(RUN, "r1/steps/idle.json")) else None
if w:
    L = w["loads"]; print("== R1 idle window loads: first", L[:5], "last", L[-5:], "min", min(L), "median", nr(L, .5), "p95", nr(L, .95))
    wb = [r["write_bytes"] for r in w["rate_rows"]]; print("   R1 idle write B/s median", round(nr(wb, .5)), "p95", round(nr(wb, .95)))
```
