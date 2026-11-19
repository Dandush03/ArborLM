# P10-I-S6 implementation audit, scientific core at commit 7b1383a (ADR-0031)

- Auditor: `arbor-auditor` subagent, Claude Opus 5.5 (model id claude-opus-5-5), 2026-11-19. Independent engineering and mathematical evidence only. It is not Astra validation and not a human approval. `Astra review: NOT_PERFORMED`.
- Object: `git archive 7b1383a` of branch `claude/p10-i-s6-impl`, unpacked read-only into `/Users/daniellaloush/dandush03/ArborLM-sealed/audit-s6-a1/` (outside every repository). I did not read the implementer's live worktree except `git log` for commit messages. I made no git writes. I used no network, did no real training, opened no sealed value, and ran one process at a time with `timeout`.
- Environment: macOS arm64, `uv run --locked` in the archive copy (it created its own `.venv` there), Python 3.12.14, torch 2.8.0. Every command was run from the archive root with `PYTHONPATH=$PWD timeout <s> uv run --locked python _audit/<script>`. Scripts are in `/Users/daniellaloush/dandush03/ArborLM-sealed/audit-s6-a1/_audit/`; the two key ones are appended below.
- Not available to me: the implementer's list of departures and its own choice of "two loosely-written tests". Neither is in the commits (the commit bodies are empty) or in `experiments/_scratch`. Section 6 gives the tests I judge to be loose.

## Verdict: CORE SOUND AFTER LISTED FIXES

I found no blocking defect. Line P, the classes, K\*, R, j†, the convergence rule, the trend line, D[FLAT], the NOT EVALUABLE causes, calibration selection, the corpus pipeline and the model layer all agree with my own reimplementations. Three required fixes apply to code that exists now (R1–R3). One of them, R1, favours the memory in what is printed beside the label. Two required items (R4, R5) are conditions on the code that is not yet written.

## Evidence, with the command for each number

| Check | Command (from the archive root) | Result |
|---|---|---|
| Line P, classes, K\*, R, j†, trend tag, D[FLAT], causes, sentence: my reference (`_audit/ref_labels.py`, imports nothing from the study) against `analysis.analyse` on random worlds. The worlds use dyadic values, run sharing in 40% of worlds, k_max of 2, 3 or 4, and failures, integrity breaks, BASE faults, collapsed cells and non-finite interventions. | `fuzz_labels.py 400 0` and `fuzz_labels.py 2000 400` | 2,400 worlds. Every row 1–12 was reached (row counts 262/80/47/186/116/146/65/470/174/133/294/427) and all ten trend tags. 0 divergences in row, label, ONE DOUBLING, K\*, R, j†, the class at every rung, tag, D[FLAT] and cause ids. The only divergences were in R16 (finding R1). |
| Line P's result space, exhaustively | `enum_linep.py` | 4,089,564 cases (every convergence state, including NOT DETERMINED, for each arm at each rung × every class vector, for k_max = 0..3, and 40 random class vectors per state at k_max = 4). Exactly one row each, no exception, 0 disagreements with my row logic. |
| Trend tag space | `enum_trend.py` | 434 cases (every HELD vector for k_max 0..4 × Δ at and around ±0.005). 0 disagreements. Every text ends with the fixed sentence. |
| Summation (G5) | `naive_vs_sum.py 2400 0`, plus a direct probe | The probe confirms that builtin `sum` in 3.12.14 is compensated: `sum([0.1]*10) == 1.0`, while naive accumulation gives 0.9999999999999999. On my dyadic worlds the two methods never changed a result, which is expected because dyadic values add exactly. |
| Rate selection, interior flag and extension rule against my own selection | `fuzz_calibration.py` | 3,000 random curve sets on the grid with up and down extensions and non-finite values. 0 disagreements. |
| Corpus rules 1–4, the mod-2 fallback and `reproduces_select`, against my brute force | `fuzz_corpus.py` | 300 random row sets: headings, sub-headings, preambles, multibyte text, duplicates inside and across articles, E hits. 0 disagreements. `reproduces_select` matched `pilot_data.select` in every case. |
| Model layer at moderate size (512 updates per arm, 4,096 rows, panel of 64 chunks) | `model_checks.py` | Trainable parameters 198,145 and 198,401, so 792,580 and 793,604 bytes. Multiply-adds from the shapes are 67,328 and 198,400 (ratio 2.94 against 67,456). Replay equals enabled bitwise, and disabled equals BASE bitwise, for both arms. The reads create no gradients. P_used moves all 2,013 used rows and leaves the unused rows identical. The V_mean read is constant across positions to 1.19e-7. NEG-REF on the trained memory passes. Peak RSS 306 MB. |
| The implementer's oracle coverage | `oracle_coverage.py` | The implementer's 40 oracle seeds reach rows 9, 11 and 12 only (counts 9/9/22). |
| The implementer's tests | `timeout 1500 uv run --locked pytest -q -p no:cacheprovider tests/test_p10i_s6_*.py` | 117 passed, 1 failed. The failure is `test_run_directory_must_be_ignored_or_outside`, because my copy is not a git work tree (A12). |

## Findings

### REQUIRED

**R1. R16 is computed and can print "REPLICATED AT 16,384" when line P is MEMORY UNSTABLE or NOT EVALUABLE by a failed dense cell. This favours the memory.**
- Where: `studies/p10i_s6/analysis.py:231` (`integrity_stop` covers only causes 1–2) and `labels.py:212–230`.
- Specification: G17, "R16 follows line P's integrity and failed-cell state".
- What the code does: it makes R16 NOT EVALUABLE only for causes 1–2, or when a rung-0 cell is undefined.
- Concrete input (`_audit/r16_concrete.py`, on the implementer's own `synthetic` builder): flat lead +0.02, both arms converging, and `failed={("M-FLAT",4,0)}`. The printed result is `MEMORY UNSTABLE (FAILED CELLS) | R16: REPLICATED AT 16,384 | trend: TREND NOT DETERMINED`. With `failed={("D-ADAPT",4,0)}` it is `NOT EVALUABLE (a D-ADAPT run that a rule reads is a failed cell) | R16: REPLICATED AT 16,384`.
- Size: the fuzz gives 83 such cases in 2,400 worlds (the `r16_detail.py 400 0` breakdown: row 2; row 1 with cause 3; row 1 with cause 4).
- Why it matters: a favourable replication readout appears beside a failure label, and it contradicts the trend line's TREND NOT DETERMINED.
- Fix: pass line P's row-1/2 state to `replication`. Whether cause 4 alone should also suppress R16 is for the lead (L1).

**R2. "CALIBRATION NOT INTERIOR" is never enforced. Direction neutral.**
- Where: `calibration.py:63–75`. The docstring of `rate_table` says it "Raises `EngineeringStop` if the edge persists", but it only records `interior[arm][k] = False`.
- The freeze (`stages.py`, `cmd_freeze`, about lines 495–525) compares the three rate tables but never reads `interior`. No code outside the unwritten R1 driver consumes `extension_decision(...)["stop"]`.
- Specification, section 8: "If a minimiser is still at an edge after these extensions: ENGINEERING STOP … No registered run carries a RATE-AT-EDGE tag."
- Failing input: any rate table with an `interior` flag False freezes.
- Fix: make `rate_table` (or `public_summary`) raise, and make the freeze refuse unless every interior flag at every rung −1..k_max is True for both arms.

**R3. The analysis loosens the integrity equalities to 1e-6 when the analysing machine is not the platform of record. Neutral; it hides cause 2.**
- Where: `stages.py:387` passes `bitwise=gates.on_platform_of_record(cfg)` to `analysis.analyse`; `analysis.py:30–31` and `289–311` (the OA block) then compare with tolerance.
- The comparisons are between recorded floats, so the analysing platform is irrelevant. A disabled ≠ BASE or replay ≠ enabled difference below 1e-6 would silently stop being a NOT EVALUABLE cause (section 11: "Every other identity compares the same computation bitwise"; section 12.2 item 2).
- Fix: always compare exactly in the analysis. Keep the platform condition for the gates that recompute.

**R4. Conditions for the P0 command, which is not written yet.**
- `parents.train_new_parents` (`parents.py:84–103`) does not check that `identity_gate` passed.
- It also accepts an existing `<group>NN.pt` as "verified" by reading the digest stored inside the file, without recomputing `backbone_digest` of the stored state.
- Section 7 requires the identity gate on all nine old parents to pass "before any new parent is trained".
- Fix: P0 refuses to train unless an `adapter_identity` record with `passed: true` and nine bitwise-equal digests exists. An existing file is accepted only if its recomputed digest equals the stored one. Otherwise it is kept aside and the parent retrained, with the attempt logged.

**R5. Conditions for the D0 command, which is not written yet.** The functions are correct (fuzz above). The command must also do the following:
- (a) Build E from both the WikiText-2 train and validation parquets (G7).
- (b) Number rows across the WikiText-103 train files in lexicographic file order (rule 3(1)). `fetch.plan_from_listing` sorts, and D0 must read in that order.
- (c) Give the panel walk an excluded set that contains every span in `data/p10i-shared/panel_ledger.json` and P10-I-S3's two panels. The ledger stores byte offsets in the concatenated validation rows, while `walk_panels` overlaps `(row, start, end)` spans, so a conversion is needed and should be tested. With that set, starting at rank 8,192 (the config's `panel_walk_start`, the same start as P10-I-S3) is equivalent to "continuing after" P10-I-S3's panels: every rank in P10-I-S3's range that P10-I-S3 skipped overlapped a span that is still excluded.
- (d) Append the two new panels to the shared ledger.
- (e) Write the download rows into the project's existing `DOWNLOAD_LEDGER.md` with its running total (section 6.3 states 1,188,183,868 bytes before this download), not only into the new `DOWNLOAD_LEDGER_S6.*`. Section 6.3 requires one row per file before the fetch (URL at the pinned revision, LFS size and SHA-256), completed after it.
- (f) Measure and record RSS against 8 GiB.
- (g) Run both gates of rule 3: the first 4,096 WikiText-2 ranks hashed against the recorded SHA-256, and zero overlap with E.

### ADVISORY

- **A1.** `analysis.py:199–201`: a missing `used_slots` statistic gives `None`, which is treated as not COLLAPSED. This would favour the memory, but `items.run_eval` cannot produce it. Make a missing statistic an INCOMPLETE REGISTRY.
- **A2.** `items.py:204–211`: a non-finite replay after a finite enabled read raises `FailedCell` (the default of `evaluate` is `nonfinite="raise"`). That turns every read into None, a failed cell. For M-FLAT this gives row 2 where section 12.2 item 2 gives row 1. Both outcomes are against the memory; it is a precedence slip only.
- **A3.** `analysis.py:104–111`: a non-finite enabled NLL at one snapshot fails only the rungs that read that snapshot. Section 12.2 says L at "the rungs that run serves" is NOT DETERMINED. Labels are unaffected, because any failure gives row 1 or 2, but per-rung L values and D[FLAT] at R are printed where the ADR says not determined.
- **A4.** `model.py:123–137`, `snapshots_equal`, compares content with `torch.equal`. Section 16 asks for bitwise equality of the state; it does not ask for file hashes. Comparing content tensor by tensor is an acceptable reading, but `torch.equal` treats −0.0 and +0.0 as equal. Compare `t.view(torch.uint8)` (as `state_digest` does) to make it bytewise. The comparison also omits the snapshot's `identity` field, which is acceptable.
- **A5.** The implementer's oracle test (`tests/test_p10i_s6_analysis.py:286–378`):
  - It is independent of `labels` and `analysis`.
  - It shares `synthetic.registry` and the key scheme, so it cannot catch a key-scheme defect.
  - It uses naive accumulation, not G5's builtin `sum`.
  - It reaches only rows 9, 11 and 12.
  - `synthetic.registry` never shares a run across rungs, so the analysis tests do not exercise run sharing, which is the expected real case. My fuzz does (40% of worlds) and agrees.
- **A6.** Loose tests:
  - `test_two_rungs_swapped_changes_the_result` (line 180) asserts `label != … or per_rung != …`. That holds for any change of value, so it does not show what requirement 7 asks for, namely that the known-answer test fails on swapped records.
  - Line 262 (`== "UNDECIDED" or != "M-AHEAD"`) is a disjunction where an exact class is known (LEVEL).
- **A7.** Test and template seeds:
  - `testing.synthetic_backbone` uses `PilotModel("dense_small", 42 + k)`, which are P1's registered seeds 42–44 (registry rows 5, 13, 14). It is also used as the load template in `stages.real_resources`; its values are overwritten there.
  - The planted toy uses P10-I-S3's `plant(..., seed=1)`, and the config's allocated `init_planted_toy = 330793` is never used.
  - Use test-range seeds, or record the reuse.
- **A8.** `stages.run_analysis` does not assert 27 cells and 27 OA cells in registered mode. Denominators are never reduced.
- **A9.** Descriptive output of section 12.5 that is missing:
  - the per-parent envelope δ (only the run's δ per parent is printed);
  - X_mean_dense;
  - calibration-versus-registered convergence states (`calibration_states` is never passed);
  - cell, parent and seed statistics at 8,192.
- **A10.** `p_used_values` and `neg_ref_values` build their tensors outside `no_grad`, so an autograd graph is formed. This is harmless: evaluation runs under `no_grad` and no backward pass is made.
- **A11.** `parents.py`: the adapter also builds the control memory `Memory("learned_tree", 201)` for new parents. G9 says it is "not constructed", with 201 a declared re-use only if the gate needs it. It is harmless (built after the backbone, frozen, not in the optimizer), but it is a departure that should be stated.
- **A12.** `test_run_directory_must_be_ignored_or_outside` fails outside a git work tree. Requirement 5 says tests should not depend on repository state.
- **A13.** `items.run_train` deletes a partial item directory on restart (`shutil.rmtree`). Requirement 4 says every discarded attempt is kept.

## Readings that need the lead's ruling — PENDING LEAD REVIEW

- **L1.** G17 scope. Does R16 become NOT EVALUABLE under row 2 and under cause 3? I read the text as yes (R1). Under cause 4 alone (Cd(R) < 0.005 at R ≠ 0)?
- **L2.** A COLLAPSED cell, or a non-finite intervention in one cell, makes the P_used or X_mean mean undefined, so F2 or F3 fails whole. The ADR literally fails only "that cell's condition", but "no mean over fewer cells" supports the implementer. The implementer's reading favours the dense arm.
- **L3.** A missing BASE record is read as NOT EVALUABLE cause 1, not as ENGINEERING STOP — INCOMPLETE REGISTRY. The text supports both.
- **L4.** The panel walk starts at rank 8,192 with P10-I-S3's panels among the excluded spans (equivalent under R5(c)). Article 0 is the preamble before the first heading, and articles are numbered after the exclusion, chunkless articles included. These are literal and acceptable in my judgement.
- **L5.** OA's convergence is read by δrun only (no OA run at r(arm, −1)).
- **L6.** A text inconsistency in 12.6. "Tag 2 occurs exactly when R16 is not REPLICATED" is false when R16 is NOT EVALUABLE by its rung-0 dense floor while HELD(0) is true, and under R1's cases. The code follows the HELD definition, which is the rule.

## What I did not audit

- `plan.py`, `runner.py`, `cost.py`, `launch/`, `printing/`, the freeze and caps arithmetic, process families, the pause mechanism end to end.
- The fetch beyond its listing and hard stop.
- `public_guard` beyond reading it.
- The seed gate. I did not run the r4 checker.
- The adapter identity gate against the real P2/P3 records. That needs the platform of record and the real parquet; I judged it non-vacuous by reading it: it compares full-backbone digests after 1,024 updates with the P4 records.
- The NEG-REF and planted gates on real calibration checkpoints.
- The R1, R2 and R3 drivers and the D0 and P0 commands, which do not exist yet.
- Anything sealed.

## My own discrepancies and mistakes, kept

1. `model_checks.py` used the implementer's `testing.synthetic_backbone(0)`, which seeds P1's registered value 42. That departs from my brief's "test-range seeds only". No training of any registered object took place; the other seeds I used are 952101–952206.
2. In `fuzz_corpus.py` I expected `"=  A  ="` not to be a heading. Under rule 1's literal text it is a heading (the third character is a space). The code is right and my expectation was wrong.
3. My reference's "integrity only" R16 variant counts a rung-0 cell that failed only through its δrun read at 8,192 as defined. The implementer counts it as undefined. That gave 8 divergences (`r16_vs_integrityonly`); they come from my reference, not the code.
4. `fuzz_labels.py` first failed with `ModuleNotFoundError: studies` (no `PYTHONPATH`); I reran it with `PYTHONPATH=$PWD`.

## Appended scripts

### `_audit/ref_labels.py`

```python
# Independent reference of ADR-0031 sections 4, 9, 10, 11, 12 (auditor, written from the ADR text).
# Imports NOTHING from studies.p10i_s6 or studies.p10i_s3.  Pure Python.
# World model (my own):
#   w["k_max"]; w["n"] cells (27); parents = n // 3
#   w["U"][k] update count for k = -1..k_max
#   w["rate"][arm][k]  rate value used at rung k
#   w["runs"][(arm, rate, c)] = {"failed": bool, "vals": {u: enabled or None}, "replay": {u: v}, "disabled": {u: v},
#                                "pu": {u: [4 draws or None]}, "xm": {u: v or None}, "vm": {u: v or None}, "slots": {u: int}}
#   w["base"][p] = (enabled or None, replay or None)
# Every comparison as written; means = builtin float sum in cell order / count (ruling G5).

ARMS = ("M-FLAT", "D-ADAPT")
FLAT, DENSE = ARMS
EFF, MINC, MINP, EPS, HALF, SHARE, FLOOR, TOL = 0.005, 22, 8, 0.001, 0.5, 0.90, 0.005, -0.005


def SUM(xs, naive=False):
    if naive:
        t = 0.0
        for x in xs:
            t += x
        return t
    return sum(xs)


class Ref:
    def __init__(self, w, naive=False):
        self.w, self.naive = w, naive

    def mean(self, xs):
        if any(x is None for x in xs):
            return None
        return SUM(xs, self.naive) / len(xs)

    def pmeans(self, xs):
        return [self.mean(xs[i:i + 3]) for i in range(0, len(xs), 3)]

    # ---------------------------------------------------------------- reads a rule makes
    def enabled(self, arm, k, c, at_k):
        """enabled NLL of the run at r(arm,k) at update U_{at_k}; ('F', None) if the run failed (no record)."""
        r = self.w["runs"][(arm, self.w["rate"][arm][k], c)]
        if r["failed"]:
            return "F", None
        return "ok", r["vals"][self.w["U"][at_k]]

    def solve(self):
        w, n, km = self.w, self.w["n"], self.w["k_max"]
        P = n // 3
        B = {}
        cause1 = False
        for p in range(P):
            e, rp = w["base"][p]
            if e is None or rp is None or e != rp:
                cause1 = True
            B[p] = e
        fail = {a: {k: [False] * n for k in range(-1, km + 1)} for a in ARMS}
        H = {a: {k: [None] * n for k in range(-1, km + 1)} for a in ARMS}
        prev = {a: {k: [None] * n for k in range(0, km + 1)} for a in ARMS}
        cause2 = False
        for a in ARMS:
            for k in range(-1, km + 1):
                rate = w["rate"][a][k]
                for c in range(n):
                    run = w["runs"][(a, rate, c)]
                    if run["failed"]:
                        fail[a][k][c] = True
                        continue
                    u = w["U"][k]
                    e = run["vals"][u]
                    if e is None:
                        fail[a][k][c] = True
                    else:
                        H[a][k][c] = e
                        # integrity of this evaluation (it exists and a rule reads it)
                        b = B[c // 3]
                        if run["replay"][u] != e or b is None or run["disabled"][u] != b:
                            cause2 = True
                    if k >= 0:
                        pv = run["vals"][w["U"][k - 1]]
                        if pv is None:
                            fail[a][k][c] = True
                        prev[a][k][c] = pv
        # a failed cell on a run makes L at every rung that run serves ND (sec 12.2) -- for the label only "any" matters
        anyfail = {a: any(any(fail[a][k]) for k in range(-1, km + 1)) for a in ARMS}

        def Lm(a, k):
            if any(fail[a][k]):
                return None
            return self.mean(H[a][k])

        L = {a: {k: Lm(a, k) for k in range(-1, km + 1)} for a in ARMS}
        st = {}
        dl, dr = {}, {}
        for a in ARMS:
            st[a], dl[a], dr[a] = {}, {}, {}
            for k in range(0, km + 1):
                d = None if L[a][k - 1] is None or L[a][k] is None else L[a][k - 1] - L[a][k]
                pm = None if any(fail[a][k]) else self.mean(prev[a][k])
                drr = None if pm is None or L[a][k] is None else pm - L[a][k]
                dl[a][k], dr[a][k] = d, drr
                st[a][k] = (d is not None and drr is not None and d < EPS and drr < EPS)
        kstar = None
        for k in range(0, km + 1):
            if all(st[a][j] for a in ARMS for j in range(k, km + 1)):
                kstar = k
                break
        R = kstar if kstar is not None else km
        # j dagger
        jd = None
        if all(L[DENSE][k] is not None for k in range(0, km + 1)):
            best = min(L[DENSE][k] for k in range(0, km + 1))
            jd = max(k for k in range(0, km + 1) if L[DENSE][k] == best)

        def Q(k):
            return [None if (H[DENSE][k][c] is None or H[FLAT][k][c] is None) else H[DENSE][k][c] - H[FLAT][k][c] for c in range(n)]

        def Qd(k):
            if jd is None:
                return [None] * n
            return [None if (H[DENSE][jd][c] is None or H[FLAT][k][c] is None) else H[DENSE][jd][c] - H[FLAT][k][c] for c in range(n)]

        def K3(q):
            m = self.mean(q)
            if m is None:
                return False
            return m >= EFF and sum(1 for x in q if x > 0) >= MINC and sum(1 for x in self.pmeans(q) if x > 0) >= MINP

        def behind(q):
            m = self.mean(q)
            if m is None:
                return False
            return m <= -EFF and sum(1 for x in q if x < 0) >= MINC and sum(1 for x in self.pmeans(q) if x < 0) >= MINP

        def cls(k):
            q, qd = Q(k), Qd(k)
            m = self.mean(q)
            if m is None or self.mean(qd) is None:
                return "ND"
            if K3(q) and K3(qd):
                return "M-AHEAD"
            if behind(q):
                return "D-AHEAD"
            if -EFF < m < EFF:
                return "LEVEL"
            return "UNDECIDED"

        classes = {k: cls(k) for k in range(0, km + 1)}
        Bc = [B[c // 3] for c in range(n)]

        def gain(vals):
            return [None if (b is None or v is None) else b - v for b, v in zip(Bc, vals)]

        causes = []
        if cause1:
            causes.append(1)
        if cause2:
            causes.append(2)
        if anyfail[DENSE]:
            causes.append(3)
        cdR = self.mean(gain(H[DENSE][R])) if not any(fail[DENSE][R]) else None
        if cdR is not None and cdR < FLOOR:
            causes.append(4)
        conv_end = {a: st[a][km] for a in ARMS}
        conv_prev = {a: (st[a][km - 1] if km >= 1 else False) for a in ARMS}
        one = False
        if causes:
            row = 1
        elif anyfail[FLAT]:
            row = 2
        elif kstar is not None:
            cs = [classes[k] for k in range(kstar, km + 1)]
            if len(set(cs)) > 1:
                row = 3
            else:
                row = {"M-AHEAD": 4, "LEVEL": 5, "D-AHEAD": 6, "UNDECIDED": 7}[cs[0]]
            one = kstar == km
        else:
            cd, cm = conv_end[DENSE], conv_end[FLAT]
            if cd and not cm and classes[km] == "M-AHEAD":
                row, one = 8, not conv_prev[DENSE]
            elif cm and not cd and classes[km] == "D-AHEAD":
                row, one = 9, not conv_prev[FLAT]
            elif (not cd) and cm:
                row = 10
            elif cd and not cm:
                row = 11
            else:
                row = 12
        # trend
        if row in (1, 2):
            tag = "TREND NOT DETERMINED"
        else:
            held = [K3(Q(k)) for k in range(0, km + 1)]
            if not held[0]:
                tag = "LEAD ABSENT AT RUNG 0"
            elif not all(held):
                k0 = min(k for k in range(0, km + 1) if not held[k])
                if not any(held[k0:]):
                    tag = f"LEAD LOST BY RUNG {k0}"
                else:
                    tag = "NOT MONOTONE"
            else:
                delta = self.mean(Q(km)) - self.mean(Q(0))
                tag = "LEAD SHRINKING" if delta <= -EFF else "LEAD GROWING" if delta >= EFF else "LEAD HELD AT EVERY RUNG"
        # R16 (my reading of G17: follows line P's integrity AND failed-cell state)
        def replication(cf, cdn, gate_rows):
            if gate_rows or any(x is None for x in cf) or any(x is None for x in cdn):
                return "NOT EVALUABLE"
            q = [a - b for a, b in zip(cf, cdn)]
            mq, mc, md = self.mean(q), self.mean(cf), self.mean(cdn)
            if md < FLOOR:
                return "NOT EVALUABLE"
            if K3(q):
                return "REPLICATED AT 16,384"
            k1 = mq >= TOL and sum(1 for x in q if x >= TOL) >= MINC and sum(1 for x in self.pmeans(q) if x >= TOL) >= MINP
            k2 = mc >= SHARE * md
            return "NOT REPLICATED (WITHIN TOLERANCE)" if (k1 and k2) else "NOT REPLICATED (otherwise)"

        r16_strict = replication(gain(H[FLAT][0]), gain(H[DENSE][0]), row in (1, 2))
        r16_integrity_only = replication(gain(H[FLAT][0]), gain(H[DENSE][0]), bool({1, 2} & set(causes)))
        # D[FLAT]
        if (1 in causes or 2 in causes) or any(fail[FLAT][R]):
            dflat = "NOT EVALUABLE"
        else:
            rate = w["rate"][FLAT][R]
            u = w["U"][R]
            C = gain(H[FLAT][R])
            pu, xm, col = [], [], []
            for c in range(n):
                run = w["runs"][(FLAT, rate, c)]
                h = H[FLAT][R][c]
                draws = run["pu"][u]
                slots = run["slots"][u]
                col.append(slots < 2)
                if slots < 2 or any(d is None for d in draws):
                    pu.append(None)
                else:
                    pu.append(SUM(draws, self.naive) / len(draws) - h)
                xm.append(None if run["xm"][u] is None else run["xm"][u] - h)

            def F1():
                m = self.mean(C)
                return m is not None and m >= EFF and sum(1 for x in C if x > 0) >= MINC and sum(1 for x in self.pmeans(C) if x is not None and x > 0) >= MINP

            def Fe(e):
                m = self.mean(e)
                cells = sum(1 for ci, ei in zip(C, e) if ci > 0 and ei is not None and ei >= HALF * ci)
                pmv = self.pmeans(e)
                return m is not None and m >= EFF and cells >= MINC and sum(1 for x in pmv if x is not None and x > 0) >= MINP

            f1, f2, f3 = F1(), Fe(pu), Fe(xm)
            dflat = "DEPENDENT" if (f1 and f2 and f3) else "CAPACITY WITHOUT DEMONSTRATED DEPENDENCE" if f1 else "NO CAPACITY"
        return {"row": row, "one": one, "kstar": kstar, "R": R, "jd": jd, "classes": classes, "tag": tag, "r16_strict": r16_strict, "r16_integrity_only": r16_integrity_only, "dflat": dflat, "causes": causes,
                "states": st, "L": L}
```

### `_audit/fuzz_labels.py`

```python
# Harness (auditor): random synthetic worlds -> (a) my reference (_audit/ref_labels.py, no study import)
# and (b) the implementer's analysis.analyse on a registry built with the implementer's key functions.
# Seeds: test range 952001..952999 only.  Usage: python _audit/fuzz_labels.py N [seed_offset]
import collections
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ref_labels as ref  # noqa: E402

from studies.p10i_s6 import analysis, core  # noqa: E402  (harness only; the reference does not import these)

CFG = core.load_config()
D = 2.0 ** -12
ROW_LABEL = {4: "PERSISTS AT CONVERGENCE", 5: "LEVEL AT CONVERGENCE", 6: "DENSE AHEAD AT CONVERGENCE", 7: "LEAD NOT ESTABLISHED AT CONVERGENCE", 3: "ORDERING NOT STABLE AFTER CONVERGENCE",
             8: "MEMORY AHEAD (DENSE CONVERGED, MEMORY STILL IMPROVING)", 9: "DENSE AHEAD (MEMORY CONVERGED, DENSE STILL IMPROVING)", 10: "CONVERGENCE NOT REACHED (DENSE STILL IMPROVING)",
             11: "CONVERGENCE NOT REACHED (MEMORY STILL IMPROVING)", 12: "CONVERGENCE NOT REACHED (BOTH STILL IMPROVING)"}


def q(x):
    return round(x / D) * D


def world(rng: random.Random, n=27):
    km = rng.choice([4, 4, 4, 3, 2])
    U = {k: core.rung_updates(CFG, k) for k in range(-1, km + 1)}
    snaps = sorted({0, *U.values()})
    rateset = [0.001, 0.003, 0.01]
    share = rng.random()
    rate = {}
    for a in ref.ARMS:
        if share < 0.4:
            r0 = rng.choice(rateset)
            rate[a] = {k: r0 for k in range(-1, km + 1)}
        else:
            rate[a] = {k: rng.choice(rateset) for k in range(-1, km + 1)}
    B = {p: 3.0 + p * 2.0 ** -6 for p in range(n // 3)}
    base = {p: (B[p], B[p]) for p in range(n // 3)}
    if rng.random() < 0.03:
        p = rng.randrange(n // 3)
        base[p] = (None, None) if rng.random() < 0.5 else (B[p], B[p] + D)
    incs = [0.0, 0.0005, 0.0009765625, 0.001, 0.0011, 0.002, 0.02, -0.001]
    lead_c = rng.choice([0.0, 0.003, 0.005, 0.0049, 0.0051, 0.006, 0.01, -0.005, -0.006, 0.02, -0.02])
    lead_slope = rng.choice([0.0, 0.0, 0.001, -0.001, 0.002, -0.003, 0.005])
    dgain0 = rng.choice([0.1, 0.1, 0.004, 0.006])
    noise_lvl = rng.choice([0.0, 0.004, 0.01, 0.03])
    pneg = rng.choice([0.0, 0.1, 0.18, 0.2, 0.3])
    runs = {}
    curve = {}
    for a in ref.ARMS:
        for r in set(rate[a].values()):
            g = {}
            acc = dgain0 if a == ref.DENSE else dgain0
            g[0] = 0.0
            mode = rng.random()
            for u in snaps[1:]:
                acc += rng.choice(incs) if mode < 0.7 else rng.choice([0.0005, 0.0009765625])
                g[u] = acc
            curve[(a, r)] = g
    ui = {u: i for i, u in enumerate(snaps)}
    cellnoise = {(c, u): (rng.choice([-1, 1]) * noise_lvl if rng.random() < pneg else rng.choice([0.0, noise_lvl / 2])) for c in range(n) for u in snaps}
    for a in ref.ARMS:
        for r in set(rate[a].values()):
            for c in range(n):
                b = B[c // 3]
                vals, rep, dis, pu, xm, vm, slots = {}, {}, {}, {}, {}, {}, {}
                for u in snaps:
                    g = curve[(a, r)][u]
                    if a == ref.FLAT:
                        lead = lead_c + lead_slope * max(0, ui[u] - 2) + cellnoise[(c, u)]
                        v = q(b - g - lead)
                    else:
                        v = q(b - g)
                    vals[u] = v
                    rep[u] = v
                    dis[u] = b
                    e = rng.choice([0.0005, 0.003, 0.01, 0.02, 0.05])
                    pu[u] = [q(v + e)] * 4
                    xm[u] = q(v + rng.choice([0.001, 0.01, 0.02]))
                    vm[u] = q(v + 0.01)
                    slots[u] = rng.choice([300] * 30 + [1, 2])
                    if rng.random() < 0.003:
                        pu[u][2] = None
                    if rng.random() < 0.002:
                        xm[u] = None
                runs[(a, r, c)] = {"failed": False, "vals": vals, "replay": rep, "disabled": dis, "pu": pu, "xm": xm, "vm": vm, "slots": slots}
    ev = rng.random()
    keys = list(runs)
    if ev < 0.04:
        runs[rng.choice(keys)]["failed"] = True
    elif ev < 0.07:
        k = rng.choice(keys)
        u = rng.choice(snaps[1:])
        runs[k]["vals"][u] = None
    elif ev < 0.09:
        k = rng.choice(keys)
        u = rng.choice(snaps[1:])
        runs[k]["replay"][u] = runs[k]["vals"][u] + D
    elif ev < 0.11:
        k = rng.choice(keys)
        u = rng.choice(snaps[1:])
        runs[k]["disabled"][u] = runs[k]["disabled"][u] + D
    return {"k_max": km, "n": n, "U": U, "rate": rate, "runs": runs, "base": base, "snaps": snaps}


def registry(w):
    reg = {}
    for p, (e, r) in w["base"].items():
        if e is not None:
            reg[core.base_key(p)] = e
        if r is not None:
            reg[core.base_key(p, core.READ_REPLAY)] = r
    for (a, rate, c), run in w["runs"].items():
        reg[core.run_key(a, rate, c)] = {"status": "failed_cell" if run["failed"] else "ok"}
        if run["failed"]:
            continue
        for u in w["snaps"]:
            v = run["vals"][u]
            if v is None:
                for rd in core.READS_OF[a]:
                    for d in (range(4) if rd == core.READ_P_USED else [0]):
                        reg[core.nll_key(a, rate, c, u, rd, d)] = None
                continue
            reg[core.nll_key(a, rate, c, u, core.READ_ENABLED)] = v
            reg[core.nll_key(a, rate, c, u, core.READ_REPLAY)] = run["replay"][u]
            reg[core.nll_key(a, rate, c, u, core.READ_DISABLED)] = run["disabled"][u]
            if a == ref.FLAT:
                for j in range(4):
                    reg[core.nll_key(a, rate, c, u, core.READ_P_USED, j)] = None if run["slots"][u] < 2 else run["pu"][u][j]
                reg[core.nll_key(a, rate, c, u, core.READ_X_MEAN)] = run["xm"][u]
                reg[core.nll_key(a, rate, c, u, core.READ_V_MEAN)] = run["vm"][u]
                reg[core.stat_key(a, rate, c, u, "used_slots")] = run["slots"][u]
            else:
                reg[core.nll_key(a, rate, c, u, core.READ_X_MEAN_DENSE)] = v + 0.001
    return reg


def compare(w, naive=False):
    mine = ref.Ref(w, naive=naive).solve()
    rt = {"rates": {a: {str(k): w["rate"][a][k] for k in range(-1, w["k_max"] + 1)} for a in ref.ARMS}}
    res = analysis.analyse(registry(w), rt, CFG, k_max=w["k_max"], bitwise=True)
    lp = res["line_p"]
    diffs = []
    if lp["row"] != mine["row"]:
        diffs.append(("row", mine["row"], lp["row"]))
    if lp["row"] >= 3 and lp["base_label"] != ROW_LABEL[lp["row"]]:
        diffs.append(("base_label", ROW_LABEL[lp["row"]], lp["base_label"]))
    if lp.get("one_doubling") != mine["one"] and lp["row"] >= 3:
        diffs.append(("one_doubling", mine["one"], lp.get("one_doubling")))
    if lp["row"] >= 3:
        for name, a, b in (("kstar", mine["kstar"], res["k_star"]), ("R", mine["R"], res["reading_rung"]), ("jd", mine["jd"], res["j_dagger"])):
            if a != b:
                diffs.append((name, a, b))
        for k in range(0, w["k_max"] + 1):
            if mine["classes"][k] != res["per_rung"][str(k)]["class"]:
                diffs.append((f"class{k}", mine["classes"][k], res["per_rung"][str(k)]["class"]))
    if not res["trend"]["tag"].startswith(mine["tag"]):
        diffs.append(("tag", mine["tag"], res["trend"]["tag"]))
    if res["r16"]["label"] != mine["r16_strict"]:
        diffs.append(("r16_vs_strictG17", mine["r16_strict"], res["r16"]["label"]))
    if res["r16"]["label"] != mine["r16_integrity_only"]:
        diffs.append(("r16_vs_integrityonly", mine["r16_integrity_only"], res["r16"]["label"]))
    if res["d_flat"]["label"] != mine["dflat"]:
        diffs.append(("dflat", mine["dflat"], res["d_flat"]["label"]))
    if sorted(lp["cause_ids"]) != sorted(mine["causes"]):
        diffs.append(("causes", mine["causes"], lp["cause_ids"]))
    # every row 3..12 label must carry the trend text and its fixed sentence
    if lp["row"] >= 3 and not lp["label"].rstrip("]").endswith("is not the label PERSISTS."):
        diffs.append(("trend_sentence", "present", lp["label"][-60:]))
    return mine, res, diffs


if __name__ == "__main__":
    N = int(sys.argv[1])
    off = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    rows = collections.Counter()
    kinds = collections.Counter()
    examples = {}
    tags = collections.Counter()
    for i in range(N):
        seed = 952001 + ((off + i) % 999)
        rng = random.Random(seed * 1000003 + off + i)
        w = world(rng)
        mine, res, diffs = compare(w)
        rows[res["line_p"]["row"]] += 1
        tags[res["trend"]["tag"].split(" (")[0][:22]] += 1
        for d in diffs:
            kinds[d[0]] += 1
            examples.setdefault(d[0], (off + i, d, res["line_p"]["row"], mine["row"]))
    print("worlds", N, "rows(impl)", dict(sorted(rows.items())))
    print("tags", dict(tags))
    print("divergences", dict(kinds))
    for k, v in examples.items():
        print("  first", k, v)
```

### `_audit/r16_concrete.py`

```python
# Auditor: concrete input for the R16 / G17 finding, on the implementer's own synthetic builder.
from studies.p10i_s6 import analysis, core, synthetic
from studies.p10i_s6.synthetic import ArmSpec, Spec
CFG = core.load_config()
def gains(s, d):
    g = {-1: s}
    for k, x in enumerate(d): g[k] = g[k - 1] + x
    return g
gd = gains(0.10, [0.0005] * 5); gf = {k: gd[k] + 0.02 for k in gd}
for failed in (frozenset({("M-FLAT", 4, 0)}), frozenset({("D-ADAPT", 4, 0)})):
    spec = Spec(ArmSpec(gf, {k: 0.0005 for k in range(5)}), ArmSpec(gd, {k: 0.0005 for k in range(5)}), p_used=lambda k, c: 0.08, x_mean=lambda k, c: 0.08, failed=failed)
    r = analysis.analyse(synthetic.registry(CFG, spec), synthetic.rate_table(4), CFG, k_max=4, bitwise=True)
    print(sorted(failed), "->", r["line_p"]["label"], "| R16:", r["r16"]["label"], "| trend:", r["trend"]["tag"])
```

Other scripts, kept in place and not appended: enum_linep.py, enum_trend.py, naive_vs_sum.py, fuzz_calibration.py, fuzz_corpus.py, model_checks.py, oracle_coverage.py, r16_detail.py.

`Astra review: NOT_PERFORMED`. Claude review is not Astra review.
