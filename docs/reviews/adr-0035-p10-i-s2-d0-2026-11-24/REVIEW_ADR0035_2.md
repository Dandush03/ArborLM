# Review 2 of draft ADR-0035 (P10-I-S2-D0): confirmation check of revision 2

- Reviewer: `arbor-auditor` subagent, Claude Opus 5.5 (`claude-opus-5-5`), 2026-11-24. Independent engineering and mathematical review. Not Astra validation and not human approval.
- File reviewed: `experiments/_scratch/p10is2_d0_20261124/ADR-DRAFT-p10-i-s2-d0-interference-diagnosis.rev2.md`.
- Nothing was loaded or scored, and no new number was computed. Besides the draft, I read:
  - `studies/p10is2/partt_real.py` lines 307–316 (`build_world_real`);
  - `studies/p10s2/world.py` lines 139–151 (`load_arm`).

  Both are in the Part T worktree at `f6dff34d`. They were read only to judge whether the specification can be implemented.

## Verdict

**SOUND AFTER THE LISTED CHANGES.** All six required and all nine advisory items of Review 1 are applied correctly. Two new required text changes remain, R7 and R8, and three advisory ones. None changes the design, a condition, a threshold or the wording rule.

## Review 1's items, as applied

| Item | Applied correctly? | Note |
|---|---|---|
| R1 | yes | 0.443 and 0.532 |
| R2 | yes | §1.4, §13 and §15 |
| R3 | yes | The five requirements, the tolerance and the gate-record content are as worded. With "differ only in the per-slot weight vector", e(1) at append is bitwise equal to a, because g2 = 0.0 makes the two weight vectors identical. |
| R4 | yes | The retry rule is consistent. A failed gate computes no counterfactual score, so its retry is still the single run. The "otherwise" branch can only arise after the gate has passed, and then it goes to the human lead. |
| R5 | partly | See R8 |
| R6 | yes | |
| A1–A9 | yes | **A3:** the extra ORDER-DEPENDENT trigger ("the two orders give different words") is fixed in advance and mechanical; it opens no choice. **A7:** the "otherwise" branch, "`row_shares` not used", is acceptable. |

I found nothing new that leaves a choice open until after observation, and no new overclaim. The order note in §9 and the caveat that c was never trained to be quiet (§13) are correct as written.

## New items

**R7 (REQUIRED): the specification cannot be implemented from the ADR alone.** §3 lists "the frozen student; panels E_A and E_B; the routers; `item_records.json`".

- Building the scoring world needs more than that. `build_world_real(repo, cfg, qdir, plan_calibration, mode, door)` takes:
  - Part T's frozen configuration;
  - Part Q's bundle and draws, through `qdir`;
  - the calibration plan, which holds the read layer and U.
- None of these is named or hashed, so they escape §3's "SHA-256 checked" rule.
- Whether `load_part_q`, given `mode` and `door`, writes anything is not stated either.
- The exact-reproduction gate would catch wrong inputs. Even so, a person holding only the ADR has to rediscover the entry points, and the provenance of these inputs goes unrecorded.

Text change: append to §3:

> "World inputs, read-only, SHA-256 recorded before use: Part T's frozen configuration, Part Q's directory (`qdir`) and the calibration plan, exactly as Part T's evaluate stage read them. The world is built with `studies.p10is2.partt_real.build_world_real`. Snapshots are loaded with `studies.p10s2.world.load_arm`, which checks each file hash against its manifest. Scoring uses `studies.p10s2.evaluate.score_panel` under the oracle route, with an `Arm` whose `prepare` substitutes the condition's read. Before the gate, the implementer shows that building the world writes nothing to the Part T run directory or to Part Q's directory (file lists and hashes before and after, recorded). The routers are not used, because every pass is under the oracle route, and they are not loaded."

In the same paragraph, delete "the routers;".

**R8 (REQUIRED): attribution and completeness of the endorsed text.**

- §1 introduces the quoted paragraph as "The direction endorsed by the human lead". By §16 it is the text of the analysis the human lead pasted, which is not the lead's own words; the lead's words are "I agree with gpt".
- The quote also contains an ellipsis.
- For a traceable record, the full pasted text must be kept alongside the endorsement. Otherwise "I agree with gpt" has nothing to anchor it.

Text change, §1, first sentence: replace "The direction endorsed by the human lead (section 16), as relayed to the drafter:" with

> "The analysis the human lead pasted and endorsed with "I agree with gpt" (section 16), excerpted as relayed to the drafter (the human lead did not write this text; the full pasted text goes verbatim into the approval record):"

In §16 item 1, after "I agree with gpt", add:

> "; the pasted analysis it answers is recorded in full beside it."

**A10 (ADVISORY): resume after an interruption.**

- §8.2 and §10 cover a gate failure and a cap. They do not cover a crash or pause partway through the scoring passes.
- Add to §8.3: "A resume after an interruption, from completed per-pass records that nobody has opened, is the same run. Any other restart is a second run (section 9)."

**A11 (ADVISORY): show the Part T run directory was untouched.**

- §11 says the Part T run directory is opened read-only.
- Record a hash list of its files before and after D0, and the same for the recomputation, as evidence of that.

**A12 (ADVISORY): pin the computation of a to the registered read.**

- Add to §4: "The weight-vector computation of a is `torch.equal` to `SparseStore.read` on every query."
- e(1) = a at append implies this only indirectly.

## Still open, not a specification defect

The approval record itself, holding the verbatim words, the pasted text and the reading of the delegation, does not exist yet. §16 makes it a precondition of approval, which is correct. Whether the delegation as read covers this approval is for the human lead's review (PENDING LEAD REVIEW).
