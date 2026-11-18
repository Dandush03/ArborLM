# Confirmation review: ADR-0023 (P10-I-S0, addressing and overload), draft 2

- **Reviewer:** the `arbor-auditor` subagent, model Claude Opus 5.5 (`claude-opus-5-5`). I did not write the draft, the code it relies on, or the closure ledger. The seed registry names an `arbor-auditor` run of another session as its author; this review did not write it and treats it as an input.
- **Draft reviewed:** `docs/decisions/ADR-0023-p10-i-s0-addressing-and-overload.md` at HEAD `26ea57b` (branch `claude/p10-i-specs`), sha256 `01540a4bdaf063e79311e534dad055acdf4cba40adf7eddc1095ec2f717fde16`. Compared with draft 1 by `git diff c525898 HEAD -- docs/decisions/ADR-0023-p10-i-s0-addressing-and-overload.md` (243 insertions, 155 deletions).
- **Inputs read:** the first review `REVIEW_ADR-0023.md`; `DIRECTION.md`; `CLOSURE_LEDGER.md` (sha256 `10d0f1ec…50c1`); `SEED_REGISTRY.md` (sha256 `b3fe7cab…134`); ADR-0024 (sha256 `6e744cf0…7b77`) §13 and §6; ADR-0020; ADR-0021 §7.2 and l.349; P10-S0 and P10-S1 records named below; `studies/p9ii/core.py`, `studies/p9/model.py`, `studies/p10s0/core.py`, `studies/p10s0/train.py`, `studies/p10s0/gates.py`, `studies/p10s1/core.py` (reading only).
- **Standing:** a Claude review. Not Astra validation and not a human approval. `Astra review: NOT_PERFORMED`. No training, no generation, no network. I did not open P10-S1's cell records; from `results/p10s1-run-2026-11-17/analysis.json` I read only the `held_out` annotations, skipping any key containing "recall".

## Commands and environment

- Independent arithmetic: `python3 -I <scratchpad>/r2_0023/checks2.py` (system Python 3.15.1, macOS arm64; standard library only; imports nothing from `arborlm` or `studies`). The script is reproduced in Appendix A because the scratchpad is not durable.
- Record reads: `grep`/`sed` on the files cited; `python3 -I -c` that loads `results/p10s1-run-2026-11-17/analysis.json` and prints `result.capacity.held_out` entries (keys containing "recall" skipped).
- Failed attempt, kept: my first `grep -rn ... --include=*.md` failed under zsh (`no matches found: --include=*.md`, unquoted glob). Re-run without `--include`. No finding depends on it.

## Verdict: NOT READY

No blocking finding remains. The decision procedure (steps 0–6, the per-series states and the two-series table) is total: I enumerated it and every combination reaches exactly one headline. Two factual errors of draft 1 are corrected. The remaining problems are two rule-level design defects that the revision introduced, partly by following my first review's own suggestions (findings N1 and N2), plus computability gaps in the new extension rule (N3) and cross-reference edits against the seed registry, the ledger and ADR-0024. N1 and N2 change scientific rules and need the human lead's choice, so they are not mechanical edits; hence NOT READY rather than READY AFTER EDITS. A third draft that adopts N1–N3 and the cross-reference table would, in my judgement, be ready for human review.

## 1. First-review findings

| # | Finding (severity) | Judgement | Note |
|---|---|---|---|
| 1 | Outcome function not total (BLOCKING) | **FIXED** | (a) step 0 fires on any missing main-grid cell, PAUSED or not; (b) step 4 is a separate REFERENCE row; (c) anchor flag stops before the freeze, step 1 covers class NOT_EVALUATED; (d) per-series states, NOT READ counts as FAILS; (e) ℓ₁ status includes NOT EVALUABLE; (f) flag makes all lines NOT EVALUABLE. Synthetic-registry tests list every case. But (f), which I recommended, is too broad: see N1. Small gap: ℓ₁ is undefined when L = "none" (N7) |
| 2 | Existing code cannot run the new slot counts (BLOCKING) | **FIXED** | §3 now states new adapter code, gate (a) at 4,096/16,384, gate (b) at new sizes, end-to-end gate at 512/1,024. I re-read `studies/p9ii/core.py` l.251–253: the check is at l.252, as cited. Gate (a)'s "shared rehearsal seed" is unspecified and P10-S0's path refuses foreign seed sets: cross-reference X3 |
| 3 | X8 ceiling unreachable; no X8 cap (REQUIRED) | **FIXED** | With the extension the ladder reaches 32,768, so T = 16,384 is reachable; X8 enters the frozen projection at that ceiling (§8, §9) |
| 4 | Blind rehearsal without mechanism; cuts after Stage R (REQUIRED) | **FIXED** | Mechanism (i)–(vi) stated; A0/X8 choices fixed at Decision 1. Advisory residue in N8 |
| 5 | Init seeds collide with derived seeds (REQUIRED) | **FIXED**, cross-reference update needed | Values removed; derived-seed check required; separate calibration init seeds. The registry now exists and assigns values; the draft still says the lead "will write" it (X1, X2) |
| 6 | No plateau floor; decline counted as plateau (REQUIRED) | **FIX INTRODUCED A NEW PROBLEM** | Two-sided step: good. The floor is applied to A5-D as well as A6, which is what my first review suggested ("both arms' m_P"). That suggestion was a mistake on my part: see N2 |
| 7 | No extension rule (REQUIRED) | **FIXED in substance; rule not computable as written** | See N3 |
| 8 | Positive meaning overclaimed; A6 not ideal (REQUIRED) | **FIXED** | 0.81 stated; RATIO ABOVE 1; SHOWN qualifier |
| 9 | Operating characteristic; negative wording (REQUIRED) | **FIXED** | Table reproduces (Appendix A, B): 0.736/0.542/0.159; 0.914/0.835/0.582; 0.965/0.932/0.810; 0.996/0.991/0.975. "About four times in ten" = 0.418 |
| 10 | "Only the slot count changes" (REQUIRED) | **FIXED** | |
| 11 | Cost range; best-case rates (REQUIRED) | **FIXED**, small residue | All-at-ceiling series M with A0's measured 0.0144 at 4,096 slots is 223 CPU-h, not 216; total still about 54 h (N9) |
| 12 | Paired rule rationale (REQUIRED) | **FIXED** | Rule fires at 6–0, 7–0, 8–0, 8–1, 9–0, 9–1, 10–0; refuses 7–1 (p = 0.070) and 8–2 (p = 0.109). With at most ten pairs, p < 0.05 implies d ≥ 6, so the d clause is redundant but harmless. Handling of pairs on a NOT_EVALUATED draw unstated (N7) |
| 13 | Lane licence extrapolated; regime tag dropped (REQUIRED) | **FIXED** | Consistent with ADR-0024 §13's cell list. New cross-reference on the A6 denominator in lane L (X6) |
| 14 | Disagreement with the ledger (REQUIRED) | **ANSWERED; answer partly sound** | WX decline sound. 65,536 decline sound, but its proposed route "to P10-I-S1's 16,384→65,536 item" is not available (X4). Condition-6 note added, but it misplaces the risk: see N1 |
| 15–20 | Advisory items | **FIXED** | Condition 3 descriptive share; load-average sampling and sharing rule; μ/A0; probe cadence; units in exposures; Stage R rounds and resume test |
| §3 | UNRESOLVED not a reason to extend | **FIXED** | §1, §7 |
| R1–R6 | Record mismatches | **FIXED** | R6 sentence in §6.5 matches the requested text |

## 2. New findings

### REQUIRED

**N1. REQUIRED. Reference validity: a flag on condition 4 removes the very cell type the study exists for, and only the anchor returns to the human lead.** (§5.2 "Reference validity" and "Stop before the freeze"; §12; §6.4 row 1; §3 ledger row on condition 6; §16 "Still unsure".)

The brief asks whether "A6 passes condition 6 at loaded cell types is unknown" can make most of the study NOT EVALUABLE. My answer: condition 6 is unlikely to be the problem; condition 4 is.

- *Condition 6.* In P10-S1's audit (`results/p10s1-run-2026-11-17/audit/a4_dep_sensitivity.out`) all 32 failures of a_use ≥ 0.95 × raw accuracy, the 12 of the reference R2 included, occurred at raw accuracy ≤ 0.436 (largest: 893 correct, 847 useful of 2,048, ratio 0.9485), and the correct-but-not-useful count tracks (n − useful) × the memory-disabled rate in every row, i.e. the survivors of the swap are chance hits. Under that model (a memory-retrieved fact never survives the swap; a non-retrieved fact is right by chance with probability c), condition 6 fails only below accuracy 0.29–0.46 for c = 0.02–0.04 (0.392 at c = 1/32; Appendix A, C). Every evaluable draw at load ≥ 1 has A6 ≥ 0.50. So a condition-6 flag on A6 is improbable at any evaluable cell type. This is an inference from P10-S1's task and arms, not a measurement of A6 at this study's loads. The draft should state it, with the source, instead of leaving it "still unsure".
- *Condition 4.* A6 has never been read on condition 4 in any record: P10-S0 classed no A6 cell, and P10-S1's HELD-OUT FRAGILE annotation (false for F-OQ at every cell in `analysis.json`) is relative to R2's ratio, not the absolute 0.90 ratio. ADR-0021 §7.2 item 3 states that under oracle addressing H1/H2 "test the shared readout through the frozen upper block, not the memory and not the address". P10-S0's overload failure was condition 4 alone (H-ratio margins down to −0.180). If that failure is partly a readout effect of overload, A6 can fail condition 4 at 8K/4K too. The rule then removes 8K/4K (load 2, P10-S0's own cell type) from the plan, Line A there is never measured, step 4 prints OVERLOAD NOT EVALUABLE — REFERENCE, and H23-O is unreadable. All of this happens by rule after Stage R, without the human lead, and the remaining grid is run although the headline can no longer be OVERLOAD-QUALIFIED once a load-1 cell type is flagged.
- My first review's change (v) ("all three lines NOT EVALUABLE") caused part of this. It was too broad: a reference failing only the G-condition does not invalidate the A-conditions.

Change (`PENDING LEAD REVIEW`):

1. Make the flag per condition. If A6 fails condition 4 only, **Lines G and Q are NOT EVALUABLE** there, **Line A is read**, and the cell type stays in the plan (A5-D, A6 and, in series M, A0 still run). If A6 fails any of conditions 2, 3, 5 or 6, all lines are NOT EVALUABLE and the cell type is removed, as now. Print, at a cell type flagged on condition 4, the descriptive "REFERENCE ALSO FAILS CONDITION 4 (A6 H-ratio x on calibration draws)" beside the existing H-accuracy-over-A6 measure.
2. Extend "Stop before the freeze" to any flag at a load-1 or load-2 cell type in either series, not only the anchor: the work returns to the human lead before the freeze with `durations.json`.
3. Replace the §3 ledger-row risk sentence and the §16 "still unsure" item with the evidence above.
4. Add the synthetic-registry cases: condition-4-only flag at load 2 (Line A read, G and Q NOT EVALUABLE) and a flag at load 1.
5. List "which A6 failures remove a cell type" in §16 as a lead choice.

**N2. REQUIRED. The plateau floor on A5-D turns the clearest overload failure into UNRESOLVED and spends the maximum budget on it.** (§5.1 "Floor"; §5.3; §7 step 5.)

Consider a loaded cell type at which A5-D settles flat at m_P = 0.40 while A6 is flat at 0.95. That is an unambiguous addressing failure, since condition 1 fails by a wide margin. Under the floor, A5-D "never has a plateau", so the cell type is extended (if budget allows) and then NOT SHOWN. It runs at the maximum T. Its failure is worded step 5, OVERLOAD UNRESOLVED … NOT SHOWN. A learned arm that is converged and bad is indistinguishable from one still rising.

The protection the floor buys for A5-D is small. P10-S1's floor (ADR-0021 l.349) was for arms that had not yet stored anything checkable. A5-D did not collapse in P10-S0 (10 of 10). A0's escape, the cited case, had a maximum of 30,656 updates, which is below 512 exposures at 8,192 facts (32,768 updates). The rule also already needs two consecutive flat doublings. P10-S1 itself printed "FLAT BELOW THE DEP FLOOR" rather than "still improving" (ADR-0021 l.349). My first review proposed the floor for both arms; for A5-D that was wrong.

Change (`PENDING LEAD REVIEW`): apply the floor to A6 only at every load. For A5-D, keep the two-sided two-step rule and add: "an A5-D that meets the step rule below the floor is printed A5-D FLAT BELOW FLOOR and counts as a plateau". Keep the anchor stop rule as it is: at load 0.5, an A5-D below 0.90 still returns the work to the human lead before the freeze, because NOT SHOWN at the anchor already stops.

**N3. REQUIRED. The extension rule is not computable the same way by two people.** (§5.1 "Extension rule"; §9; §11.)

- "Projected total charged hours" is undefined. Is it 1× the projection or the 2× cap of §9? Does it include Stage R hours already spent, X8 and its calibration at their ceiling, and the three evaluations per cell? Is it at stage 3's measured rates per slot count? The cap of §9 (twice the projection) can exceed the Decision-1 budget; say how the two relate.
- "Granted in order of ascending load, series M before S": state that extensions are decided only after every cell type's base ladder has finished, and whether a refusal stops the queue or the next item is still tried if it fits.
- Stage R's own per-stage cap (§9, "twice each stage's projection") has no projection to start from, because Stage R's length is what it measures. Fix it from the base-ladder worst case plus the extension budget.

Change: one sentence for each. My suggestion: "projected total = Stage R hours spent + the remaining Stage R rounds + main grid at the rule's T + X8 and its calibration at T = 16,384, three evaluations per cell, at stage 3's measured seconds per update per (arm, slot count), divided by six workers; 1× (not the cap's 2×); each item in the order is granted if it fits and refused otherwise, and the next item is tried".

### ADVISORY

**N4. ADVISORY. The extension's costs are understated in two places.** §5.1's "about 3 hours" per 8,192-fact cell at T = 16,384 holds at 4,096 slots; at 16,384 slots it is 5.4 h. One calibration run to 32,768 exposures at 8K/16K is 10.9 h serial (5.8–10.9 h across slot counts; Appendix A, D). §11's "about 15 more per cell type" is the total at T = 16,384 at 4,096-slot rates; the increment over T = 8,192 is 7.3–12.2 h by slot count, and the total is 14.6–24.4 h. State which figure is meant.

**N5. ADVISORY. Sealing proves non-alteration, not non-reading.** A committed sha256 shows that the sealed files were not changed; it does not show that nobody read them. State the access control in plain terms (for example, file permissions, a directory outside the worktree, read only by the auditor's script), and state that Decision 2 sees `durations.json`, whose NOT SHOWN entries predict an UNRESOLVED step. A decision not to run, taken at Decision 2, should be recorded with what was seen.

**N6. ADVISORY. Untagged numbers.** "36 GiB" aggregate under sharing (§9) and "load average above 2.0" (§10) are the drafter's numbers; mark them **[choice]**.

**N7. ADVISORY. Small definitional gaps.**
- ℓ₁ for Lines A and G when L = "none": define it as 0.5.
- H23-G: also not read when there is no ℓ₁ (NO BREAK FOUND).
- H23-O: "Line Q HOLDS at load 2" can be true while L_Q < 2 (NON-MONOTONE). Define it as L_Q ≥ 2, or say that it is read independently of L_Q.
- §6.7: say whether a pair on a draw NOT_EVALUATED at that cell type is excluded from d and from the sign test.
- §8: "NOT RUN — BREAK LOCATED BELOW 8" is printed also when ℓ₁ = 4 is NOT EVALUABLE; use "NOT RUN — L_Q BELOW 4".

**N8. ADVISORY. End-to-end gate sizes.** The small-store gate runs at 512 and 1,024 slots only. 2,048 and 8,192 are covered by gate (b) alone. Running the end-to-end gate at every new size costs minutes.

**N9. ADVISORY.** §11 row "every cell type at the base ceiling": series M is 223 CPU-h with A0 at its measured 0.0144 (the draft adopted that rate for the central row); the total of about 54 h is unchanged (53.7 + 1.5).

## 3. Numbers checked against records (added or changed in this revision)

| Draft location | Claim | Record | Result |
|---|---|---|---|
| §2 rows on F-OQ | 0.390 → 0.654 (8K/1K), 0.392 → 0.637 (32K/4K), 6,144 and 3,072 exposures; 0.948 → 0.996, 0.991 → 0.999 | P10-S1 `OUTCOME.md` §4 table | matches; 393,216·128/8,192 = 6,144, 786,432·128/32,768 = 3,072 |
| §2 remark 2 | last-doubling gain in bits per fact of i\*; ADR-0021 §1 fact 11 | first review's checks; ADR-0021 l.53 | matches |
| §3 | `Cell.__post_init__` line 252 | `studies/p9ii/core.py` l.251–253 | matches |
| §4.2 | seed + 1000·k, `studies/p9/model.py` l.272–276; `DERIVED_INIT_OFFSETS` | l.272–278; `studies/p10s1/core.py` l.819 | matches |
| §4.2 | data draw dominates in 24 of 28 | `ERRATUM_SEED_BLOCK.md`; P10-S1 `OUTCOME.md` finding 3 | matches |
| §5.1 | P10-S1 floor added in revision 5 because every calibration cell met the rule early | ADR-0021 l.349 | matches |
| §5.1 | A0 escape median 13,664 | first review, `extras_out.txt` l.40 | matches |
| §3, §5.2 | P10-S1's reference failed condition 6 at low accuracy, `ACCEPTANCE.md` ruling 1 | `ACCEPTANCE.md` l.26; `audit/a4_dep_sensitivity.out` | matches; R2 failed at raw accuracy 0.25–0.38 (N1) |
| §6.6 | operating-characteristic table | own computation | matches |
| §6.2 | 201.5; about 0.7% | first review's computation | matches |
| §10 | M5 Max, 48 GB, six single-thread workers | ADR-0020 l.431 | matches |
| §11 | 57.5 / 8.2 / 18.3; about 29–31; 216 / 29 / 71 → about 54; X8 about 9 and about 18; up to about 75 | own computation | matches, except 216 → 223 (N9) |

No idle-load figure or other unsourced machine claim appears in this draft.

## 4. Closure-ledger rows declined by the draft

- **WX (record-length-free variant): declining is sound.** It is a second interface change beside load, and §13 excludes WX explicitly. One wording fix: §3 says "by ADR-0020 a WX failure can never be read as evidence". The record's words are "not evidence that the record length is required" (ledger l.82). Use those words. The ledger should then read CLOSED AS RECORDED (unresolved; declined by ADR-0023 §3), pending the human lead.
- **65,536 slots: declining is sound, but the proposed alternative route does not exist.** The question here is load, and a 32,768-fact series at converged durations is costly. P10-I-S1's "16,384→65,536" item, however, is an oracle-capacity transition. ADR-0024 lane L licenses only ADR-0023's tested cell types and excludes the 32,768- and 131,072-fact rows (ADR-0024 l.295). Learned addressing at 65,536 therefore has no taker in P10-I. The only consistent disposition is CLOSED AS RECORDED, kept visible as unresolved ("Addressing at 65,536 is not qualified by any study"). Change §3 and §16 item 9 to propose that alone, and change ledger l.83.

The ledger is a draft and not immutable. It should be edited, not left to disagree with the specification (X4, X5).

## 5. Choices reserved for the human lead (§16)

| Item | Really the lead's? |
|---|---|
| 1 grid; 2 X8; 5 meaning of 0.90 under a degraded reference; 6 "both series" × "every lower load"; 7 A0; 8 μ and no dense baseline; 10 licence scope; 12 budget and sharing; 13 approvals | Yes: scientific scope, thresholds or budget |
| 3 convergence rule | Yes, but the drafter should propose N2's A6-only floor rather than park "whether the floor applies to A5-D" in "still unsure" |
| 4 extension and hour budget | The budget is the lead's; how the projection is computed is a missing rule, not a choice (N3) |
| 9 ledger | Yes, but offer only options that exist (section 4) |
| 11 seeds | No longer a choice: the registry exists. The lead approves the registry; the draft adopts its values (X1, X2) |
| missing | Which A6 failures remove a cell type, and whether a flag at loads 1–2 returns the work before the freeze (N1). Add as an item |
| "Still unsure" sentence | Not a lead choice: condition 6 can be answered from P10-S1's audit (N1). Whether the 0.01 step is attainable under a degraded reference is an empirical question that Stage R answers by NOT SHOWN; say so |

## 6. Cross-reference mismatches

| File | Line | What it says | What it must say |
|---|---|---|---|
| ADR-0023 | 119 | registry "that the lead will write" | "`SEED_REGISTRY.md` (written by the `arbor-auditor` subagent, checker `seed_registry_check.py`, RESULT: PASS at its section 6) assigns: registered and reserve draw sets 300001–306999 (draw d at 300001 + 100(d−1); reserves 301001, 301101, 301201, 301301; P10-S0 in-set layout); calibration sets 309001, 309101; rehearsal 309201; pipeline check 309301; initialisation 330001 (odd draws; A6 on every draw), 330002 (even draws), calibration 330091 (draw 1) and 330093 (draw 2), rehearsal and pipeline check 330092, test mode 330098 and 330099; unit tests 932001–932999" (**X1**) |
| ADR-0023 | 116–117 | counts without test-mode initialisation; no derivation rule | Add the two test-mode initialisation seeds and the registry's §4.3 condition 1: no initialisation seed is derived arithmetically from a data, rehearsal or test seed (**X2**) |
| ADR-0023 | 64 | gate (a) "on a shared rehearsal seed" | Name it. P10-S0's path accepts only its own rehearsal set, P9-II's rehearsal set 5 or test sets (`studies/p10s0/core.py` l.541–556, `check_seed_set`), so gate (a) needs a declared re-use (for example P10-S0's rehearsal set and init seed, as P10-S0's G4 re-used P9-II set 5). Add it to the registry as a declared re-use, as the registry does for ADR-0029 (**X3**) |
| ADR-0023 | 92; §16 item 9 | 65,536 routed "to P10-I-S1's 16,384→65,536 item or close it as recorded" | "close it as recorded (unresolved)"; ADR-0024 l.295 excludes these rows from lane L (**X4**) |
| CLOSURE_LEDGER.md | 82, 83 | CARRIED INTO P10-I-S0 (candidate) | CLOSED AS RECORDED (unresolved; declined by ADR-0023 §3; pending the human lead) (**X4**) |
| CLOSURE_LEDGER.md | 88 | lane L "CARRIED INTO P10-I-S0" | "P10-I-S0 (licence, ADR-0023 §15) and P10-I-S1 (lane L, ADR-0024 §13)" (**X5**) |
| ADR-0024 | 298 | "ADR-0023's cell-success composite is applied unchanged" | Condition 1 needs A6 (lr 0.003, R1 codes) on the same draw, cell and update count; ADR-0024's F-OQ goes through a rate search (l.106) and is not A6 unless its rate is 0.003. Name the denominator, or run A6. ADR-0023 §15 should state that a lane applying the composite must include A6 as frozen here (**X6**) |
| SEED_REGISTRY.md vs ADR-0024 | registry l.143; ADR-0024 l.297 | registry: lane L data 247001… "ADR-0023's in-set layout, if lane L needs data of its own"; ADR-0024: lane L runs "on this study's draws" (P10-S1 layout) | One of the two must change. ADR-0023 is unaffected if the licence stays tied to cell types; noted for ADR-0024's reviewer (**X7**) |
| ADR-0023 | 90 (§3 ledger row) and 383 | condition-6 risk at loaded cell types, "unknown" | the evidence and change of N1 (**X8**) |

Labels read across drafts were checked. ADR-0024 uses "OMITTED — ADDRESSING NOT QUALIFIED AT THIS CELL (ADR-0023)", the reference regime and the convergence status per cell type, L_Q, and "8K/1K only if its conditional series runs". Each exists in ADR-0023 §§6.5, 7, 8 and 15 with the same meaning. ADR-0024's "N1 and N2 if L_Q ≥ 2; C1 also if L_Q ≥ 8" agrees with ADR-0023's X8 trigger (L_Q = 4 → X8 → possible L_Q = 8).

`Astra review: NOT_PERFORMED`. This review is independent engineering and mathematical evidence by the `arbor-auditor` subagent (Claude Opus 5.5). It is not Astra validation and not a human approval.

## Appendix A: check script (verbatim; `python3 -I checks2.py`, Python 3.15.1)

```python
"""Confirmation-review checks for ADR-0023 draft 2 (auditor's own code; imports nothing from arborlm or studies)."""
from math import comb
print("== A. paired rule: d = b - c >= 6 AND exact two-sided sign test p < 0.05, ten pairs")
def p2(b, c):
    n = b + c
    if n == 0: return 1.0
    k = max(b, c)
    return min(1.0, 2 * sum(comb(n, j) for j in range(k, n + 1)) / 2 ** n)
for b in range(11):
    for c in range(11 - b):
        d = b - c; p = p2(b, c)
        if d >= 6 or p < 0.05:
            print(f"  b={b} c={c} d={d} p={p:.4f} d>=6:{d>=6} p<0.05:{p<0.05} rule:{d>=6 and p<0.05}")
print("== B. operating characteristic (RELIABLE = <=1 failure of 10), L_Q>=2 = both series at 0.5,1,2")
for p in (0.90, 0.95, 0.97, 0.99):
    one = p**10 + 10*p**9*(1-p); both = one*one
    print(f"  p={p}: one {one:.3f} both {both:.3f} L_Q>=2 {both**3:.3f}  break<=2 {1-both**3:.3f}")
print("== C. condition 6 for an oracle reference under a chance-survivor model")
print("   a_use = r (memory-retrieved facts never survive the swap); survivors = (1-r)*c; acc = r + (1-r)*c")
for c in (0.02, 0.029, 1/32, 0.04):
    r = 0.95*c/(0.05 + 0.95*c); acc = r + (1-r)*c
    print(f"  c={c:.4f}: condition 6 fails below r={r:.3f}, i.e. accuracy {acc:.3f}")
print("   P10-S1 audit a4: largest failure 893 correct, 847 useful of 2048 -> raw", round(893/2048,4), "ratio", round(847/893,4))
print("== D. cost: A0 at 4,096 slots 0.0144 (measured), others as the draft")
R = {16384: {"A5-D": 0.0172, "A0": 0.0144, "A6": 0.0187}, 8192: dict.fromkeys(("A5-D","A0","A6"), 0.013),
     4096: {"A5-D": 0.0102, "A0": 0.0144, "A6": 0.0091}, 2048: dict.fromkeys(("A5-D","A0","A6"), 0.010),
     1024: dict.fromkeys(("A5-D","A0","A6"), 0.010), 512: dict.fromkeys(("A5-D","A0","A6"), 0.010)}
M = [16384, 8192, 4096, 2048]; S = [4096, 2048, 1024, 512]
def cells(F, slots, arms, T): return sum(T * F / 128 * R[n][a] * 10 for n in slots for a in arms) / 3600
def stageR(F, slots, T): return sum(2 * T * F / 128 * R[n][a] * 2 for n in slots for a in ("A5-D","A6")) / 3600
for T in (8192, 16384):
    m = cells(8192, M, ("A5-D","A0","A6"), T); s = cells(2048, S, ("A5-D","A6"), T); r = stageR(8192, M, T) + stageR(2048, S, T)
    print(f"  every cell type at T={T}: M {m:.0f} S {s:.0f} R {r:.0f} CPU-h; six workers {(m+s+r)/6:.1f} h (+1.5 overhead {(m+s+r)/6+1.5:.1f})")
for n in M:
    per = (16384 - 8192) * 8192 / 128 * sum(R[n][a] for a in ("A5-D","A0","A6")) * 10 / 3600 / 6
    tot = 16384 * 8192 / 128 * sum(R[n][a] for a in ("A5-D","A0","A6")) * 10 / 3600 / 6
    rr = (32768 - 16384) * 8192 / 128 * (R[n]["A5-D"] + R[n]["A6"]) * 2 / 3600
    longest = (32768) * 8192 / 128 * max(R[n]["A5-D"], R[n]["A6"]) / 3600
    print(f"  extension at 8K/{n}: registered +{per:.1f} h over T=8,192 (total at T=16,384 {tot:.1f} h, six workers); Stage R extra round {rr:.1f} CPU-h; one calibration run to 32,768 e = {longest:.1f} h")
x8 = 16384 * 8192 / 128 * 0.010 * 3 * 10 / 3600 / 6; x8c = 2 * 16384 * 8192 / 128 * 0.010 * 2 * 2 / 3600 / 6
print(f"  X8 at T=16,384: cells {x8:.1f} h + calibration {x8c:.1f} h six-worker")
```

Key output:

- **A.** The rule fires at 6–0, 7–0, 8–0, 8–1, 9–0, 9–1 and 10–0. It does not fire at 7–1 (p = 0.0703) or 8–2 (p = 0.1094).
- **B.** L_Q ≥ 2 has probability 0.159, 0.582, 0.810 and 0.975 at p = 0.90, 0.95, 0.97 and 0.99.
- **C.** Condition 6 fails below accuracy 0.290, 0.374, 0.392 and 0.455 at c = 0.02, 0.029, 1/32 and 0.04.
- **D.**
  - At the base ceiling: series M 223, series S 29 and Stage R 71 CPU-h, about 53.7 h on six workers.
  - With every cell type extended: 107.4 h.
  - Extension increments: +12.2, +9.5, +8.2 and +7.3 h at 16,384, 8,192, 4,096 and 2,048 slots.
  - One calibration run to 32,768 exposures: 10.9, 7.6, 5.9 and 5.8 h.
  - X8 at T = 16,384: 14.6 + 3.9 h.
