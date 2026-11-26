# M0 stage 2, R1: record of conditions (wording, levels distinct, second solver) for the 10 lineages of the survivor list

Auditor: `arbor-auditor` context, model Claude Opus 5.5 (`claude-opus-5-5`, from session metadata), 2026-11-26. I wrote none of the lineages, rule scripts, run copies or solvers. Independent engineering evidence only; **not Astra validation, not human approval, nothing registered.** Brief: `experiments/_scratch/m0_fr_briefs_20261126/COMMON.md`, `STAGE2.md` (eval R1). Spec: ADR-0033 addendum 1 at `2c944302` (sections 0-2, 4A stage 2, 8, 12 item 16), `LEAD_RULINGS_7.md` R-40, `LEAD_RULINGS_8.md`.

## Result

| Condition | PASS | FAIL |
|---|---|---|
| wording | 10 | 0 |
| levels_distinct | 10 | 0 |
| second_solver | 10 | 0 |
| map | "see map_of_record" (not mine) | |

`stage2_conditions_r1.json` SHA-256 `b2474d925206264def8b77798f4fd8347e4ed2c89e2005a691483905f975e377` (built twice by `build_conditions_r1.py`, same hash).

## Second-solver fixture check

Seed `int.from_bytes(sha256(b"400002|stage2-check|R1")[:8], "big")` = **14961762383913329776** (not among the 108 integers of `addendum1_rev6_fresh_run.out.txt` part A: grep count 0). Per lineage and level, stream `random.Random(int.from_bytes(sha256("<seed>|<lineage id>|<level>")[:8], "big"))`, 50 items, Retry redrawn on the same stream. Builder key against `final_r1/solvers_final.py` (`SOLVERS[id](question)`): **3,500 fixtures, 3,500 agree, 0 mismatches, 0 ambiguous, 0 parse errors; 350 per lineage, 50 per level.** No mismatch ids to report. The same run under `PYTHONHASHSEED=7` gives byte-identical `fixtures_r1.jsonl` (`6204d454…0ed5`) and summary (`a65f6c81…fe06`). Coverage: the solver's `SOLVERS` names all 10 survivor ids (it also names two lineages not on the list). Recorded agreement in `FINAL_R1.md` section 1: 0 mismatches / 0 ambiguous / 0 parse on 84,000 + 42,000 items over 12 shapes (10,500 per shape); I did not open those run outputs (the brief forbids past outputs) and cite the report only.

## Levels distinct: the rule, and the R-40 decision

Rule, the same for all ten (fixed before applying it): PASS iff (a) the builder's level parameters differ between every two levels, confirmed on the fixtures by 0 shared normalised texts across levels and by an identity test (one shared stream seed per lineage for all seven levels, 20 items; no two levels equal); (b) a stated size/steps/depth parameter is non-decreasing over 0..6 and larger at 6; (c) every adjacent pair differs in at least one stated parameter in the direction of more work. All ten meet (a)-(c); nine have a size/steps parameter that rises strictly at every level (see `REASONS.md`, `levels_params_r1.stdout.txt`).

**R-40, R1 point (Venn levels 0 and 1): decided PASS.** Reason: levels 0 and 1 (2 groups each; `_VENN5`, `lineages_r1_fix3_d.py:350`) ask different read-outs ("none", total − a − b + ab; "exactly one", a + b − 2ab) and draw from wider ranges (regions 1..24 against 1..28, none 0..30 against 0..32, lines 359-360). They are not a relabel and not one item distribution (0 shared texts; identity test differs). The procedure's size does not rise from 0 to 1, and the same holds from 3 to 4 (3 groups; "exactly two" against "at least two"), which R-40 does not name; condition (c) is met there by the number ranges only. Whether level 1 is harder than level 0 is a question of difficulty, on which the brief says no lineage is failed. **A stricter reading (the procedure's size must rise between every two adjacent levels) would FAIL this lineage; I did not apply it: PENDING LEAD REVIEW.**

The other R-40 points are not R1's and I decide nothing on them: R2 `dictionary_rank` (level 1 to 2) and `from_base` (shared texts across levels) are level points for the R2 auditor; M1 `gcd_lcm`'s false general rule exact at levels 3-6 is a cheap rule's rate (the fresh run's; its mean-log-answer dip is a level point for the M1 auditor); C1's within-shape rates in `slices_f4` and `binary_search_f3` are cheap-rule rates and belong to the fresh run.

## Findings and what I could not establish

1. **Section 8 item 1, "the fixtures it receives carry no answer from the first solver" (review note N3), is not shown by the record for the R1 solver.** `final_r1/samples.py` (the dump `FINAL_R1.md:48` says the solvers were written from) prints `KEY: repr(b.answer)` (`samples.py:2,15`), the builder's key, and the auditor fixed a solver bug after a keyed comparison (`FINAL_R1.md:59-61`). The condition as briefed (a text-only solver from a separate context that agrees on every fixture) is met, and I recorded PASS on it; whether N3 bars this solver is **PENDING LEAD REVIEW**. It applies to all ten lineages alike.
2. The separation of contexts (solver author did not read builders) rests on the final auditor's statement in `FINAL_R1.md:48-50`; I cannot check session metadata. The solver's code imports nothing from the repository (`solvers_final.py:9-11`; `heapq` at 224).
3. Wording: open and category answers (exchange rates, Venn, weekday) state their answer form through the question ("how many units", "how many of the people", "which day of the week") and not by an explicit list or instruction; I read that as stated (my reading, applied to all). Cosmetic grammar ("1 units of", "A" before a vowel) does not change any key. Alternative readings a reader might bring despite a stated convention were not tested beyond the solver's ambiguity checks.
4. "The pair audited" and the place in the map are not mine (another auditor's map of record).
5. I saw incidental figures while reading code and the spec: dropped lineages' figures in the docstring of `lineages_r1_fix4_clusters.py:16-55`, figures in the approved text, and the per-level parameter means of `FINAL_R1.md` section 4 (no cheap-rule rows). No cheap-rule figure entered any judgement; I did not read `FINAL_R1.md` sections 3, the verdict table or any past run output.

## Commands and environment

macOS 27.2.1 arm64; `uv 0.12.15`; `uv run --locked python` = CPython 3.12.14 (implementation worktree's locked environment); worktree `agent-a0c9d741ea96ce52f` HEAD `128a02a7`; builders unchanged since `7cd0ac5a` and `final_r1/` unchanged since `b78e58b1` (`git diff --quiet`, working tree included). From the worktree root:

```
PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 uv run --locked python <D>/stage2_check_r1.py <D>/run1            # stdout run1.stdout.txt
PYTHONHASHSEED=7 PYTHONDONTWRITEBYTECODE=1 uv run --locked python <D>/stage2_check_r1.py <D>/run2_hashseed7  # stdout run2_hashseed7.stdout.txt
PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 uv run --locked python <D>/levels_params_r1.py <D>/run1/levels_params_r1.json
python3 -I <D>/build_conditions_r1.py <D>     # run from <D>; standard library only
```

`<D>` = `/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_fr_stage2_r1_20261126/deliver`. Input hashes: survivor list `0b658145…be0d`; `solvers_final.py` `20aa9451…ca62`; `samples.py` `fb4d7566…3697`; `FINAL_R1.md` `e38b9627…44b8`; `lineages_r1_rev4.py` `e14e21ea…9a24`; `lineages_r1.py` `19360b35…66e4`; `lineages_r1_fix3_d.py` `8ca69ebf…af66`; `lineages_r1_fix3_e.py` `254eb4f0…6f`; `lineages_r1_fix4_a.py` `81cbb05a…540a`; `lineages_r1_fix4_clusters.py` `f7161d82…cd38`; `core.py` `07907f1e…081d`; `vocab.py` `2c4036be…c293`.

## Slips (kept)

`REASONS.md` carries wrong line citations for three lineages (grid walk, swap tracking, Venn); corrected in `REASONS_CORRECTIONS.md`, the original left as written. No command failed. Nothing written outside this directory; no deletes, moves or permission commands; no commit; no item of a run seed or dry-run seed generated; no rule script, unit or model run.

Astra review: NOT_PERFORMED
