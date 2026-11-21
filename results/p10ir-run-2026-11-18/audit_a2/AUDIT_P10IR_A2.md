# P10-I-R stage group A2: independent recomputation (ADR-0029 section 10)

Auditor: `arbor-auditor` subagent, model Claude Opus 5.5 (`claude-opus-5-5`), 2026-11-18. This is independent engineering and mathematical evidence. It is **not Astra review and not human approval**. `Astra review: NOT_PERFORMED`.

Inputs: ADR-0029 (sections 5, 7–11, 15, 19, 20); `studies/p10ir/` and `configs/p10ir_routing.toml` at freeze `c712a905` (`git diff c712a90 HEAD -- studies configs src tests` is empty); the run directory `experiments/P10IR-registered-20261118` (gates-a2, a2-train, a2 (the same directory as `A2/` on this case-insensitive APFS volume: one inode), confirm, analysis, a1 for the comparison); P10-S1's attempt-2 run directory; `SEED_REGISTRY.md`; `results/p10ir-freeze-2026-11-18/` and `results/p10ir-rehearsal-measure-2026-11-18/`.

## Environment and commands

- macOS 27.2.1 arm64. JSON-only scripts: system `python3 -B` (Python 3.15.1, standard library). Tensor scripts: the worktree's venv interpreter called directly (`.venv/bin/python -B`, Python 3.12.14, torch 2.8.0, numpy absent), one thread, one interop thread, deterministic algorithms, `PYTHONPATH=<worktree> PYTHONDONTWRITEBYTECODE=1 PYTHONPYCACHEPREFIX=<scratch>/pycache`. Scratch folder: `experiments/_scratch/audit-p10ir-a2/`. `git status --porcelain --ignored` of the worktree was identical before and after the tensor runs (`ignored_before.txt`). No git writes.
- `timeout 900 python3 -B audit_labels_a2.py` -> `audit_labels_a2.out.txt`
- `timeout 900 python3 -B audit_integrity_a2.py` -> `audit_integrity_a2.out.txt`; draw-manifest hashes against the plan -> `draw_manifest_hashes.out.txt`
- `timeout 120 python3 -B audit_margins_a2.py`, `audit_spread_a2.py`, `audit_replicates_a2.py` -> `*.out.txt` (descriptive)
- `timeout 7500 zsh launch_tensors.sh` (8 processes, `xargs -P 6`, each `timeout 7200 .venv/bin/python -B audit_tensors_a2.py <T-OQ|F-OQ> <1|2> <16384|98304>`) -> `tensors_*.json`, `log_*.txt`, `launch_exits.txt` (all exit 0; tree 182 s, flat 34 s each); `timeout 120 python3 -B summarize_tensors_a2.py` -> `summarize_tensors.out.txt`
- `timeout 1800 .venv/bin/python -B audit_route_ties_a2.py T-OQ 2 98304` -> `route_ties_T-OQ_d2_u98304.json`

Failed checker attempts, kept (`failed_attempts.txt`): `audit_labels_a2.py` KeyError (plateau block exists only at RUN); `audit_integrity_a2.py` KeyError (`returncode` absent in some manifests); `audit_route_ties_a2.py` IndexError at v = 64 (`failed_log_route_ties_attempt1.txt`). Each fixed and rerun. One of my own checker definitions produced false "non-tie" flags (see 3).

## 1. Integrity: REPRODUCED

- Manifests gates-a2, a2-train, a2, confirm: COMPLETE, registered, clean, item_errors 0, one history entry each, plan SHA-256 `a52da5fb…` and config `388c16b2…` equal the blobs at `c712a90`; platform macOS 27.2.1 arm64, torch 2.8.0, threads 1/1, deterministic. a2-train 20/20 tasks completed, charged 4,871.49 s; a2 20/20, 2,483.60 s; gates-a2 43.32 s; confirm 0.116 s. Charged seconds equal the stage's wall time (a2-train summed worker-seconds 27,788; a2 12,757).
- Caps: the A2 cap chain recorded at each stage start is 10,800 − charged so far (10,800 / 10,756.68 / 5,885.18 / 3,401.59), so the 3.0 h cap was enforced as a group cap. **A2 group charged 2.055 h of 3.0. A1 group 1.113 h of 6.0. Counting rehearsal 0.386 h of 1.0. Study total 3.554 h of 10.0** (3.921 h if the measuring rehearsal, run on provisional caps, is counted). Bridge training took 1.35 charged hours against ADR §10's 0.87 projection (loaded machine); A2 overall 2.06 against "about 1.5".
- Bridge cells (20): seeds equal the registry and ADR §5: draw d -> set `p10ir-bridge-d`, base 290001 + 100(d − 1), init 330600 + d (330601–330605); every value of the five draw manifests lies in base..base+99, inside 290001–296999, with the index seed base + 60 (290061 … 290461); the five draw manifests hash to the plan's frozen SHA-256s; in the tensor runs, draws 1 and 2 regenerate to their manifests. Per cell, arm, facts, slots, learning rate 0.003, run length (49,152 / 98,304), U_P (8,192 / 16,384) and the full snapshot schedule (including 10,240 for T-OQ 8K/4K) equal the matching P10-S1 cell's train.json (P10-S1 init 2100 + d, set `p10s1-draw-d`). Platform 1/1 threads, deterministic. 185 snapshot files hash to train.json and snapshot.json; all 40 items' checkpoint_identity hashes equal train.json at U_P or the run length.
- Adapter identity gate: passed in the record; own check: the six adapter snapshots (F-OQ and T-OQ 8K/4K d1 i2101 at 512, 1,024, 2,048) have file SHA-256 equal to P10-S1's stored model.pt and its recorded `model_sha256` (`torch.equal` not re-run; file identity implies it).
- Gates-a2: gate 1 (5 manifests regenerated; 0 checkpoints, none exist before training), gate 5 and gate 6 (RESULT: PASS, checker SHA-256 `e4623604…`) passed; none skipped. Per item (40): checkpoint_identity 40, t0_path 20 (all queries, 0 mismatches), t0_counts 20, f0_counts 20, i256_counts 20 (gate 2 as replaced), tv1 on/off 20, T3 and T2 against independent flat 20 each, index rebuild 80: all passed, none skipped or failed. Gate 3 is not applicable to A2 (§10) and was not run.
- A1's analysis.json SHA-256 is `0ea94efe…` (unchanged; equals the committed copy in `results/p10ir-run-2026-11-18/`; modified before confirm.json was written); confirm.json records the same hash.

## 2. A2 labels and R-CONFIRM: REPRODUCED

Own rules (8.1, 8.2, 8.3, 8.4, 9, 10, ruling 1 and ruling 3), i from counts with my own Fano and binomial bound. **4,261 comparisons with confirm.json, 0 differences**: 1,120 read-panel i values (max |Δ| = 0), a_use and accuracy; every replicate's row, P/C/J/H/R tags, CR8 tag and g_P/g_C/g_PC per panel; per-panel retention status and the accuracy version (ruling 3) for T1/T2/T3 and every I64 budget; c* per replicate; cell labels; median c* and share of N; plateau NOT CHECKED with no tag (ruling 4); components, actions, NO READ-TIME CAUSE; R-CONFIRM values and the A1/A2 values they compare; the descriptive means (a_use, i, CR8, testability, index a_use and CR8 per budget).

- Tree: EXACT SEARCH HARMS in 5/5 replicates at all four cell-checkpoints. Distance from the thresholds is large: max g_P/g_C/g_PC ≤ −0.09/−0.10/−0.34 (need ≥ 0.5); i(T0) − i(T2) ≥ 1.04 bits per panel (need ≥ 0.25); max CR8(T0) 0.079.
- Index: INDEX APPROACHES FLAT ONLY ABOVE 512; c* 8K/4K U_P [2048 ×5], 8K/4K RUN [1024 ×5], 32K/16K both [2048 ×5]; at 8K/4K U_P, 1,024 was RESTORED on 3 of 10 replicate-panels (closest to a different c*).
- R-DIAGNOSIS (A2) EVALUABLE, pair (EXACT SEARCH HARMS, INDEX APPROACHES FLAT ONLY ABOVE 512), no action, no banner. A1 components recomputed from A1's cell labels equal A1's record. **R-CONFIRM-TREE: CONFIRMED; R-CONFIRM-INDEX: CONFIRMED.** Ruling 1 did not arise (no CELL-DEPENDENT or CHECKPOINT-DEPENDENT value in either stage).

## 3. Measurements from the bridge tensors (32K/16K, draws 1 and 2, U_P and run length): REPRODUCED WITH NOTE

Own float64 brute force over all N keys for 4 tree checkpoints × 11 reads (T0, T1, T1w, T3, T2, Tv1/4/8 on and off) and 4 flat checkpoints × (F0, I64@512 and I64@2048, seed 298001); the panel pass is P10-S1's, given my selection. 624 comparisons, 26 differences, all at float precision:

- End-task counts exact for 52 of 56 read-checkpoints (T0 and F0 exact everywhere, all index reads exact). T-OQ d2 at 98,304: T1, T3 and Tv8_on differ by 1 correct / 1 useful per panel, T1w by 1 on panel B (14 count differences of 32,768; i changes by about 2e-4 bits; no label effect).
- Cause, diagnosed (`route_ties_…json`): three facts. Facts 3438 and 17308 have 8th/9th selection-score gaps of 2.6e-7 and 1.5e-7 (float ties). Fact 2019 has a **router** tie: the 2nd and 3rd branch scores differ by 2.7e-7 (float64) / 2.4e-7 (float32), so float64 and float32 visit different second branches. My gate-4-style comparison checks only the 8th/9th selection gap, so it flagged this fact as a "non-tie" in T0, T1 and T1w (3 of the 26). This is a limitation of my checker's tie definition, not a defect of the study. The study's float32 path is the reference of record; it equals `S1Memory._top_tree` bit for bit (gate t0_path).
- Fact measures within 3.8e-6 of the records (6 differences above 1e-6: T2 SR8/AM_S d1 U_P; I64@512 CR8/SR8/AM_C/AM_S d1 U_P), pair TV means within 5e-6 (3). Examples: CR8(T0) d1 U_P 0.0157, d1 RUN 0.0061, d2 RUN 0.0060; I64@2048 CR8 0.947 / 0.945. Max weight difference against the study path 2.9e-7 (tolerance 1e-6). Index hashes rebuild equal to the records; float64 candidate sets equal P10-S1's float32 mask on every fact.
- I256@512 was not recomputed from the tensors (A2's I256 gate is its own check against P10-S1's functions).

## 4. A2 against A1 at the primary cells (means over 5 replicates; a_use unless stated)

| | 8K/4K U_P A1 / A2 | 8K/4K RUN A1 / A2 | 32K/16K U_P A1 / A2 | 32K/16K RUN A1 / A2 |
|---|---|---|---|---|
| F0 | 0.948 / 0.949 | 0.996 / 0.996 | 0.916 / 0.917 | 0.992 / 0.991 |
| T0 | 0.469 / 0.493 | 0.769 / 0.773 | 0.401 / 0.411 | 0.697 / 0.703 |
| T1 | 0.340 / 0.353 | 0.515 / 0.521 | 0.332 / 0.341 | 0.529 / 0.536 |
| T1w | 0.417 / 0.436 | 0.681 / 0.687 | 0.371 / 0.381 | 0.633 / 0.640 |
| T3 | 0.384 / 0.402 | 0.589 / 0.598 | 0.293 / 0.298 | 0.408 / 0.409 |
| T2 | 0.064 / 0.064 | 0.062 / 0.062 | 0.039 / 0.039 | 0.033 / 0.034 |
| CR8(T0) | 0.072 / 0.073 | 0.063 / 0.062 | 0.016 / 0.016 | 0.0063 / 0.0063 |
| sweep i(on) v=1,2,4,8 | .58 1.38 1.07 1.00 / .62 1.49 1.15 1.07 | 1.20 3.08 2.16 2.00 / 1.20 3.10 2.22 2.04 | .43 1.06 .81 .66 / .44 1.11 .83 .68 | .84 2.62 1.58 1.18 / .84 2.65 1.60 1.19 |
| I64 a_use 128…2048 | .48 .65 .82 .92 .95 / .48 .65 .82 .92 .95 | .54 .72 .89 .98 1.00 / .54 .72 .89 .98 1.00 | .38 .52 .68 .82 .89 / .38 .52 .69 .82 .90 | .42 .58 .77 .91 .98 / .42 .58 .77 .91 .98 |
| I64 CR8 128…2048 | .48 .64 .80 .94 .995 / .48 .63 .80 .94 .995 | .47 .63 .80 .93 .995 / .47 .63 .80 .93 .995 | .40 .54 .69 .84 .95 / .40 .54 .69 .84 .95 | .40 .53 .69 .84 .94 / .40 .53 .69 .84 .94 |
| c* (median) | 2048 (one 1024) / 2048 | 1024 / 1024 | 2048 / 2048 | 2048 / 2048 |

The replication is close: every A2 − A1 difference in mean a_use is within 0.024 and within about 1 standard error of the replicate spread (largest |t| 1.9, I256@512 at 8K/4K RUN); every read keeps its order (F0 > T0 > T1w > T3 ≈ T1 > T2 ≈ chance); the visit sweep peaks at v = 2 in both; index curves agree to 0.01. Two descriptive differences, neither affecting the reading: A2 is slightly better at the tree reads at U_P (T0 +0.023 at 8K/4K, +0.010 at 32K/16K), and A2's replicate spread is smaller (T0 sd 0.005 vs 0.023 at 32K/16K RUN), because A1's draw 4 is high (0.737 / 0.472). New draws and new initialisation seeds were changed together, so A2 cannot separate data from initialisation variation. The run-length labels in A1 carry TREE STILL LEARNING (5/5); in A2 the plateau is NOT CHECKED (ruling 4), so the replication is of a label on memories that A1 showed were still learning at that length.

## 5. What CONFIRMED licenses, and how the report reads

- **Licensed:** that the A1 component values replicate by row name on five fresh draws with fresh initialisation, at both primary cells and both checkpoints. In row-7 terms: exact search over the tree's own keys and values reads worse than the trained read (T2 near chance), and neither removing the prior (T1) nor removing the hard restriction (T3) closes most of the gap. The index label also replicates: a post-hoc 64-wide k-means index needs more than 512 candidates (1,024–2,048) to be RESTORED. "The re-analysis points to …" can now be said with "and was confirmed on fresh checkpoints".
- **Not licensed:** any statement that the gap *is caused by* a named read-time factor. ADR §10 makes CONFIRMED a **necessary** condition for such a statement, not a sufficient one. The confirmed row (row 7, "EXACT SEARCH HARMS — NOT SEPARABLE AT READ TIME") names no factor: its claim is limited to "exact search selects slots that serve the fact worse than the trained read; the content may be sound for the read it was trained under", and its action is none. Also not licensed: training-time causes; stability at the run length (A1: TREE STILL LEARNING; A2: NOT CHECKED); anything about a trained index or router; anything outside oracle-addressed recall of random facts (§15); that CR8 measures recall of the slots that hold the fact.
- **Reads more favourably than the records support:** (1) `confirm.json` `statement_allowed.caused_by_a_named_factor_at_read_time: true` and REPORT_CONFIRM.md "requires R-CONFIRM-TREE: CONFIRMED. Allowed here: True". `labels.may_say_cause` (labels.py:338–340) tests only `R-CONFIRM-TREE == CONFIRMED` and ignores whether the confirmed row names a factor; with EXACT SEARCH HARMS no causal statement is available. This is the most consequential presentation issue. (2) As in A1, the row is printed as "EXACT SEARCH HARMS" without "— NOT SEPARABLE AT READ TIME" and without its limiting claim (`EXACT_SEARCH_LONG` is never used). (3) The testability note "(near 1: … not testable)" is printed where the share is 0.315, 0.290, 0.098 and 0.062, that is where CANDIDATES was testable and T3 was worse than T0. (4) The confirmation report does not say that A1's run-length tree labels it confirms carry TREE STILL LEARNING.
- **Reads less favourably / inaccurate:** confirm.json's plateau reason "no recorded snapshot series" (analysis.py:334, following ruling 4's "fresh cells have no recorded snapshot series") is factually wrong for the checkpoints. Every bridge cell stores the run/2 snapshot (24,576 at 8K/4K; 49,152 at 32K/16K) on P10-S1's full schedule; they were not evaluated. NOT CHECKED is the registered ruling and stands. Cosmetic: an empty "R-DIAGNOSIS-LOADED" heading is printed.

## 6. Defects of the frozen code

- No defect of the frozen code changed a number or a label in A2 (0 of 4,261 label-side differences; tensor differences at float ties only).
- Record and presentation: `labels.may_say_cause` (above) writes a permission into the registered confirm.json that the ADR's wording does not grant for row 7; the plateau reason string (above); the report items (2) and (3) carried over from A1.
- Naming: the `a2` stage folder and the adapter's `A2/` folder (train cells, draws) are one directory on this case-insensitive volume. The code is consistent on either kind of file system; reviewers should not expect two folders.

PENDING LEAD REVIEW: whether the outcome record should state that "Allowed here: True" does not apply to row 7 (no named factor); whether ruling 4's stated reason should be corrected in the outcome record (run/2 snapshots exist, unevaluated); whether the outcome record should carry A1's TREE STILL LEARNING beside the confirmed run-length labels.

## Scripts (verbatim; appended below by shell from the scratch folder)

### audit_labels_a2.py

```
"""Independent recomputation of P10-I-R stage A2 labels and R-CONFIRM from the a2 item records (auditor's own code).

Adapted from ../audit-p10ir-a1/audit_labels.py (same author). Reads only raw JSON: a2/items/*/read.*.json and item.json,
confirm/confirm.json and analysis/analysis.json (for comparison only). Imports nothing from studies.* or arborlm.*.
Rules written from ADR-0029 text: 8.1, 8.2, 8.3, 8.4, 9 (combination), 10 (R-CONFIRM), 19 ruling 1, 3, 4.
Run: python3 -B audit_labels_a2.py
"""
import glob, json, math, os, statistics, sys

RUN = "/Users/daniellaloush/dandush03/ArborLM/experiments/P10IR-registered-20261118"
OUT = os.path.dirname(os.path.abspath(__file__))
GAP, MARGIN, RATIO, FLOOR_A, CLOSURE, R_MIN, H_MARGIN, TREE_CAND = 0.5, 0.25, 0.90, 0.25, 0.5, 0.90, 0.25, 512
CELLS = {"8K/4K": dict(f=8192, n=4096, up=8192, run=49152), "32K/16K": dict(f=32768, n=16384, up=16384, run=98304)}
BUDGETS = [128, 256, 512, 1024, 2048]
I64_SEEDS = [298001, 298002, 298003]
PANELS = ("A", "B")


def log_binom_pmf(n, k, p):
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1) + k * math.log(p) + (n - k) * math.log1p(-p)

_HIGH = {}
def chance_high(n, tests=40, alpha=0.001, p=1 / 32):
    if n in _HIGH:
        return _HIGH[n]
    tail, acc = alpha / tests / 2, 0.0
    for k in range(n, -1, -1):
        acc += math.exp(log_binom_pmf(n, k, p))
        if acc > tail:
            _HIGH[n] = k
            return k
    raise AssertionError

def fano(acc):
    e = 1.0 - acc
    h = 0.0 if e <= 0 or e >= 1 else -(e * math.log2(e) + (1 - e) * math.log2(1 - e))
    return 5.0 - h - e * math.log2(31)

def bits(useful, n):
    if n <= 0 or useful <= chance_high(n):
        return 0.0
    return fano(useful / n)

FLOOR_I = fano(FLOOR_A)


def cell_of(facts, slots):
    for name, c in CELLS.items():
        if c["f"] == facts and c["n"] == slots:
            return name
    raise KeyError((facts, slots))


def load_items():
    items = {}
    for path in sorted(glob.glob(f"{RUN}/a2/items/*/item.json")):
        d = os.path.dirname(path)
        it = json.load(open(path))
        reads = {}
        for rp in glob.glob(f"{d}/read.*.json"):
            r = json.load(open(rp))
            reads[r["read"]] = r
        key = (cell_of(it["facts"], it["slots"]), it["arm"], it["draw"], it["update"])
        assert key not in items, key
        items[key] = {"item": it, "reads": reads, "dir": d}
    return items


def gate_failures(item):
    return {k: g for k, g in item["gates"].items() if g.get("passed") is not True}


def restored(ix, iy):
    if iy < FLOOR_I:
        return "WEAK"
    return "RESTORED" if (iy - ix <= MARGIN + 1e-12 and ix >= RATIO * iy - 1e-12) else "NOT RESTORED"


def tree_row(i, cr8):
    if any(i["F0"][p] < FLOOR_I for p in PANELS):
        return "NOT EVALUABLE", {}
    gap = {p: i["F0"][p] - i["T0"][p] >= GAP - 1e-12 for p in PANELS}
    if not any(gap.values()):
        return "NO GAP", {}
    if not all(gap.values()):
        return "MIXED-PANEL", {}
    g = {r: {p: (i[r][p] - i["T0"][p]) / (i["F0"][p] - i["T0"][p]) for p in PANELS} for r in ("T1", "T3", "T2")}
    def cond(r):
        return all(restored(i[r][p], i["F0"][p]) == "RESTORED" for p in PANELS) or all(g[r][p] >= CLOSURE - 1e-12 for p in PANELS)
    P, C, J = cond("T1"), cond("T3"), cond("T2")
    H = all(i["T2"][p] <= i["T0"][p] - H_MARGIN + 1e-12 for p in PANELS)
    R = cr8 >= R_MIN - 1e-12
    tags = dict(P=P, C=C, J=J, H=H, R=R, g_P=g["T1"], g_C=g["T3"], g_PC=g["T2"])
    row = ("PRIORS AND CANDIDATES, SEPARATELY" if P and C else "PRIORS" if P else "CANDIDATES" if C else "JOINT" if J
           else "EXACT SEARCH HARMS" if H else "CONTENT" if R else "NOT IDENTIFIED")
    return row, tags


def index_row(i_f0, i_c, feasible):
    if any(i_f0[p] < FLOOR_I for p in PANELS):
        return "NOT EVALUABLE", None
    ok = {c: all(restored(i_c[c][p], i_f0[p]) == "RESTORED" for p in PANELS) for c in feasible}
    cstar = None
    for k, c in enumerate(feasible):
        if all(ok[x] for x in feasible[k:]):
            cstar = c
            break
    if cstar is None:
        return "INDEX DOES NOT APPROACH FLAT", None
    return ("SPARSE INDEX APPROACHES FLAT" if cstar <= TREE_CAND else "INDEX APPROACHES FLAT ONLY ABOVE 512"), cstar


def cell_rule(rows):
    assert len(rows) == 5
    if sum(r == "NOT EVALUABLE" for r in rows) >= 2:
        return "NOT EVALUABLE"
    for r in set(rows):
        if r not in ("NOT EVALUABLE", "MIXED-PANEL") and rows.count(r) >= 4:
            return r
    return "MIXED"


def component(labels):
    """labels[(cell, cp)] -> component under ADR 9 items 2-3 and ruling 1 (CELL-DEPENDENT kept with its per-cell rows)."""
    at = {}
    for cp in ("U_P", "RUN"):
        vals = {cell: labels[(cell, cp)] for cell in CELLS}
        at[cp] = vals["8K/4K"] if len(set(vals.values())) == 1 else ("CELL-DEPENDENT", tuple(sorted(vals.items())))
    return at["U_P"] if at["U_P"] == at["RUN"] else ("CHECKPOINT-DEPENDENT", at["U_P"], at["RUN"])


def main():
    items = load_items()
    log, diffs, ncmp = [], [], [0]

    def cmp(what, mine, theirs, tol=0.0):
        ncmp[0] += 1
        if isinstance(mine, float) or isinstance(theirs, float):
            same = mine is not None and theirs is not None and abs(float(mine) - float(theirs)) <= tol
        else:
            same = mine == theirs
        if not same:
            diffs.append(f"{what}: mine={mine!r} theirs={theirs!r}")

    log.append(f"items: {len(items)} (expected 40); keys complete: {sorted(set((k[0],k[1],k[3]) for k in items)) and all((c,a,d,u) in items for c,v in CELLS.items() for a in ('T-OQ','F-OQ') for d in range(1,6) for u in (v['up'],v['run']))}")
    n_reads, max_i_err = 0, 0.0
    for key, rec in items.items():
        for name, r in rec["reads"].items():
            for p in PANELS:
                pc = r["panels"][p]
                mine = bits(int(pc["useful"]), int(pc["n"]))
                ncmp[0] += 3
                err = abs(mine - float(pc["i"]))
                max_i_err = max(max_i_err, err)
                if err > 1e-12:
                    diffs.append(f"i of {key} {name} {p}: mine {mine} recorded {pc['i']}")
                if int(pc["useful"]) / int(pc["n"]) != float(pc["a_use"]):
                    diffs.append(f"a_use of {key} {name} {p}")
                if int(pc["correct"]) / int(pc["n"]) != float(pc["accuracy"]):
                    diffs.append(f"accuracy of {key} {name} {p}")
                n_reads += 1
    log.append(f"per-read i recomputed from counts: {n_reads} read-panels, max |i_mine - i_rec| = {max_i_err:.3e}; floor i = {FLOOR_I:.6f}")
    fails = {k: gate_failures(v["item"]) for k, v in items.items()}
    gate_tally = {}
    for k, v in items.items():
        for gname, g in v["item"]["gates"].items():
            gate_tally.setdefault(gname.split("_s29")[0], {}).setdefault(g.get("status"), 0)
            gate_tally[gname.split("_s29")[0]][g.get("status")] += 1
    log.append(f"item gates by name and status: {gate_tally}")
    log.append(f"items with a non-passed gate: {sum(1 for v in fails.values() if v)}; items incomplete: {sum(1 for v in items.values() if not v['item'].get('complete'))}; not_applicable lists non-empty: {sum(1 for v in items.values() if v['item'].get('not_applicable'))}")

    conf = json.load(open(f"{RUN}/confirm/confirm.json"))
    A2 = conf["A2"]
    mine_labels = {"tree": {}, "index": {}}
    for cell, c in CELLS.items():
        feasible = [b for b in BUDGETS if b < c["n"]]
        for cp, u in (("U_P", c["up"]), ("RUN", c["run"])):
            ck = A2["cells"][cell]["checkpoints"][cp]
            cmp(f"update {cell} {cp}", u, ck["update"])
            trows, irows, cstars = [], [], []
            for d in range(1, 6):
                t, f = items.get((cell, "T-OQ", d, u)), items.get((cell, "F-OQ", d, u))
                th_t, th_i = ck["tree"]["replicates"][d - 1], ck["index"]["replicates"][d - 1]
                cmp(f"draw order {cell} {cp} d{d}", (d, d), (th_t["draw"], th_i["draw"]))
                t_bad = t is None or bool(fails[(cell, "T-OQ", d, u)])
                f0_bad = f is None or any(g.get("scope") == "f0" for g in fails[(cell, "F-OQ", d, u)].values())
                idx_bad = f is None or any(g.get("scope") == "index" for g in fails[(cell, "F-OQ", d, u)].values())
                if t_bad or f0_bad:
                    row, tags = "NOT EVALUABLE", {}
                else:
                    i = {r: {p: float(t["reads"][r]["panels"][p]["i"]) for p in PANELS} for r in ("T0", "T1", "T1w", "T2", "T3")}
                    i["F0"] = {p: float(f["reads"]["F0"]["panels"][p]["i"]) for p in PANELS}
                    row, tags = tree_row(i, float(t["reads"]["T0"]["facts"]["cr8"]))
                    # ruling 3: accuracy version and per-panel retention status
                    for r in ("T1", "T2", "T3"):
                        for p in PANELS:
                            X, Y = t["reads"][r]["panels"][p], f["reads"]["F0"]["panels"][p]
                            a0 = X["disabled_correct"] / X["n"]
                            av = (X["correct"] / X["n"] - a0) / (Y["correct"] / Y["n"] - a0)
                            cmp(f"acc version {cell} {cp} d{d} {r} {p}", av, th_t["retention"][r][p]["accuracy_version"], 1e-12)
                            cmp(f"retention {cell} {cp} d{d} {r} {p}", restored(i[r][p], i["F0"][p]), th_t["retention"][r][p]["status"])
                    # same checkpoint for acc0: T-OQ disabled count used for X; record whether F0 disabled differs (descriptive)
                trows.append(row)
                cmp(f"tree row {cell} {cp} d{d}", row, th_t["row"])
                for k in ("P", "C", "J", "H", "R"):
                    if k in tags:
                        cmp(f"tree tag {k} {cell} {cp} d{d}", tags[k], th_t["tags"].get(k))
                if tags:
                    cmp(f"tree cr8 tag {cell} {cp} d{d}", float(t["reads"]["T0"]["facts"]["cr8"]), th_t["tags"]["cr8"], 0.0)
                for k in ("g_P", "g_C", "g_PC"):
                    if k in tags:
                        for p in PANELS:
                            cmp(f"tree {k} {cell} {cp} d{d} {p}", tags[k][p], th_t["tags"][k][p], 1e-12)
                if idx_bad or f0_bad:
                    irow, cs = "NOT EVALUABLE", None
                else:
                    i_f0 = {p: float(f["reads"]["F0"]["panels"][p]["i"]) for p in PANELS}
                    i_c = {b: {p: sum(float(f["reads"][f"I64@{b}/s{s}"]["panels"][p]["i"]) for s in I64_SEEDS) / 3 for p in PANELS} for b in feasible}
                    irow, cs = index_row(i_f0, i_c, feasible)
                    for b in feasible:
                        for p in PANELS:
                            cmp(f"index retention {cell} {cp} d{d} {b} {p}", restored(i_c[b][p], i_f0[p]), th_i["retention"][str(b)][p]["status"])
                irows.append(irow)
                cstars.append(cs)
                cmp(f"index row {cell} {cp} d{d}", irow, th_i["row"])
                cmp(f"c* {cell} {cp} d{d}", cs, th_i["tags"].get("c_star"))
            tl, il = cell_rule(trows), cell_rule(irows)
            got = [x for x in cstars if x is not None]
            med = float(statistics.median(got)) if got else None
            cmp(f"cell tree label {cell} {cp}", tl, ck["tree"]["label"])
            cmp(f"cell index label {cell} {cp}", il, ck["index"]["label"])
            cmp(f"median c* {cell} {cp}", med, ck["index"]["c_star_median"], 0.0)
            cmp(f"c* share of N {cell} {cp}", med / c["n"], ck["index"]["c_star_share_of_N"], 0.0)
            if cp == "RUN":  # ruling 4: NOT CHECKED, no tag (the block exists only at the run length)
                cmp(f"plateau {cell} {cp}", "NOT CHECKED", ck["plateau"]["status"])
                cmp(f"plateau tags {cell} {cp}", [], ck["plateau"]["tags"])
            else:
                cmp(f"no plateau block at U_P {cell}", "plateau" in ck, False)
            mine_labels["tree"][(cell, cp)] = tl
            mine_labels["index"][(cell, cp)] = il
            log.append(f"A2 {cell:8s} {cp:4s} u={u:6d} tree={tl} {trows}  index={il} c*={cstars} median={med}")

    rd = A2["r_diagnosis"]
    comp = {k: component(v) for k, v in mine_labels.items()}
    ne = [(k, cell, cp) for k, v in mine_labels.items() for (cell, cp), x in v.items() if x == "NOT EVALUABLE"]
    cmp("A2 R-DIAGNOSIS evaluable", not ne, rd["evaluable"])
    cmp("A2 tree component", comp["tree"], rd["components"]["tree"]["value"])
    cmp("A2 index component", comp["index"], rd["components"]["index"]["value"])
    for k in ("tree", "index"):
        for cp in ("U_P", "RUN"):
            for cell in CELLS:
                cmp(f"A2 component {k} at {cp} {cell}", mine_labels[k][(cell, cp)], rd["components"][k]["at"][cp]["cells"][cell])
    actions_tree = {"PRIORS AND CANDIDATES, SEPARATELY", "PRIORS", "CANDIDATES", "CONTENT"}
    rec_tree = comp["tree"] if isinstance(comp["tree"], str) and comp["tree"] in actions_tree else None
    rec_index = comp["index"] if comp["index"] == "SPARSE INDEX APPROACHES FLAT" else None
    cmp("A2 tree action none", rec_tree is None, rd["recommended"]["tree"] is None)
    cmp("A2 index action none", rec_index is None, rd["recommended"]["index"] is None)
    nrtc = comp["tree"] in ("EXACT SEARCH HARMS", "NOT IDENTIFIED") and comp["index"] == "INDEX DOES NOT APPROACH FLAT"
    cmp("A2 NO READ-TIME CAUSE", nrtc, rd["no_read_time_cause_identified"])
    log.append(f"A2 R-DIAGNOSIS evaluable={not ne}; tree={comp['tree']}; index={comp['index']}; actions tree={rec_tree} index={rec_index}; NRTC={nrtc}")

    # R-CONFIRM against A1's frozen analysis record, compared by row name (8.2; 10; ruling 1)
    ana = json.load(open(f"{RUN}/analysis/analysis.json"))
    a1rd = ana["A1"]["r_diagnosis"]
    a1comp = {}
    for k in ("tree", "index"):
        lab = {(cell, cp): ana["A1"]["cells"][cell]["checkpoints"][cp][k]["label"] for cell in CELLS for cp in ("U_P", "RUN")}
        a1comp[k] = component(lab)
        cmp(f"A1 {k} component (from A1 cell labels)", a1comp[k], a1rd["components"][k]["value"])
    rc = {}
    for k, name in (("tree", "R-CONFIRM-TREE"), ("index", "R-CONFIRM-INDEX")):
        if not a1rd["evaluable"]:
            v = "NOT APPLICABLE"
        elif ne:
            v = "NOT EVALUABLE"
        else:
            v = "CONFIRMED" if a1comp[k] == comp[k] else "NOT CONFIRMED"
        rc[name] = v
        cmp(name, v, conf["r_confirm"][name]["value"])
        cmp(name + " a1", a1comp[k], conf["r_confirm"][name]["a1"])
        cmp(name + " a2", comp[k], conf["r_confirm"][name]["a2"])
    log.append(f"R-CONFIRM: {rc}; A1 components {a1comp}")

    # descriptive means, A2 against A1 (task 4)
    def mean_ause(src, cell, u, arm, read):
        return sum(sum(src[(cell, arm, d, u)]["reads"][read]["panels"][p]["useful"] / src[(cell, arm, d, u)]["reads"][read]["panels"][p]["n"] for p in PANELS) / 2 for d in range(1, 6)) / 5
    def mean_i(src, cell, u, arm, read):
        return sum(sum(float(src[(cell, arm, d, u)]["reads"][read]["panels"][p]["i"]) for p in PANELS) / 2 for d in range(1, 6)) / 5
    def mean_fact(src, cell, u, arm, read, k):
        return sum(float(src[(cell, arm, d, u)]["reads"][read]["facts"][k]) for d in range(1, 6)) / 5
    # A1 items
    a1items = {}
    for path in sorted(glob.glob(f"{RUN}/a1/items/*/item.json")):
        it = json.load(open(path))
        try:
            cell = cell_of(it["facts"], it["slots"])
        except KeyError:
            continue
        if it["update"] not in (CELLS[cell]["up"], CELLS[cell]["run"]):
            continue
        reads = {json.load(open(rp))["read"]: json.load(open(rp)) for rp in glob.glob(os.path.dirname(path) + "/read.*.json")}
        a1items[(cell, it["arm"], it["draw"], it["update"])] = {"reads": reads}
    for cell in CELLS:
        for cp in ("U_P", "RUN"):
            u = CELLS[cell]["up" if cp == "U_P" else "run"]
            for tag, src in (("A1", a1items), ("A2", items)):
                desc = {r: round(mean_ause(src, cell, u, "T-OQ", r), 3) for r in ("T0", "T1", "T1w", "T3", "T2")}
                desc["F0"] = round(mean_ause(src, cell, u, "F-OQ", "F0"), 3)
                desc["I256"] = round(mean_ause(src, cell, u, "F-OQ", "I256@512"), 3)
                log.append(f"{tag} {cell} {cp} mean a_use {desc}; T0 CR8 {mean_fact(src, cell, u, 'T-OQ', 'T0', 'cr8'):.4f} AM_C {mean_fact(src, cell, u, 'T-OQ', 'T0', 'am_c'):.4f}; T3 SR8 {mean_fact(src, cell, u, 'T-OQ', 'T3', 'sr8'):.4f}; testability 1-chg(T3) {1 - mean_fact(src, cell, u, 'T-OQ', 'T3', 'sr8')*0 - sum(src[(cell,'T-OQ',d,u)]['reads']['T3']['pair']['share_selected_changed'] for d in range(1,6))/5:.4f}")
                vs = [v for v in (1, 2, 4, 8) if v <= CELLS[cell]["n"] // 256]
                on = {1: "Tv1_on", 2: "T0", 4: "Tv4_on", 8: "Tv8_on"}; off = {1: "Tv1_off", 2: "T1", 4: "Tv4_off", 8: "Tv8_off"}
                if CELLS[cell]["n"] // 256 == 16:
                    on[16], off[16] = "T3", "T2"; vs = vs + [16]
                log.append(f"   sweep i(on) { {v: round(mean_i(src, cell, u, 'T-OQ', on[v]), 3) for v in vs} } i(off) { {v: round(mean_i(src, cell, u, 'T-OQ', off[v]), 3) for v in vs} }")
                idx = {}
                for b in [x for x in BUDGETS if x < CELLS[cell]["n"]]:
                    recs = [src[(cell, "F-OQ", d, u)]["reads"][f"I64@{b}/s{s}"] for d in range(1, 6) for s in I64_SEEDS]
                    a = sum(sum(r["panels"][p]["useful"] / r["panels"][p]["n"] for p in PANELS) / 2 for r in recs) / 15
                    idx[b] = (round(a, 3), round(sum(float(r["facts"]["cr8"]) for r in recs) / 15, 3))
                log.append(f"   index (a_use, CR8) per budget {idx}")
            # A2 descriptive block of confirm.json against own means
            dd = A2["cells"][cell]["checkpoints"][cp]["tree"]["descriptive"]
            for r in ("T0", "T1", "T1w", "T3", "T2"):
                cmp(f"desc a_use {cell} {cp} {r}", mean_ause(items, cell, u, "T-OQ", r), dd["reads"][r]["a_use"], 1e-12)
                cmp(f"desc i {cell} {cp} {r}", mean_i(items, cell, u, "T-OQ", r), dd["reads"][r]["i"], 1e-12)
            cmp(f"desc a_use {cell} {cp} F0", mean_ause(items, cell, u, "F-OQ", "F0"), dd["reads"]["F0"]["a_use"], 1e-12)
            cmp(f"desc cr8 {cell} {cp} T0", mean_fact(items, cell, u, "T-OQ", "T0", "cr8"), dd["t0_measures"]["cr8"], 1e-12)
            cmp(f"desc testability {cell} {cp}", 1 - sum(items[(cell, 'T-OQ', d, u)]["reads"]["T3"]["pair"]["share_selected_changed"] for d in range(1, 6)) / 5, dd["testability"]["share_T3_selection_equals_T0"], 1e-12)
            di = A2["cells"][cell]["checkpoints"][cp]["index"]["descriptive"]["budgets"]
            for b in [x for x in BUDGETS if x < CELLS[cell]["n"]]:
                recs = [items[(cell, "F-OQ", d, u)]["reads"][f"I64@{b}/s{s}"] for d in range(1, 6) for s in I64_SEEDS]
                cmp(f"desc idx a_use {cell} {cp} {b}", sum(sum(r["panels"][p]["useful"] / r["panels"][p]["n"] for p in PANELS) / 2 for r in recs) / 15, di[str(b)]["a_use"], 1e-12)
                cmp(f"desc idx cr8 {cell} {cp} {b}", sum(float(r["facts"]["cr8"]) for r in recs) / 15, di[str(b)]["cr8"], 1e-12)
        # A1 c* per replicate for comparison
        for cp in ("U_P", "RUN"):
            a1i = ana["A1"]["cells"][cell]["checkpoints"][cp]["index"]
            log.append(f"A1 {cell} {cp} c* {[r['tags'].get('c_star') for r in a1i['replicates']]} median {a1i['c_star_median']}; A1 tree rows {[r['row'] for r in ana['A1']['cells'][cell]['checkpoints'][cp]['tree']['replicates']]}")
    cmp("confirm a1_analysis_sha256", conf["a1_analysis_sha256"], "0ea94efec822605953b1e7177464401e362453b0edfd2c6b55a2b161685ff6da")
    log.append(f"statement_allowed in confirm.json: {conf['statement_allowed']}")
    log.append(f"COMPARISONS {ncmp[0]}; DIFFERENCES {len(diffs)}")
    log += ["DIFF " + x for x in diffs[:300]]
    text = "\n".join(log)
    print(text)
    open(f"{OUT}/audit_labels_a2.out.txt", "w").write(text + "\n")


if __name__ == "__main__":
    sys.exit(main())
```

### audit_integrity_a2.py

```
"""Integrity checks of P10-I-R stage group A2 (auditor's own code; standard library only). Run: python3 -B audit_integrity_a2.py"""
import glob, hashlib, json, os, subprocess, sys

RUN = "/Users/daniellaloush/dandush03/ArborLM/experiments/P10IR-registered-20261118"
S1 = "/Users/daniellaloush/dandush03/ArborLM/experiments/P10S1-registered-attempt2-20261117"
WT = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/arborlm-consolidation-experiment-2b31c1"
FREEZE = "c712a905b01da3f12e2f884f8eaf44933a1756db"
OUT = os.path.dirname(os.path.abspath(__file__))
log, bad = [], []

def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def blob_sha(path):
    return hashlib.sha256(subprocess.run(["git", "-C", WT, "show", f"{FREEZE}:{path}"], capture_output=True, check=True).stdout).hexdigest()

def check(what, ok, detail=""):
    log.append(f"{'OK ' if ok else 'BAD'} {what} {detail}")
    if not ok:
        bad.append(what)

plan_sha, cfg_sha = blob_sha("studies/p10ir/freeze/plan.json"), blob_sha("configs/p10ir_routing.toml")
log.append(f"plan blob sha at freeze {plan_sha}; config blob sha {cfg_sha}")
plan = json.loads(subprocess.run(["git", "-C", WT, "show", f"{FREEZE}:studies/p10ir/freeze/plan.json"], capture_output=True, check=True).stdout)

# 1. manifests
charged = {}
for st in ("gates-a1", "a1", "analysis", "report", "gates-a2", "a2-train", "a2", "confirm"):
    m = json.load(open(f"{RUN}/{st}/manifest.json"))
    charged[st] = m["charged_seconds"]
    t = m.get("tasks", {})
    h = m["history"]
    check(f"manifest {st}", m["status"] == "COMPLETE" and m["mode"] == "registered" and m["clean"] and m["item_errors"] == 0 and not m["item_error_list"]
          and m["identity"]["plan_sha256"] == plan_sha and m["identity"]["config_sha256"] == cfg_sha and len(h) == 1 and all(x["status"] == "completed" and x.get("returncode", 0) == 0 for x in t.values()),
          f"tasks {len(t)} charged {m['charged_seconds']:.3f} cap_at_start {h[0]['caps']['stage_seconds']:.3f} wall {h[0]['started_utc']}..{h[0]['finished_utc']} platform {m['identity']['platform']['platform']} threads {m['identity']['platform']['torch_num_threads']},{m['identity']['platform']['torch_interop_threads']} det {m['identity']['platform']['deterministic_algorithms']}")
from datetime import datetime
for st in ("a2-train", "a2"):
    h = json.load(open(f"{RUN}/{st}/manifest.json"))["history"][0]
    wall = (datetime.fromisoformat(h["finished_utc"]) - datetime.fromisoformat(h["started_utc"])).total_seconds()
    log.append(f"{st}: charged {h['charged_seconds']:.1f} s vs wall {wall:.1f} s; summed task seconds {sum(x['seconds'] for x in json.load(open(f'{RUN}/{st}/manifest.json'))['tasks'].values()):.1f}")
a2tot = sum(charged[s] for s in ("gates-a2", "a2-train", "a2", "confirm"))
a1tot = sum(charged[s] for s in ("gates-a1", "a1", "analysis", "report"))
cap_chain = [json.load(open(f"{RUN}/{s}/manifest.json"))["history"][0]["caps"]["stage_seconds"] for s in ("gates-a2", "a2-train", "a2", "confirm")]
check("A2 cap chain = 10800 minus earlier A2 stages", all(abs(cap_chain[k] - (10800 - sum(charged[s] for s in ("gates-a2", "a2-train", "a2", "confirm")[:k]))) < 1e-6 for k in range(4)), str(cap_chain))
rc = json.load(open(f"{WT}/results/p10ir-freeze-2026-11-18/rehearsal_count.json"))
def charged_sum(o):
    s = 0.0
    if isinstance(o, dict):
        for k, v in o.items():
            s += v if k == "charged_seconds" and isinstance(v, (int, float)) else charged_sum(v)
    return s
rehearsal = charged_sum(rc)
rm = charged_sum(json.load(open(f"{WT}/results/p10ir-rehearsal-measure-2026-11-18/rehearsal.json")))
log.append(f"charged hours: A1 group {a1tot/3600:.4f} (cap 6.0); A2 group {a2tot/3600:.4f} (cap 3.0) = gates-a2 {charged['gates-a2']:.1f} + a2-train {charged['a2-train']:.1f} + a2 {charged['a2']:.1f} + confirm {charged['confirm']:.3f} s; counting rehearsal {rehearsal/3600:.4f} (cap 1.0); measuring rehearsal (provisional caps) {rm/3600:.4f}")
log.append(f"study total (counting rehearsal + A1 + A2) {(rehearsal + a1tot + a2tot)/3600:.4f} h; with the measuring rehearsal {(rehearsal + rm + a1tot + a2tot)/3600:.4f} h (cap 10.0)")

# 2. A1 analysis record untouched
check("analysis.json hash", sha(f"{RUN}/analysis/analysis.json") == "0ea94efec822605953b1e7177464401e362453b0edfd2c6b55a2b161685ff6da")
for f in ("analysis/analysis.json", "analysis/manifest.json"):
    cp = glob.glob(f"{WT}/results/p10ir-run-2026-11-18/**/{os.path.basename(f)}", recursive=True)
    log.append(f"committed copies of {f}: {[(os.path.relpath(c, WT), sha(c) == sha(f'{RUN}/{f}')) for c in cp]}")
log.append(f"mtime analysis.json {os.path.getmtime(RUN + '/analysis/analysis.json')} < confirm.json {os.path.getmtime(RUN + '/confirm/confirm.json')}")

# 3. bridge draws and seeds
reg = {d: dict(base=290001 + 100 * (d - 1), init=330600 + d, name=f"p10ir-bridge-{d}") for d in range(1, 6)}
for d in range(1, 6):
    m = json.load(open(f"{RUN}/a2/draws/p10ir-bridge-{d}/data_manifest.json"))
    vals = m["seed_values"]
    check(f"draw manifest {d}", m["seed_name"] == reg[d]["name"] and m["seed_base"] == reg[d]["base"] and all(reg[d]["base"] <= v < reg[d]["base"] + 100 for v in vals) and all(290001 <= v <= 296999 for v in vals) and reg[d]["base"] + 60 in vals,
          f"base {m['seed_base']} values {min(vals)}..{max(vals)} n={len(vals)}")
plan_a2 = plan.get("a2") or plan.get("A2") or {}
log.append(f"plan top-level keys: {list(plan.keys())}")

# 4. bridge cells vs registry and P10-S1
cells = sorted(os.listdir(f"{RUN}/a2/train/cells"))
check("20 bridge cells", len(cells) == 20 and not any(c.endswith(".partial") or c.endswith(".failed.json") for c in cells), str(len(cells)))
nsnap = 0
for lab in cells:
    t = json.load(open(f"{RUN}/a2/train/cells/{lab}/train.json"))
    d = t["draw"]
    s1lab = lab.replace(f"_i{330600 + d}", f"_i{2100 + d}")
    s = json.load(open(f"{S1}/cells/{s1lab}/train.json"))
    same = {k: (t[k], s[k]) for k in ("arm", "facts", "slots", "learning_rate", "run_updates", "u_p", "snapshots")}
    check(f"cell {lab} seeds", t["init_seed"] == reg[d]["init"] and t["seed_name"] == reg[d]["name"] and t["status"] == "completed" and t["updates"] == t["run_updates"], f"init {t['init_seed']} set {t['seed_name']}")
    check(f"cell {lab} pinned to {s1lab}", all(a == b for a, b in same.values()) and s["init_seed"] == 2100 + d and s["seed_set"] == f"p10s1-draw-{d}", str({k: v[0] for k, v in same.items()}))
    pl = t["platform"]
    check(f"cell {lab} platform", pl["torch_num_threads"] == 1 and pl["torch_interop_threads"] == 1 and pl["deterministic_algorithms"] and pl["torch"] == "2.8.0")
    for u, h in t["snapshot_sha256"].items():
        p = f"{RUN}/a2/train/cells/{lab}/snapshots/u{int(u):07d}/model.pt"
        sj = json.load(open(os.path.dirname(p) + "/snapshot.json")) if os.path.exists(os.path.dirname(p) + "/snapshot.json") else {}
        ok = sha(p) == h and sj.get("model_sha256", h) == h
        nsnap += 1
        if not ok:
            check(f"snapshot {lab} {u}", False)
    check(f"cell {lab} snapshot list", sorted(int(u) for u in t["snapshot_sha256"]) == sorted(t["snapshots"]) == sorted(int(x[1:]) for x in os.listdir(f"{RUN}/a2/train/cells/{lab}/snapshots")))
log.append(f"snapshot files hashed against train.json and snapshot.json: {nsnap}")
# item checkpoint identity vs train.json
for p in sorted(glob.glob(f"{RUN}/a2/items/*/item.json")):
    it = json.load(open(p))
    t = json.load(open(f"{RUN}/a2/train/cells/{it['cell']}/train.json"))
    check(f"item {os.path.basename(os.path.dirname(p))} checkpoint", it["gates"]["checkpoint_identity"]["model_sha256"] == t["snapshot_sha256"][str(it["update"])] and it["update"] in (t["u_p"], t["run_updates"]) and it["complete"])
# done records
done = glob.glob(f"{RUN}/a2/tasks/*.done.json")
check("a2 done records 20", len(done) == 20 and all(json.load(open(x))["complete"] for x in done))

# 5. adapter identity gate: own hashes
g = json.load(open(f"{RUN}/gates-a2/gates.json"))
log.append(f"gates-a2 passed {g['passed']}; gate names {list(g['gates'])}; failed {g['failed']}")
for lab in ("P_F-OQ_f8192_n4096_d1_i2101", "P_T-OQ_f8192_n4096_d1_i2101"):
    for u in (512, 1024, 2048):
        new = f"{RUN}/gates-a2/identity_work/{lab}/snapshots/u{u:07d}/model.pt"
        old = f"{S1}/cells/{lab}/snapshots/u{u:07d}/model.pt"
        rec = json.load(open(os.path.dirname(old) + "/snapshot.json"))["model_sha256"]
        check(f"identity {lab} u{u}", sha(new) == sha(old) == rec, rec[:16])
g1 = g["gates"]["gate1_identities"]
log.append(f"gate1: {g1}")
log.append(f"gate5: {g['gates']['gate5_rehearsal']}")
log.append(f"gate6: passed {g['gates']['gate6_seeds']['passed']} result {g['gates']['gate6_seeds']['checker']['result_line']} sha {g['gates']['gate6_seeds']['checker']['sha256']} roles {g['gates']['gate6_seeds']['roles']}")
log.append(f"RESULT: {'ALL OK' if not bad else 'BAD: ' + '; '.join(bad)}")
text = "\n".join(log)
print(text)
open(f"{OUT}/audit_integrity_a2.out.txt", "w").write(text + "\n")
```

### audit_margins_a2.py

```
"""Distance of A2's labels from their thresholds (auditor's own code; standard library). Run: python3 -B audit_margins_a2.py"""
import json
RUN = "/Users/daniellaloush/dandush03/ArborLM/experiments/P10IR-registered-20261118"
c = json.load(open(f"{RUN}/confirm/confirm.json"))["A2"]
for cell in ("8K/4K", "32K/16K"):
    for cp in ("U_P", "RUN"):
        t = c["cells"][cell]["checkpoints"][cp]["tree"]["replicates"]
        g = {k: max(r["tags"][k][p] for r in t for p in "AB") for k in ("g_P", "g_C", "g_PC")}
        cr8 = max(r["tags"]["cr8"] for r in t)
        ix = c["cells"][cell]["checkpoints"][cp]["index"]["replicates"]
        below = {b: sum(1 for r in ix for p in "AB" if r["retention"][b][p]["status"] == "RESTORED") for b in ("512", "1024", "2048") if b in ix[0]["retention"]}
        print(cell, cp, "max g", {k: round(v, 3) for k, v in g.items()}, "max CR8", round(cr8, 4), "RESTORED panel-replicates (of 10) per budget", below)
```

### audit_spread_a2.py

```
"""Replicate spread of A1 and A2 means at the primary cells, and a Welch-type t of the A2-A1 difference (descriptive; auditor's own code). Run: python3 -B audit_spread_a2.py"""
import glob, json, os, statistics as st
RUN = "/Users/daniellaloush/dandush03/ArborLM/experiments/P10IR-registered-20261118"
def load(stage):
    out = {}
    for p in glob.glob(f"{RUN}/{stage}/items/*/item.json"):
        it = json.load(open(p))
        if (it["facts"], it["slots"]) not in ((8192, 4096), (32768, 16384)):
            continue
        d = os.path.dirname(p)
        out[(it["facts"], it["arm"], it["draw"], it["update"])] = {json.load(open(r))["read"]: json.load(open(r)) for r in glob.glob(d + "/read.*.json")}
    return out
A1, A2 = load("a1"), load("a2")
def au(r): return sum(r["panels"][p]["useful"] / r["panels"][p]["n"] for p in "AB") / 2
def ii(r): return sum(r["panels"][p]["i"] for p in "AB") / 2
for f, up, run in ((8192, 8192, 49152), (32768, 16384, 98304)):
    for u in (up, run):
        for arm, read, fn in (("T-OQ", "T0", au), ("T-OQ", "T1", au), ("T-OQ", "T1w", au), ("T-OQ", "T3", au), ("T-OQ", "T2", au), ("F-OQ", "F0", au), ("T-OQ", "T0", ii), ("F-OQ", "I256@512", au)):
            a = [fn(A1[(f, arm, d, u)][read]) for d in range(1, 6)]
            b = [fn(A2[(f, arm, d, u)][read]) for d in range(1, 6)]
            se = (st.variance(a) / 5 + st.variance(b) / 5) ** 0.5
            print(f"f{f} u{u} {read:9s} {fn.__name__}: A1 {st.mean(a):.4f} (sd {st.stdev(a):.4f})  A2 {st.mean(b):.4f} (sd {st.stdev(b):.4f})  diff {st.mean(b)-st.mean(a):+.4f}  t {((st.mean(b)-st.mean(a))/se) if se else float('nan'):+.2f}")
```

### audit_replicates_a2.py

```
"""Per-replicate T0 and F0 a_use, A1 and A2, primary cells (descriptive). Run: python3 -B audit_replicates_a2.py"""
import glob, json, os
RUN = "/Users/daniellaloush/dandush03/ArborLM/experiments/P10IR-registered-20261118"
for stage in ("a1", "a2"):
    for p in sorted(glob.glob(f"{RUN}/{stage}/items/*T-OQ*/item.json")):
        it = json.load(open(p))
        if (it["facts"], it["slots"]) not in ((8192, 4096), (32768, 16384)) or it["update"] not in (8192, 49152, 16384, 98304) or (it["facts"] == 8192 and it["update"] in (16384, 98304)) or (it["facts"] == 32768 and it["update"] in (8192, 49152)):
            continue
        d = os.path.dirname(p)
        r = json.load(open(d + "/read.T0.json"))
        print(stage, it["facts"], it["update"], "d", it["draw"], "T0 a_use", round(sum(r["panels"][x]["a_use"] for x in "AB") / 2, 4), "CR8", round(r["facts"]["cr8"], 4))
```

### launch_tensors.sh

```
#!/bin/zsh
# Runs the 8 tensor checks, at most 6 at once, each with a hard deadline of 7200 s. Usage: zsh launch_tensors.sh
W=/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/arborlm-consolidation-experiment-2b31c1
S=/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/audit-p10ir-a2
cd $S
export PYTHONPATH=$W PYTHONDONTWRITEBYTECODE=1 PYTHONPYCACHEPREFIX=$S/pycache
printf '%s\n' "T-OQ 1 16384" "T-OQ 1 98304" "T-OQ 2 16384" "T-OQ 2 98304" "F-OQ 1 16384" "F-OQ 1 98304" "F-OQ 2 16384" "F-OQ 2 98304" | \
  xargs -P 6 -L 1 sh -c 'a=$0; d=$1; u=$2; timeout 7200 '"$W"'/.venv/bin/python -B '"$S"'/audit_tensors_a2.py $a $d $u > '"$S"'/log_${a%%-OQ}_d${d}_u${u}.txt 2>&1; echo "exit $? $a $d $u" >> '"$S"'/launch_exits.txt'
echo ALLDONE >> $S/launch_exits.txt
```

### audit_tensors_a2.py

```
"""Brute-force float64 recomputation of P10-I-R A2 (bridge) reads from the checkpoint tensors (auditor's own selection, weights, recall,
attention-mass, candidate and information code). The study code is called ONLY as the object under comparison (studies.p10ir.reads.tree_path,
for the per-fact gate-4-style comparison). P10-S1/P9 functions are used for the data draw, the backbone, loading model.pt, the oracle query
codes and the panel pass (derangement, address swap, answer scoring): the parts gate 2 already ties to P10-S1's registered counts.

Usage (one checkpoint per process):
  PYTHONPATH=<worktree> PYTHONDONTWRITEBYTECODE=1 PYTHONPYCACHEPREFIX=<scratch>/pycache <worktree>/.venv/bin/python -B audit_tensors.py <T-OQ|F-OQ> <draw> <update>
"""
import json, math, os, sys, time
from pathlib import Path

import torch
from torch.nn import functional as F

torch.set_num_threads(1)
torch.set_num_interop_threads(1)
torch.use_deterministic_algorithms(True)

W = Path("/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/arborlm-consolidation-experiment-2b31c1")
RUN = Path("/Users/daniellaloush/dandush03/ArborLM/experiments/P10IR-registered-20261118")
S1 = Path("/Users/daniellaloush/dandush03/ArborLM/experiments/P10S1-registered-attempt2-20261117")
EXP = Path("/Users/daniellaloush/dandush03/ArborLM/experiments")
OUT = Path(__file__).resolve().parent
TEMP, EPS, TOP, SOFT = 0.2, 1e-8, 8, 64
PER = 256
TIE, WTOL = 1e-5, 1e-6

from studies.p9 import controls, data as data_mod, core as p9core  # noqa: E402
from studies.p10s1 import core as s1core, evaluate as s1eval, index as s1index  # noqa: E402
from studies.p10s1.model import S1Memory, build_model  # noqa: E402
from studies.p10s1.train import load_model_state  # noqa: E402

arm, draw, update = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
FACTS, SLOTS = 32768, 16384
plan = json.load(open(W / "studies/p10ir/freeze/plan.json"))
item = [i for i in plan["items"]["A2"] if i["arm"] == arm and i["draw"] == draw and i["update"] == update and i["cell_name"] == "32K/16K"][0]
out = {"item": item["id"], "arm": arm, "draw": draw, "update": update, "torch": torch.__version__, "threads": torch.get_num_threads()}
t_start = time.monotonic()


# --- my float64 helpers ---------------------------------------------------------------------------------------------------
def unit64(x):
    x = x.detach().to(torch.float64)
    return x / x.norm(dim=-1, keepdim=True).clamp_min(EPS)


def top_ids(scores, k):
    """Top k per row by score descending, ties to the lower column id. Exact: topk(k+16), then lexicographic sort; rows whose (k+16)-th value equals the k-th fall back to a full stable sort."""
    extra = min(scores.shape[1], k + 16)
    vals, idx = scores.topk(extra, dim=1)
    # lexicographic (-score, id) within the candidates
    o1 = idx.argsort(dim=1, stable=True)
    vals, idx = vals.gather(1, o1), idx.gather(1, o1)
    o2 = (-vals).argsort(dim=1, stable=True)
    vals, idx = vals.gather(1, o2), idx.gather(1, o2)
    if extra < scores.shape[1]:
        unsafe = vals[:, k - 1] <= vals[:, extra - 1]
        if bool(unsafe.any()):
            full = (-scores[unsafe]).argsort(dim=1, stable=True)[:, :extra]
            idx[unsafe] = full
            vals[unsafe] = scores[unsafe].gather(1, full)
    return vals[:, :k], idx[:, :k]


def fano(acc):
    e = 1.0 - acc
    h = 0.0 if e <= 0 or e >= 1 else -(e * math.log2(e) + (1 - e) * math.log2(1 - e))
    return 5.0 - h - e * math.log2(31)


def chance_high(n, tests=40, alpha=0.001, p=1 / 32):
    tail, acc = alpha / tests / 2, 0.0
    for k in range(n, -1, -1):
        acc += math.exp(math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1) + k * math.log(p) + (n - k) * math.log1p(-p))
        if acc > tail:
            return k


HIGH = chance_high(FACTS)


def bits(useful, n):
    return 0.0 if useful <= HIGH else fano(useful / n)


# --- data, model -------------------------------------------------------------------------------------------------------------
seeds = s1core.seed_set(item["seed_name"], item["seed_base"])
corpus = p9core.load_trained_corpus(EXP)
data = data_mod.build_study_data(seeds, corpus, sizes=data_mod.DataSizes(main_trained=item["table_facts"], unseen=item["unseen"], lane_d_per_set=s1core.LANE_D_STUB))
man = json.load(open(plan["draw_manifests"][item["seed_name"]]["path"]))
out["draw_hashes_equal_manifest"] = man["sha256s"] == data.sha256s()
_cwd = os.getcwd()
os.chdir(W)  # P5/P4 parent verification reads repository-relative records (read only); back to the scratch folder at once
try:
    backbone = controls.load_backbone(p9core.PRIMARY_PARENT, EXP)[0]
finally:
    os.chdir(_cwd)
model = build_model(arm, SLOTS, item["init_seed"], backbone, r1_seed=seeds.r1_codes, hash_seed=s1core.h8_seed(seeds), seed_rng=False)
snap = RUN / "a2" / "train" / "cells" / item["cell"] / "snapshots" / s1core.snapshot_stem(update)
out["snapshot_dir"] = str(snap)
load_model_state(snap, model)
model.eval()
raw = torch.load(snap / "model.pt", weights_only=True, map_location="cpu")["model"]
src = model.addition
out["keys_equal_raw_tensor"] = bool(torch.equal(raw["addition.keys"], src.keys.detach()))
K = unit64(raw["addition.keys"])  # [N, 16]
RT = unit64(raw["addition.router"]) if arm == "T-OQ" else None
n_branches = SLOTS // PER
key_branch = torch.arange(SLOTS) // PER

all_ident = data.facts.ident
codes_all = s1eval.fact_codes(model, data, int(all_ident.shape[0]))  # [all facts, 16] float32 unit codes (the query)
codes = codes_all[:FACTS]
out["facts_in_table"] = int(all_ident.shape[0])
out["code_norm_max_dev"] = float((codes.double().norm(dim=1) - 1).abs().max())


# --- my tree read ------------------------------------------------------------------------------------------------------------
def tree_read(q32, v, ps, pw, k=SOFT):
    q = q32.to(torch.float64)
    cos = q @ K.T / TEMP
    routes = q @ RT.T / TEMP
    prior = routes.log_softmax(-1)
    _, border = top_ids(routes, n_branches)
    visited = border[:, :v]
    in_c = torch.zeros(q.shape[0], n_branches, dtype=torch.bool).scatter_(1, visited, True)[:, key_branch]
    kp = prior[:, key_branch]
    sel = (cos + kp) if ps else cos.clone()
    sel = sel.masked_fill(~in_c, -math.inf)
    _, ids = top_ids(sel, k)
    wsc = ((cos + kp) if pw else cos).gather(1, ids)
    sel_sc = sel.gather(1, ids)
    return ids, wsc, sel_sc, in_c, visited, routes


def flat_read(q32, cand=None, k=SOFT):
    q = q32.to(torch.float64)
    cos = q @ K.T / TEMP
    sc = cos if cand is None else cos.masked_fill(~cand, -math.inf)
    _, ids = top_ids(sc, k)
    return ids, cos.gather(1, ids), sc.gather(1, ids)


def ivf_mask(q32, idx, minimum):
    q = q32.to(torch.float64)
    unit = unit64(idx.centroids)
    sc = q @ unit.T
    order = (-sc).argsort(dim=1, stable=True)
    cum = idx.sizes.to(torch.int64)[order].cumsum(1)
    reached = cum >= minimum
    need = torch.where(reached.any(1), reached.to(torch.int64).argmax(1), torch.full((q.shape[0],), idx.lists - 1))
    rank = torch.empty_like(order).scatter_(1, order, torch.arange(idx.lists).expand(q.shape[0], -1).contiguous())
    visited = rank <= need[:, None]
    return visited.gather(1, idx.assign[None, :].expand(q.shape[0], -1)), cum.gather(1, need[:, None]).squeeze(1)


def exhaustive8(q32):
    q = q32.to(torch.float64)
    cos = q @ K.T / TEMP
    v, i = top_ids(cos, TOP)
    return i, v


# --- end-task through the panel pass, with my selection served per query ------------------------------------------------------
class MyMemory(S1Memory):
    def __init__(self, source, table_ids, table_w, row_of):
        super().__init__(source.spec, source.seed, r1_seed=source.r1_seed)
        self.load_state_dict(source.state_dict(), strict=True)
        self.table_ids, self.table_w, self.row_of = table_ids, table_w, row_of
        self.miss = 0
        self.fallback = None

    def _lookup(self, q):
        rows = []
        for r in q:
            key = tuple(r.tolist())
            j = self.row_of.get(key)
            if j is None:
                self.miss += 1
                j = -1
            rows.append(j)
        rows = torch.tensor(rows)
        ids = torch.empty(q.shape[0], SOFT, dtype=torch.int64)
        w = torch.empty(q.shape[0], SOFT, dtype=torch.float32)
        ok = rows >= 0
        ids[ok] = self.table_ids[rows[ok]]
        w[ok] = self.table_w[rows[ok]].to(torch.float32)
        if bool((~ok).any()):
            fi, fw = self.fallback(q[~ok])
            ids[~ok], w[~ok] = fi, fw.to(torch.float32)
        return w, ids

    def _top_tree(self, q):
        w, ids = self._lookup(q)
        return w, ids, torch.zeros(q.shape[0], 2, dtype=torch.int64), torch.zeros(q.shape[0], n_branches)

    def _top_flat(self, q):
        return self._lookup(q)


row_of = {tuple(row): j for j, row in enumerate(codes_all.tolist())}
pi = s1eval._deranged(data, FACTS, s1core.mask_seed(seeds, 0))


def end_task(table_ids, table_w, fallback):
    mem = MyMemory(src, table_ids, table_w, row_of)
    mem.fallback = fallback
    old = model.addition
    model.addition = mem
    res = {}
    try:
        for panel in s1core.PANELS:
            stream = s1eval.stream_for(data, FACTS, s1core.PANEL_STREAM[panel])
            c = s1eval.panel_counts(model, data, FACTS, stream, pi=pi, tables=None)
            res[panel] = {"n": int(c["n"]), "correct": int(c["correct"]), "useful": int(c["useful"]), "i": bits(int(c["useful"]), int(c["n"])), "a_use": int(c["useful"]) / int(c["n"])}
    finally:
        model.addition = old
    res["lookup_misses"] = mem.miss
    return res


def recorded(name):
    return json.load(open(RUN / "a2" / "items" / f"A2__{item['cell']}__u{update:07d}" / f"read.{name.replace('/', '~')}.json"))


def compare_counts(mine, rec):
    return {p: {"mine_correct": mine[p]["correct"], "rec_correct": rec["panels"][p]["correct"], "mine_useful": mine[p]["useful"], "rec_useful": rec["panels"][p]["useful"],
                "mine_i": round(mine[p]["i"], 6), "rec_i": round(float(rec["panels"][p]["i"]), 6)} for p in ("A", "B")}


CH = 512
if arm == "T-OQ":
    from studies.p10ir import reads as p10ir_reads  # the object under comparison only

    specs = {"T0": (2, True, True), "T1": (2, False, False), "T1w": (2, True, False), "T3": (64, True, True), "T2": (64, False, False),
             "Tv1_on": (1, True, True), "Tv1_off": (1, False, False), "Tv4_on": (4, True, True), "Tv4_off": (4, False, False), "Tv8_on": (8, True, True), "Tv8_off": (8, False, False)}
    keys32, router32 = src.keys.detach(), src.router.detach()
    results = {}
    store = {}
    # exhaustive E8 once
    E_ids, E_vals = [], []
    for s in range(0, FACTS, CH):
        i, v = exhaustive8(codes[s:s + CH])
        E_ids.append(i); E_vals.append(v)
    E_ids, E_vals = torch.cat(E_ids), torch.cat(E_vals)
    wE = E_vals.softmax(-1)
    for name, (v, ps, pw) in specs.items():
        t0 = time.monotonic()
        ids_all, w_all, sel_all, stats = [], [], [], {k: [] for k in ("cr8", "cr1", "sr8", "am_c", "am_s", "span")}
        g4 = {"facts": 0, "sets_differ": 0, "float_ties": 0, "not_float_ties": 0, "max_weight_diff": 0.0}
        for s in range(0, codes_all.shape[0], CH):
            q = codes_all[s:s + CH]
            ids, wsc, selsc, in_c, visited, routes = tree_read(q, v, ps, pw)
            ids_all.append(ids); w_all.append(wsc); sel_all.append(selsc)
            if s < FACTS:
                n_here = min(CH, FACTS - s)
                e = E_ids[s:s + n_here]
                c8 = in_c[:n_here].gather(1, e)
                sel8 = ids[:n_here, :TOP]
                s_in_e = (sel8[:, :, None] == e[:, None, :]).any(1)
                stats["cr8"].append(c8.double().mean(1)); stats["cr1"].append(c8[:, 0].double())
                stats["sr8"].append((sel8[:, :, None] == e[:, None, :]).any(-1).double().mean(1))
                stats["am_c"].append((c8.double() * wE[s:s + n_here]).sum(1)); stats["am_s"].append((s_in_e.double() * wE[s:s + n_here]).sum(1))
                br = sel8 // PER
                stats["span"].append((br.min(1).values != br.max(1).values).double())
                # gate-4-style comparison with the study's float32 path, per fact
                ref = p10ir_reads.tree_path(keys32, router32, q[:n_here], v, ps, pw, per=PER, chunk_elements=1 << 20)
                a_set, _ = sel8.sort(1)
                b_set, ob = ref.ids[:, :TOP].sort(1)
                same = (a_set == b_set).all(1)
                # tie: 8th and 9th selection scores within 1e-5 in either computation (theirs: recompute selection scores of their 9 in float32)
                gap_mine = (selsc[:n_here, TOP - 1] - selsc[:n_here, TOP]).abs()
                cos32 = (F.normalize(keys32, dim=-1, eps=EPS)[ref.ids[:, :TOP + 1]] @ q[:n_here].unsqueeze(-1)).squeeze(-1) / TEMP
                pr32 = ref.routes.log_softmax(-1).gather(1, ref.ids[:, :TOP + 1] // PER) if ps else 0.0
                s32 = cos32 + pr32
                gap_theirs = (s32[:, TOP - 1] - s32[:, TOP]).abs()
                tie = (gap_mine <= TIE) | (gap_theirs <= TIE)
                g4["facts"] += n_here
                g4["sets_differ"] += int((~same).sum()); g4["float_ties"] += int((~same & tie).sum()); g4["not_float_ties"] += int((~same & ~tie).sum())
                wa = wsc[:n_here, :TOP].softmax(-1).gather(1, sel8.argsort(1))
                wb = ref.values[:, :TOP].to(torch.float64).softmax(-1).gather(1, ob)
                if bool(same.any()):
                    g4["max_weight_diff"] = max(g4["max_weight_diff"], float((wa - wb).abs().max(1).values[same].max()))
        ids_all, w_all = torch.cat(ids_all), torch.cat(w_all)
        store[name] = (ids_all[:FACTS, :TOP], w_all[:FACTS, :TOP])
        facts = {k: float(torch.cat(x).mean()) for k, x in stats.items()}
        rec = recorded(name)
        fb = (lambda q, v=v, ps=ps, pw=pw: tree_read(q, v, ps, pw)[:2])
        et = end_task(ids_all, w_all, fb)
        results[name] = {"facts_mine": facts, "facts_recorded": rec["facts"], "gate4_vs_study_path": g4, "counts": compare_counts(et, rec), "lookup_misses": et["lookup_misses"], "seconds": round(time.monotonic() - t0, 1)}
        print(name, json.dumps(results[name]), flush=True)
    # pair statistics (section 7): T0 vs T1, T1w, T3; T3 vs T2
    def pair(a, b):
        ai, aw = store[a]; bi, bw = store[b]
        aw, bw = aw.softmax(-1), bw.softmax(-1)
        m = ai[:, :, None] == bi[:, None, :]
        changed = ~m.any(-1).all(-1)
        w_b_at_a = (m.double() * bw[:, None, :]).sum(-1)
        tv = 0.5 * ((aw - w_b_at_a).abs().sum(1) + (bw * (~m.any(1)).double()).sum(1))
        return float(changed.double().mean()), float(tv.mean())
    for a, b in (("T1", "T0"), ("T1w", "T0"), ("T3", "T0"), ("T2", "T3")):
        ch, tv = pair(a, b)
        results[a]["pair_mine"] = {"against": b, "share_selected_changed": ch, "tv_mean": tv}
        results[a]["pair_recorded"] = recorded(a).get("pair")
    out["my_cr8_T0"] = results["T0"]["facts_mine"]["cr8"]
    out["reads"] = results
else:
    results = {}
    E_ids, E_vals = [], []
    for s in range(0, FACTS, CH):
        i, v = exhaustive8(codes[s:s + CH])
        E_ids.append(i); E_vals.append(v)
    E_ids, E_vals = torch.cat(E_ids), torch.cat(E_vals)
    wE = E_vals.softmax(-1)
    # F0
    t0 = time.monotonic()
    ids_all, w_all = [], []
    for s in range(0, codes_all.shape[0], CH):
        ids, wsc, _ = flat_read(codes_all[s:s + CH])
        ids_all.append(ids); w_all.append(wsc)
    ids_all, w_all = torch.cat(ids_all), torch.cat(w_all)
    et = end_task(ids_all, w_all, lambda q: flat_read(q)[:2])
    results["F0"] = {"counts": compare_counts(et, recorded("F0")), "lookup_misses": et["lookup_misses"], "facts_recorded": recorded("F0")["facts"],
                     "facts_mine": {"sr8": float((ids_all[:FACTS, :TOP].sort(1).values == E_ids.sort(1).values).all(1).double().mean())}, "seconds": round(time.monotonic() - t0, 1)}
    print("F0", json.dumps(results["F0"]), flush=True)
    seed = 298001
    idx = s1index.build_index(src.keys.detach(), seed, SLOTS // 64)
    for budget in (512, 2048):
        name = f"I64@{budget}/s{seed}"
        rec = recorded(name)
        t0 = time.monotonic()
        ids_all, w_all, st = [], [], {k: [] for k in ("cr8", "cr1", "sr8", "am_c", "am_s", "cand")}
        cand_diff = 0
        for s in range(0, codes_all.shape[0], CH):
            q = codes_all[s:s + CH]
            mask, cnt = ivf_mask(q, idx, budget)
            ids, wsc, _ = flat_read(q, mask)
            ids_all.append(ids); w_all.append(wsc)
            if s < FACTS:
                n_here = min(CH, FACTS - s)
                m32, c32 = s1index.candidate_mask(idx, q[:n_here], budget)  # the object under comparison: P10-S1's float32 mask
                cand_diff += int((m32 != mask[:n_here]).any(1).sum())
                e = E_ids[s:s + n_here]
                c8 = mask[:n_here].gather(1, e)
                sel8 = ids[:n_here, :TOP]
                st["cr8"].append(c8.double().mean(1)); st["cr1"].append(c8[:, 0].double())
                st["sr8"].append((sel8[:, :, None] == e[:, None, :]).any(-1).double().mean(1))
                st["am_c"].append((c8.double() * wE[s:s + n_here]).sum(1))
                st["am_s"].append(((sel8[:, :, None] == e[:, None, :]).any(1).double() * wE[s:s + n_here]).sum(1))
                st["cand"].append(cnt[:n_here].double())
        ids_all, w_all = torch.cat(ids_all), torch.cat(w_all)
        cand = torch.cat(st.pop("cand"))
        facts = {k: float(torch.cat(x).mean()) for k, x in st.items()}
        et = end_task(ids_all, w_all, lambda q, b=budget: flat_read(q, ivf_mask(q, idx, b)[0])[:2])
        results[name] = {"index_sha256_equal_record": idx.sha256() == rec.get("index_sha256"), "facts_mine": facts, "facts_recorded": rec["facts"],
                         "candidates_facts_mine": {"mean": float(cand.mean()), "p99": float(torch.quantile(cand, 0.99))}, "candidates_facts_recorded": rec.get("candidates_facts"),
                         "facts_whose_float64_candidate_set_differs_from_p10s1_float32_mask": cand_diff,
                         "counts": compare_counts(et, rec), "lookup_misses": et["lookup_misses"], "seconds": round(time.monotonic() - t0, 1)}
        print(name, json.dumps(results[name]), flush=True)
    out["reads"] = results
out["seconds"] = round(time.monotonic() - t_start, 1)
(OUT / f"tensors_{arm}_d{draw}_u{update}.json").write_text(json.dumps(out, indent=1))
print("DONE", out["seconds"])
```

### summarize_tensors_a2.py

```
"""Summarize the eight A2 tensors_*.json files (copy of ../audit-p10ir-a1/summarize_tensors.py): count agreement against the recorded reads. Run: python3 -B summarize_tensors.py"""
import glob, json, os
OUT = os.path.dirname(os.path.abspath(__file__))
lines, n_cmp, n_diff = [], 0, 0
worst_fact = 0.0
for p in sorted(glob.glob(f"{OUT}/tensors_*.json")):
    d = json.load(open(p))
    lines.append(f"== {os.path.basename(p)}: draw hashes equal manifest {d['draw_hashes_equal_manifest']}; keys equal raw tensor {d['keys_equal_raw_tensor']}; facts in table {d['facts_in_table']}; seconds {d['seconds']}")
    if "p10s1_tree_recall_recorded" in d:
        lines.append(f"   P10-S1 recorded tree_recall_of_exhaustive_top8 at this snapshot: {d['p10s1_tree_recall_recorded']}; my CR8(T0) {d['my_cr8_T0']}")
    for name, r in d["reads"].items():
        cnt = r["counts"]
        cdiff = []
        for p_ in ("A", "B"):
            c = cnt[p_]
            n_cmp += 2
            for k in ("correct", "useful"):
                if c[f"mine_{k}"] != c[f"rec_{k}"]:
                    n_diff += 1
                    cdiff.append(f"{p_}.{k} {c[f'mine_{k}']} vs {c[f'rec_{k}']}")
        fm, fr = r.get("facts_mine", {}), r.get("facts_recorded", {})
        fd = []
        for k, v in fm.items():
            kr = "share_span_both" if k == "span" else k
            if kr in fr:
                n_cmp += 1
                dv = abs(v - fr[kr])
                worst_fact = max(worst_fact, dv)
                if dv > 1e-6:
                    n_diff += 1
                    fd.append(f"{k} {v:.6f} vs {fr[kr]:.6f}")
        g4 = r.get("gate4_vs_study_path")
        extra = ""
        if g4:
            extra = f" gate4[sets_differ {g4['sets_differ']}, ties {g4['float_ties']}, non-ties {g4['not_float_ties']}, max dw {g4['max_weight_diff']:.2e}]"
            n_cmp += 1
            if g4["not_float_ties"] or g4["max_weight_diff"] > 1e-6 or g4["float_ties"] > 0.001 * g4["facts"]:
                n_diff += 1
        if "pair_mine" in r and r.get("pair_recorded"):
            pm, pr = r["pair_mine"], r["pair_recorded"]
            for k in ("share_selected_changed", "tv_mean"):
                n_cmp += 1
                if abs(pm[k] - pr[k]) > 1e-6:
                    n_diff += 1
                    fd.append(f"pair {k} {pm[k]:.6f} vs {pr[k]:.6f}")
        if "candidates_facts_mine" in r:
            cm, cr = r["candidates_facts_mine"], r["candidates_facts_recorded"]
            n_cmp += 2
            for k in ("mean", "p99"):
                if abs(cm[k] - cr[k]) > 1e-9:
                    n_diff += 1
                    fd.append(f"candidates {k} {cm[k]} vs {cr[k]}")
            extra += f" index hash equal {r['index_sha256_equal_record']}; float64-vs-float32 candidate-set differences {r['facts_whose_float64_candidate_set_differs_from_p10s1_float32_mask']}"
        a = (cnt["A"]["mine_useful"] + cnt["B"]["mine_useful"]) / 65536
        lines.append(f"   {name:16s} a_use {a:.4f} i(A,B) {cnt['A']['mine_i']:.4f},{cnt['B']['mine_i']:.4f} CR8 {fm.get('cr8', float('nan')):.4f} AM_C {fm.get('am_c', float('nan')):.4f} counts {'EXACT' if not cdiff else cdiff} facts {'AGREE' if not fd else fd} misses {r['lookup_misses']}{extra}")
lines.append(f"COMPARISONS {n_cmp}; DIFFERENCES {n_diff}; largest |fact-measure difference| {worst_fact:.2e}")
text = "\n".join(lines)
print(text)
open(f"{OUT}/summarize_tensors.out.txt", "w").write(text + "\n")
```

### audit_route_ties_a2.py

```
"""Diagnose the facts whose float64 selection differs from the study float32 path (A2, 32K/16K). Setup copied from audit_tensors_a2.py.
Usage as audit_tensors_a2.py with arm T-OQ."""
"""Brute-force float64 recomputation of P10-I-R A2 (bridge) reads from the checkpoint tensors (auditor's own selection, weights, recall,
attention-mass, candidate and information code). The study code is called ONLY as the object under comparison (studies.p10ir.reads.tree_path,
for the per-fact gate-4-style comparison). P10-S1/P9 functions are used for the data draw, the backbone, loading model.pt, the oracle query
codes and the panel pass (derangement, address swap, answer scoring): the parts gate 2 already ties to P10-S1's registered counts.

Usage (one checkpoint per process):
  PYTHONPATH=<worktree> PYTHONDONTWRITEBYTECODE=1 PYTHONPYCACHEPREFIX=<scratch>/pycache <worktree>/.venv/bin/python -B audit_tensors.py <T-OQ|F-OQ> <draw> <update>
"""
import json, math, os, sys, time
from pathlib import Path

import torch
from torch.nn import functional as F

torch.set_num_threads(1)
torch.set_num_interop_threads(1)
torch.use_deterministic_algorithms(True)

W = Path("/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/arborlm-consolidation-experiment-2b31c1")
RUN = Path("/Users/daniellaloush/dandush03/ArborLM/experiments/P10IR-registered-20261118")
S1 = Path("/Users/daniellaloush/dandush03/ArborLM/experiments/P10S1-registered-attempt2-20261117")
EXP = Path("/Users/daniellaloush/dandush03/ArborLM/experiments")
OUT = Path(__file__).resolve().parent
TEMP, EPS, TOP, SOFT = 0.2, 1e-8, 8, 64
PER = 256
TIE, WTOL = 1e-5, 1e-6

from studies.p9 import controls, data as data_mod, core as p9core  # noqa: E402
from studies.p10s1 import core as s1core, evaluate as s1eval, index as s1index  # noqa: E402
from studies.p10s1.model import S1Memory, build_model  # noqa: E402
from studies.p10s1.train import load_model_state  # noqa: E402

arm, draw, update = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
FACTS, SLOTS = 32768, 16384
plan = json.load(open(W / "studies/p10ir/freeze/plan.json"))
item = [i for i in plan["items"]["A2"] if i["arm"] == arm and i["draw"] == draw and i["update"] == update and i["cell_name"] == "32K/16K"][0]
out = {"item": item["id"], "arm": arm, "draw": draw, "update": update, "torch": torch.__version__, "threads": torch.get_num_threads()}
t_start = time.monotonic()


# --- my float64 helpers ---------------------------------------------------------------------------------------------------
def unit64(x):
    x = x.detach().to(torch.float64)
    return x / x.norm(dim=-1, keepdim=True).clamp_min(EPS)


def top_ids(scores, k):
    """Top k per row by score descending, ties to the lower column id. Exact: topk(k+16), then lexicographic sort; rows whose (k+16)-th value equals the k-th fall back to a full stable sort."""
    extra = min(scores.shape[1], k + 16)
    vals, idx = scores.topk(extra, dim=1)
    # lexicographic (-score, id) within the candidates
    o1 = idx.argsort(dim=1, stable=True)
    vals, idx = vals.gather(1, o1), idx.gather(1, o1)
    o2 = (-vals).argsort(dim=1, stable=True)
    vals, idx = vals.gather(1, o2), idx.gather(1, o2)
    if extra < scores.shape[1]:
        unsafe = vals[:, k - 1] <= vals[:, extra - 1]
        if bool(unsafe.any()):
            full = (-scores[unsafe]).argsort(dim=1, stable=True)[:, :extra]
            idx[unsafe] = full
            vals[unsafe] = scores[unsafe].gather(1, full)
    return vals[:, :k], idx[:, :k]


def fano(acc):
    e = 1.0 - acc
    h = 0.0 if e <= 0 or e >= 1 else -(e * math.log2(e) + (1 - e) * math.log2(1 - e))
    return 5.0 - h - e * math.log2(31)


def chance_high(n, tests=40, alpha=0.001, p=1 / 32):
    tail, acc = alpha / tests / 2, 0.0
    for k in range(n, -1, -1):
        acc += math.exp(math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1) + k * math.log(p) + (n - k) * math.log1p(-p))
        if acc > tail:
            return k


HIGH = chance_high(FACTS)


def bits(useful, n):
    return 0.0 if useful <= HIGH else fano(useful / n)


# --- data, model -------------------------------------------------------------------------------------------------------------
seeds = s1core.seed_set(item["seed_name"], item["seed_base"])
corpus = p9core.load_trained_corpus(EXP)
data = data_mod.build_study_data(seeds, corpus, sizes=data_mod.DataSizes(main_trained=item["table_facts"], unseen=item["unseen"], lane_d_per_set=s1core.LANE_D_STUB))
man = json.load(open(plan["draw_manifests"][item["seed_name"]]["path"]))
out["draw_hashes_equal_manifest"] = man["sha256s"] == data.sha256s()
_cwd = os.getcwd()
os.chdir(W)  # P5/P4 parent verification reads repository-relative records (read only); back to the scratch folder at once
try:
    backbone = controls.load_backbone(p9core.PRIMARY_PARENT, EXP)[0]
finally:
    os.chdir(_cwd)
model = build_model(arm, SLOTS, item["init_seed"], backbone, r1_seed=seeds.r1_codes, hash_seed=s1core.h8_seed(seeds), seed_rng=False)
snap = RUN / "a2" / "train" / "cells" / item["cell"] / "snapshots" / s1core.snapshot_stem(update)
out["snapshot_dir"] = str(snap)
load_model_state(snap, model)
model.eval()
raw = torch.load(snap / "model.pt", weights_only=True, map_location="cpu")["model"]
src = model.addition
out["keys_equal_raw_tensor"] = bool(torch.equal(raw["addition.keys"], src.keys.detach()))
K = unit64(raw["addition.keys"])  # [N, 16]
RT = unit64(raw["addition.router"]) if arm == "T-OQ" else None
n_branches = SLOTS // PER
key_branch = torch.arange(SLOTS) // PER

all_ident = data.facts.ident
codes_all = s1eval.fact_codes(model, data, int(all_ident.shape[0]))  # [all facts, 16] float32 unit codes (the query)
codes = codes_all[:FACTS]
out["facts_in_table"] = int(all_ident.shape[0])
out["code_norm_max_dev"] = float((codes.double().norm(dim=1) - 1).abs().max())


# --- my tree read ------------------------------------------------------------------------------------------------------------
def tree_read(q32, v, ps, pw, k=SOFT):
    q = q32.to(torch.float64)
    cos = q @ K.T / TEMP
    routes = q @ RT.T / TEMP
    prior = routes.log_softmax(-1)
    _, border = top_ids(routes, n_branches)
    visited = border[:, :v]
    in_c = torch.zeros(q.shape[0], n_branches, dtype=torch.bool).scatter_(1, visited, True)[:, key_branch]
    kp = prior[:, key_branch]
    sel = (cos + kp) if ps else cos.clone()
    sel = sel.masked_fill(~in_c, -math.inf)
    _, ids = top_ids(sel, k)
    wsc = ((cos + kp) if pw else cos).gather(1, ids)
    sel_sc = sel.gather(1, ids)
    return ids, wsc, sel_sc, in_c, visited, routes


def flat_read(q32, cand=None, k=SOFT):
    q = q32.to(torch.float64)
    cos = q @ K.T / TEMP
    sc = cos if cand is None else cos.masked_fill(~cand, -math.inf)
    _, ids = top_ids(sc, k)
    return ids, cos.gather(1, ids), sc.gather(1, ids)


def ivf_mask(q32, idx, minimum):
    q = q32.to(torch.float64)
    unit = unit64(idx.centroids)
    sc = q @ unit.T
    order = (-sc).argsort(dim=1, stable=True)
    cum = idx.sizes.to(torch.int64)[order].cumsum(1)
    reached = cum >= minimum
    need = torch.where(reached.any(1), reached.to(torch.int64).argmax(1), torch.full((q.shape[0],), idx.lists - 1))
    rank = torch.empty_like(order).scatter_(1, order, torch.arange(idx.lists).expand(q.shape[0], -1).contiguous())
    visited = rank <= need[:, None]
    return visited.gather(1, idx.assign[None, :].expand(q.shape[0], -1)), cum.gather(1, need[:, None]).squeeze(1)


def exhaustive8(q32):
    q = q32.to(torch.float64)
    cos = q @ K.T / TEMP
    v, i = top_ids(cos, TOP)
    return i, v



# --- diagnosis of the v=2 set differences against the study's float32 path (auditor's addition) -----------------------------
from studies.p10ir import reads as p10ir_reads  # object under comparison only
keys32, router32 = src.keys.detach(), src.router.detach()
rows = []
for name, (v, ps, pw) in {"T0": (2, True, True), "T1": (2, False, False), "T1w": (2, True, False), "T3": (64, True, True), "Tv8_on": (8, True, True)}.items():
    for s in range(0, FACTS, 512):
        q = codes_all[s:s + 512]
        ids, wsc, selsc, in_c, visited, routes = tree_read(q, v, ps, pw)
        ref = p10ir_reads.tree_path(keys32, router32, q, v, ps, pw, per=PER, chunk_elements=1 << 20)
        same = (ids[:, :TOP].sort(1).values == ref.ids[:, :TOP].sort(1).values).all(1)
        for j in (~same).nonzero().flatten().tolist():
            r64 = routes[j].sort(descending=True).values
            r32 = ref.routes[j].sort(descending=True).values
            vb = set(visited[j].tolist())
            vb32 = set(ref.routes[j].double().argsort(descending=True)[:v].tolist())
            rows.append({"read": name, "fact": s + j, "route_gap_v_vs_v+1_f64": float(r64[v - 1] - r64[v]) if v < n_branches else None, "route_gap_f32": float(r32[v - 1] - r32[v]) if v < n_branches else None,
                         "visited_same_as_f32_order": vb == vb32, "sel_gap8_9_f64": float(selsc[j, TOP - 1] - selsc[j, TOP]),
                         "mine_minus_theirs": sorted(set(ids[j, :TOP].tolist()) - set(ref.ids[j, :TOP].tolist())), "theirs_minus_mine": sorted(set(ref.ids[j, :TOP].tolist()) - set(ids[j, :TOP].tolist()))})
print(json.dumps(rows, indent=1))
(OUT / f"route_ties_{arm}_d{draw}_u{update}.json").write_text(json.dumps(rows, indent=1))
```

### failed_attempts.txt

```
attempt 1 of audit_labels_a2.py: KeyError 'plateau' at U_P checkpoint (the plateau block exists only at RUN); fixed by checking plateau at RUN only
attempt 1 of audit_integrity_a2.py: KeyError 'returncode' (some stage manifests' tasks have no returncode field); fixed with .get(returncode, 0)
attempt 1 of audit_route_ties_a2.py: IndexError at v=64 (T3: no v+1-th branch); fixed by recording None there
```
