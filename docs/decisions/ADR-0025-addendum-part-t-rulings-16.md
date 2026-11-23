# ADR-0025 addendum — Part T rulings 16 (ruling 51), 2026-11-23

Ruling of the scientific lead (Claude Fable 5.2), made while Part T's registered run is PAUSED at its `train` stage and before any registered Part T outcome value has been read by anyone. ADR-0025 is not edited. No threshold, seed, cell, rate, scientific rule, training or scoring code, calibration selection or label changes. `Astra review: NOT_PERFORMED`. Claude review is not Astra review.

## The human lead's words (as reported by the lead from chat)

- 2026-11-22: "update cap and start over if necessary my cap is 6 days for any test".
- 2026-11-23, asked "Shall I set the bound to 205 charged hours?": "ok, yes continue at night how many ours you have left?" The lead reads "yes" as confirming 205 charged hours; this reading is for his review.
- 2026-11-23, asked whether the 50 finished cells may be scored early, and told why not: "agree, ok, so please work so we can resume today and have the result by tomorrow morning".
- 2026-11-23: "right the training is the only face that freezes my development work so as long as we complete the training by morning it's ok"; "got it we have until 8am tomorrow panama time".

## The event

Registered run in `experiments/P10IS2-T-registered-20261121`, freeze `c25d4f0b1d0ff5f529072cc7983c835a0267e2fb`. `gates` COMPLETE (1,428.6 s). `train` ended PAUSED at 17:01 local on 2026-11-23 (exit 4): 50 of 54 cells complete; 345,134.9 s (95.87 h) charged against the stage cap of 75.68 h; registered ledger 96.27 h; study total 120.48 h of the 151 h bound. No later stage started. No outcome value was read; the lead declined a proposal to score the finished cells early (`docs/PARAMETER_CHANGELOG.md` row 37).

Cause, from cost records only: the six M-ii cells ran three at a time; each holds about 32.5 GB of MPS driver memory with a peak resident set of 2.15 GB, so the 8 GiB per-worker guard (resident set) never refused and three cells exceeded the machine's 48 GB. The two that finished took 23,669 s and 25,535 s against 2,827 s in the counting rehearsal. Audit 16 had found that the frozen code checks the stage cap at wave starts and against wall clock inside a wave, and has no path to extend a cap or resume a stage whose cap is spent.

## Ruling 51

1. **Caps by cost projection.** The stage caps of `train` and `combined` are replaced by explicit charged-hour caps set on cost records and projections only: train 125.8 h (95.87 h charged plus 4 x 7.48 h for the unfinished M-ii cells); combined 6.0 h (Decision 2, item 6, had stated the combined projection before the run). Evaluate (21.77 h) and recompute (22.66 h) stay as frozen. The study bound is 205 charged hours on the human lead's word. The total of caps is 204.02 h.
2. **M-ii cells run one at a time.** A cost and memory measure only: the same cells, seeds, updates and code paths; three resume from their kept checkpoints and one starts.
3. **The cap check compares charged time** (the sum over worker processes), as ADR-0025 defines the cap, and a free-memory admission check holds back a further concurrent worker. Both change when work is allowed to start, never what is computed.
4. **Targeted rehearsal instead of a repeated full counting rehearsal.** The second freeze requires: the first counting rehearsal (COMPLETE against the pre-amendment plan), and a targeted rehearsal against the amended plan that runs one M-ii cell at registered size alone on rehearsal seeds (timed, with its memory recorded), a forced pause at a cap and a resume from a checkpoint through the amended mechanism, each new check made to refuse once, and a read-only preflight of the registered preconditions against the real worktree and run directory. The stages after `train` are not re-rehearsed: they are unchanged from the plan the first counting rehearsal completed against.
5. **Second freeze and second Decision 2; the run directory is resumed.** The first freeze record and Decision 2 are kept on record. The completed `gates` and the 50 completed cells stand as run under the first freeze; nothing completed is re-run. The amendment record lists every plan and config key that differs, and the code refuses any other difference.
6. **Nothing is launched before an independent audit** (audit 17) finds the amendment ready, and the targeted rehearsal's record is COMPLETE.

## Departures from ADR-0025, to be disclosed in the outcome record and report

- Section 7.1 rule 4 ("no Part T training or scoring file changes after a calibration output exists") is waived for the named non-training files of the amendment; calibration is not repeated and its selections stand.
- Section 10 item 3 (each stage cap is 2 x its projected time, by code from the measuring rehearsal) is replaced for `train` and `combined` by the explicit caps above; `combined` is about 3.7 x its measured projection.
- Section 10 item 5 (a counting rehearsal against the plan that is frozen): replaced by item 4 above.
- Section 9 and ruling 47: the bound changes a second time after the calibration output existed (95.68 → 151 → 205), each time on the human lead's word and on cost only.
- A registered stage ran above its cap (95.87 h against 75.68 h) because of the frozen code's wave-start and wall-clock checks.
- The amended run mixes cells trained three at a time under the first freeze with four M-ii cells trained one at a time under the second; three of those four resume from checkpoints written under heavy memory pressure. The computation per cell is the same; no registered quantity is a time or throughput reading.
- Machine state: Colima, stated stopped in Decision 2, ran from about 12:25 on 2026-11-22 to 12:40 on 2026-11-23; the ArborML Lab session's builds resumed on 2026-11-23 on the human lead's word.
- The memory admission check reads free system memory, not MPS driver memory.

## Limits

The caps and the bound were set knowing cost records only. Whether the amendment is blind to outcomes rests on the seal (no sealed value opened; attested again at the second Decision 2) and on the fact that no scoring stage has run. The wording of this ruling is the lead's, for the human lead's review; his words above chose the direction (update the cap, 205 hours, resume today).


## Records

- SHA-256 of `studies/p10is2/partt_amendment/AMENDMENT_RECORD.json` as committed: `10463ef919f9ec534d2d3e573d55810e2521fac5a003c51d3d6186d6c3c3b7ad`.
- Audit 17 (arbor-auditor, Claude Opus 5.5) found the amendment ready after fixes D1 (the plan difference check on the import walk) and D2 (a registered launch refuses `--rehearsal-arms`); both are made. A third defect found while making D1 is also fixed: `candidate-plan` chooses the calibration record by the same code-hash comparison (`chosen_calibration`), which now applies the amendment exemption as the freeze does.
