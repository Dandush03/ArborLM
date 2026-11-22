# ADR-0025 addendum — Part T rulings 15 (ruling 50), 2026-11-22

Ruling of the scientific lead (Claude Fable 5.2), made after Part T's freeze (`c25d4f0b1d0ff5f529072cc7983c835a0267e2fb`) and Decision 2, and after the first registered launch was refused; before any registered Part T value exists. The way forward was put to the human lead as two options and he chose this one in chat on 2026-11-22: **"agree with your recommendation"** (the recommendation was to take the records off the branch, recorded as a ruling and audited before the launch). ADR-0025 is not edited. No threshold, seed, cell, cap, rate, rule, code file, plan or config changes. `Astra review: NOT_PERFORMED`. Claude review is not Astra review.

## The event

On 2026-11-22 at 06:39 local the registered stage `gates` was launched once and REFUSED by the code after about one second (exit 2): "another study's freeze record is in this worktree (ruling L11)", naming `studies/p10i_s3/freeze/freeze_record.json`, `studies/p10i_s6/freeze/freeze_record.json`, `studies/p10ir/freeze/freeze_record.json`, `studies/p10is0/freeze/freeze_record.json`, `studies/p10is1/freeze/freeze_record.json` and `studies/p10is5/freeze/freeze_record.json`. Nothing registered was computed, no run directory was created, no registered seed was consumed and nothing was charged. The launch output is kept at `experiments/_scratch/p10is2_partt_registered_20261122/gates.out`.

## The finding

ADR-0025 section 19, ruling L11, reads: "a guard refuses to start a registered stage in a directory git would track, or in a worktree that another study's freeze record names". The guard (`studies/p10is2/common/plan.py`, `foreign_freeze_records`) refuses when any other study's freeze record file is present under `studies/*/freeze/`. That is stricter than the text. The six files are tracked files of `main` and arrived with the merges of `main` into this branch (needed for seed registry revision 7, ruling 45, and for the push hook). None of them names this worktree. The guard runs in registered mode only; no rehearsal exercised it against the merged tree, and audits 12 to 14 did not catch it.

`studies/p10is2/common/plan.py` is a frozen file. Changing the guard to match the text would mean a new plan and a repeated counting rehearsal (ADR-0025 section 10 item 5; 14.58 h), which the 151 h bound does not hold.

## Ruling 50

1. One commit on `claude/p10-i-s2-impl`, after the freeze commit, removes those six files from this branch's tree and adds this record. Nothing else changes. The six files are not Part T frozen files (Part T's frozen set is `studies/p10is2/**` outside `partq/` and `freeze/`, the Part T config, `uv.lock` and `pyproject.toml`), are not in the plan's frozen-input set or import walk, and are read by no Part T code.
2. The guard is not edited and still runs at every registered stage. **Stated plainly: this satisfies the guard by removing what it looks for.** What the registered rule protects (that a registered stage does not start in a worktree that belongs to another study's frozen run) is therefore established by hand before the launch, by the independent auditor: no other study's freeze record names this worktree, no other study's registered run uses it or is alive, and the run directory is git-ignored and does not exist.
3. The six files remain on `main`, unchanged. **They are restored on this branch (by reverting the removal commit) before the branch is merged into `main` or `main` is merged into it again**; no merge of this branch may delete them from `main`. `main` is not merged into this branch while the registered run is in progress (it could not be in any case: no write is made in this worktree during a registered stage).
4. This departure from the letter of the guard's intent is disclosed in Part T's outcome record and report, beside the disclosures of Decision 2. Decision 2 (`results/p10is2-partt-freeze-20261122/DECISION_2_PARTT.md`) stands as committed; it names the freeze commit, which is unchanged.
5. Limit of the authority: the human lead's words above chose this option; the wording of this ruling is the lead's, for his review.
