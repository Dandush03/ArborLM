# P10-I-S1 — narrow independent check before the freeze commit and Decision 2 (audit 3)

Auditor: arbor-auditor subagent, model Opus 5.5 (`claude-opus-5-5`), 2026-11-21. Independent engineering evidence. **Not Astra validation and not human approval.**

## Scope, environment and method

- **What was audited.** Worktree `agent-ab0efbf6bb233cc02`, branch `claude/p10-i-s1-impl`, HEAD `e9561de`, plus the uncommitted `studies/p10is1/freeze/freeze_record.json`.
- **What I last confirmed.** Audit 2 confirmed `8038f44`. Since then there are three commits: `260762b`, `bbf23cf` and `e9561de`.
- **Read only.** Nothing in the worktree was changed or run. There were no commits and no git writes. No sealed content was opened: the only sealed-side figure read is the calibration ledger's total, as carried in the projection.
- **Scripts and outputs.** All are in `/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/audit_s1_prefreeze3/`, each run under `timeout`:
  - `check_baseline.py` → `check_baseline_run1.out`, run with `/usr/bin/python3 -I` (3.9.6). It uses no study code.
  - `check_projection.py` → `check_projection_run2.out`, run with the worktree's `.venv/bin/python -I` (3.12.14) for `tomllib`. It uses no study code.
  - **Failed attempt, kept:** `check_projection_run1` failed with `ModuleNotFoundError: tomllib` because the system Python is 3.9. The rerun used 3.12.
  - `config_at_260762b.toml` is `git show 260762b:configs/p10is1_capacity.toml`.
- **Other read-only commands.** Inline Python reads of the rehearsal manifests, records, ledgers and plan; `git diff`/`log`/`show`/`ls-files`/`ls-tree`; `vm_stat`; `ps`.

## Verdict: READY FOR THE FREEZE COMMIT AND DECISION 2

There is no required code fix. One **required operational condition** applies to Decision 2: the machine-sharing plan of item 5 does not fit S1's memory guard on today's figures. The Decision 2 text must also carry disclosures D1–D4.

## 1. The baseline: **CONFIRMED**

**Committed copies.**
- `results/p10is1-quiet-baseline-20261121/record.json` (SHA-256 `62c031ec…47bd`) and `samples.jsonl` (`73da7c38…e4b5`) are byte-identical to `$E/P10IS1-quiet-baseline/first/`.
- The record names the same samples hash.

**Recomputed independently** (integer hundredths; nearest rank at ⌈95n/100⌉; twice the median for even n):
- Accepted attempt: session 1, attempt 2, 420 samples, indices 1–420.
- Window **P95 = 167, L = 217.** The ceiling (300) is respected, and L is below the 250 that triggers a report.
- T1 against T3: 2·median 238 vs 279, difference −41 (|·| ≤ 50 ✓). P95 151 vs 179, difference −28 (|·| ≤ 50 ✓). **Settled.**
- These equal the record's `accepted` block and the config.

**Raw conditions** at all 420 samples of the accepted attempt, re-checked from the raw fields rather than the recorded `failed` lists. All hold:
- no tool-call shell, no other study's process, no virtual machine;
- idle time ≥ 600 s (the minimum was 5,687 s);
- mains power, not Low Power Mode, no thermal line, one boot time;
- presence constant (application and Claude Code both present), `claude_pids` constant at [369, 370, 40449, 54306, 65713, 99328];
- largest gap 10.15 s; condition `open`.

**Attempt 1 (discarded).** At sample 202, `claude_pids` lost 39681, 39683 and 39685: three `claude` processes ended together. That is consistent with the other project's session ending, as `DISCLOSURE.md` infers. The discard is correct.

**Record fields.**
- `code_commit` = 260762b, `root` = the canonical root, `test_root` = false.
- Paused sessions 0/0, no fallback to closed.
- `quiet_rules_sha256` `e8dfcab4…` equals my own recomputation on both the HEAD config and the config at 260762b.

**SESSIONS.log.** One line (first, session 1, attempts 1–2, ACCEPTED). Its hash equals the committed samples file, which holds session 1 only.

**Changes since the code commit.** Between 260762b and HEAD, `studies/p10is1/**` and the config differ only in:
- the seven `[quiet]` hand entries: `baseline_provisional`, `load_p95`, `load_limit`, `app_present`, `cli_present`, `baseline_record_path` and `baseline_record_sha256`; `condition` was already "open" and is unchanged;
- `[caps] total_hours` 51 → 52;
- `freeze/plan.json` and one new file in `freeze/superseded/`.

No other configuration section changed.

## 2. Projection v2 against v1: **CONFIRMED; the disclosure is sufficient**

**What differs.** A key-by-key diff gives 20 differing leaves. Every one is H_c or follows from it:
- `h_charged_hours` 6.7037 → 7.9665; `typed_hours` 0 → 1.2628;
- `base_total_hours`, `budget_B_hours` and `total_hours`, each +1.2628 (or +0.6314 for B);
- the 12 `levels_considered[].total_hours_with_it`;
- `caps.total_cap_hours` and `config_caps.total_hours` 51 → 52;
- `sum_of_stage_caps_plus_charged` 58.70 → 59.97.

**What is identical:** `grants` (2K/256 786,432; 8K/1K 393,216; 32K/4K 786,432, each 4·U0), `remaining_hours` (21.927), `stage_hours`, `contention`, `workers`, `refused`, `closed` and status WITHIN BUDGET.

**The caps entered.** The committed `[caps]` equals v2's `config_caps` key by key: train 31, evaluate 1, timing 1, throughput 1, analysis 1, rehearsal 13, total 52.

**Disclosure.** Changelog row 21 (`origin/main`) states that only the charged hours changed, gives the reason, lists the grants as identical, gives 59.97 h against 60, and records that §11's "once" was departed from at the accounting ruling's direction. That meets the audit-2 condition. `DISCLOSURE.md` covers the machine sharing, not the projection, which is fine because row 21 carries it. **Suggestion (advisory):** copy row 21's text into the S1 branch, beside the plan (a `docs/` or `results/` note), so the freeze commit itself carries it.

## 3. The hand set-aside: **CANNOT AFFECT THE PLAN OR THE FREEZE**

- `superseded/plan-823b44a8e88f.json` (committed in 1332998) and `superseded/plan-823b44a8e88f-second-copy-20261121.json` have the same SHA-256, `823b44a8…b341`, equal to `plan.json` at `bbf23cf`. The step renamed a byte-identical copy.
- `candidate-plan` derives the plan from code, config, calibration, manifests and the projection. It never reads `superseded/`.
- **The plan's file-hash set** (`frozen_files`, 38 entries) matches both the working tree and `git show HEAD:<file>` for every entry, `uv.lock` included.
- The freeze directory (`plan.json`, `superseded/*`, `freeze_record.json`) is outside the set by design, so neither copy enters any hash.
- Plan SHA-256 = `e1479e36…1864`, equal to the rehearsal record's and `counting_start.json`'s.

## 4. The counting rehearsal: **CONFIRMED, real size; the cost difference is explained**

**Plan and size.**
- The rehearsal record names this plan (`e1479e36…`). `caps_provisional` is false. Item counts: train 155, evaluate 110, ladder 3, timing 16, throughput 35, baselines 15, gates/analysis/report 1. `item_problems` is empty.
- The R2 table covers rows 2,048, 8,192 and 32,768, each at fractions 1/16 to 1, with conditions a, b and c qualified.
- The view plan has 31 cells (one replicate, draw 1). 31 × 5 = 155.
- **Every one of the 31 cells trained to its planned length.** Flat cells reach 49,152 (R2 8,192); ladder cells reach U0 (98,304 or 196,608). Every planned snapshot up to that length exists. Full table in this audit's session log; 0 mismatches.

**Quiet stages.**
- **Timing:**
  - Quiet on the first poll: 1-min 124 and 5-min 168 against L 217; no failed condition; the same `claude_pids` as the baseline; idle 11,977 s.
  - End check passed, with the 1-min load at 123 after the delay.
  - The child watch ran 21 ticks with 0 failures, using 0.46 CPU-s in the child.
  - Load trace maximum 138. Top-ten at the start: the stage's own python; at the end, idle.
  - 16 items valid; **largest spread 0.0352** against 0.05. No re-timing and no discard. Charged 198 s against the 1-h cap.
- **Throughput:**
  - Poll 1 failed only `FIVE-MINUTE LOAD ABOVE L` (365, after evaluate). That is the five-minute rule working.
  - Poll 2, 600 s later, was quiet (139/163).
  - End check passed at 126. 19 watch ticks, 0 failures. Load trace maximum 200. Charged 181 s.
  - Top-ten at the start shows **`signpost_reporter` at 100 % CPU** (a macOS diagnostic process; see D3).

**Charged time.** The rehearsal ledger's non-pre-freeze sum is **1.3536 h**: gates 0.4 s, timing 198 s, train 3,867 s, ladder 330 s, evaluate 284 s, baselines 11 s, throughput 181 s. Waiting was 600 s, not charged. The pre-freeze ledger carries `counting-rehearsal` 4,873.7 s (= 1.354 h, wall minus waiting).

**Why 1.35 h against the projected 6.47 h.**
- `budget.project` costs the counting rehearsal as one replicate with **every ladder cell running to its full grant, 4·U0**, round by round. Its docstring says: "costed as if it used every granted level".
- In this rehearsal all three ladder cells were `all_full: True` at the first point (U0), so the ladder stopped at round 0. It cost 330 s instead of roughly 5 h. The incomplete rehearsal of 2026-11-19 stopped at the same points.
- Training was not short: one replicate took 1.07 h, against the projection's 5.60 h for five replicates (ratio 5.2).

**Nothing ran short of its length.** The projection is an upper bound by construction.

**Is the registered projection credible?**
- Of the 21.93 h "remaining", 6.47 h is this rehearsal. The registered stages are projected at about 15.45 h, of which the ladder is 9.58 h at full grants.
- If the registered draws are full at U0 as the rehearsal draw was, the registered run will take roughly 6–7 charged hours.
- If they need ladder rounds, up to about 15.5 h.
- Both fit the caps (item 5).

**D1 (disclosure for Decision 2).** No rehearsal has run `run_ladder_cell` beyond round 0 at real size. Neither this one nor that of 2026-11-19 trained a ladder cell past U0, evaluated the new snapshots and decided at a later point.
- **What exercises it:** the unit tests (segment resume bit for bit for every arm; next level; failed round; cumulative caps) and the calibration engine, which is separate code.
- **What does not:** the registered stage driver's continuation has run only in tests.
- **Severity: ADVISORY.** It is an engineering risk (a PAUSED or ENGINEERING STOP mid-run), not a label risk.
- **Option:** before the run, a one-cell forced-round smoke on rehearsal data. That is a new run and the lead's call.

## 5. Budget arithmetic

| Item | Hours |
|---|---|
| H_c in the plan and the registered ledger (calibration 6.483 + pre-freeze ledger at projection time 0.221 + typed 1.263) | 7.967 |
| This counting rehearsal (pre-freeze ledger; not in the registered ledger; budgeted inside the 13-h rehearsal cap) | 1.354 |
| **Charged before the freeze** | **9.320** |
| Registered stage caps: train+ladder 31, evaluate+baselines 1, timing 1, throughput 1, analysis+gates+report 1 | 35 |
| **Worst case, every registered cap spent** | **44.32 ≤ 60** |

- **The total cap.** The registered ledger total is 52 h, from 7.967. So up to 44.03 h is available to the registered stages, more than the 35 h of stage caps. The total cap cannot bind before a stage cap. The 59.97-h check already reserved 13 h for this rehearsal, which used 1.35 h.
- **Margins on the projection's figures.**
  - train key 31 h against 15.18 h, ladder at full grants (2.04×);
  - evaluate key 1 h against 0.125 h (8×);
  - timing 1 h against 0.055 h measured;
  - throughput 1 h against 0.05 h measured;
  - analysis 1 h against about 0.
  - **No cap is exhausted on the projection's figures.**
- **Sharing with P10-I-S2 Part T** (2 workers at about 8 GiB each) during S1's train and ladder.
  - *Measurement and labels: safe.* Timing and throughput run alone: S2's `studies.p10…` processes are refused at every reading, watch tick and end check, so S2 must be stopped before those two stages. Training is bit-exact regardless of load, by gate G4. A pause never changes a label (§16.1).
  - **Caps: not safe on today's memory (required operational condition).**
    - S1's runner adds a worker only when available memory covers its **aggregate guard of 18 GiB**.
    - Today, with no study running, available is **29.4 GiB** (`vm_stat`, the study's formula; 48 GiB total).
    - With S2 at 16 GiB, about 13 GiB would remain: under 18 GiB, so **S1 would stop adding workers.**
    - `run_tasks` charges **wall time**, so memory waiting is charged (unlike quiet waiting). After up to 6 h without memory the tasks go PAUSED — ENVIRONMENT.
    - A long memory stall plus fewer workers could reach the 31-h train cap, which is 2.04× the upper-bound projection, and pause the stage.
  - **Condition for Decision 2:** start S2 Part T alongside S1's train, ladder or evaluate only if `vm_stat` shows available ≥ 18 GiB + S2's peak (about 34 GiB). Otherwise run S2 before or after those stages, or with fewer or smaller workers.
  - Any cap extension is a resource decision under the standing delegation, never on outcome values.

## 6. The freeze record (uncommitted): **CONFIRMED**

- `plan_file_sha256` = `e1479e36…1864`, equal to `plan.json`.
- `rehearsal.sha256` = `87854244…c3d5`, equal to the rehearsal record file.
- `rehearsal_gate` passed: of this plan file, caps not provisional, nothing missing.
- `quiet_baseline`: 167/217, open, both presences, the record and samples hashes, `report_above` false.
- **G9:** passed with the **revision 3 checker** `seed_registry_check_r3.py`. Its SHA-256 `e4623604…7594` equals the expected value. Copy `34e42822…`, 10 allocation rows, result PASS. Roles: registered 160, calibration 64, rehearsal 32, test 288, initialisation 10, derived 50, declared reuse 38.
- **Revision 4 on `origin/main`** (`SEED_REGISTRY_R4.md`, `seed_registry_check_r4.py`) is not on this branch. It allocates only P10-I-S6 blocks: 320001–329999, 330701–330799 (and the spare 330801–330999) and 952001–952999. None overlaps S1's ranges (240001–240499, 249001–249199, 249201–249299, 330101–330199, 933001–933999). So revision 3 is sufficient for S1. The freeze record should say so (D2).
- **Re-derivation.** I did not re-run `freeze`, which writes. I confirmed the plan's 38 file hashes against HEAD and its config and `uv.lock` entries.

**What the freeze does not check that Decision 2 should know:**
- **D1:** the ladder continuation path has not run at real size (item 4).
- **D2:** G9 ran under revision 3, while revision 4 exists on `main`; there is no overlap.
- **D3:** the quiet-stage conditions do not see an OS process at full CPU, such as `signpost_reporter` at the start of the rehearsal's throughput stage; only the load does. Throughput is descriptive. For MC-T, the timing stage's per-item spread rule and the CPU-seconds measure are the guard. The rehearsal timing's largest spread was 0.0352.
- **D4:** the registered timing and throughput readings require the baseline's presences:
  - **application present and Claude Code present**: if the human lead quits the application, or no `claude` CLI runs, the reading is refused (not counted);
  - the set of Claude processes must stay unchanged through each measurement.

  The other project's post-window statement was never obtained (`DISCLOSURE.md`).

## 7. Anything else that should stop DECISION: RUN?

Nothing in the code or records. Before the run:
- **Commit** `freeze/plan.json`, `freeze/freeze_record.json` and nothing else (§8 of the run sheet). Make no later change in `studies/p10is1/**`, the config, `uv.lock`, `studies/p10s1`, `studies/p9*` or `src/arborlm`.
- **Memory:** the item 5 condition on sharing with S2.
- **Order:** the registered timing stage first and alone, with S0, S6 and S2 stopped and the Claude processes stable.
- **RUN directory:** the registered run directory is `$E/P10IS1-pre-20261118` (the run sheet's UNSURE note on the name stands).

`Astra review: NOT_PERFORMED`
