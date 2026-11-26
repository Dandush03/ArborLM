# M0 fresh run: amendment audit, showings (ADR-0033 addendum 1, section 4A stage 1S point 8, last bullet)

Auditor: an `arbor-auditor` context run as Claude Opus 5.5 (`claude-opus-5-5`). I wrote none of the lineages, none of the rule scripts and not the closed list. I am not the context that makes the second derivation of the closed list.
Commit read: `b78e58b1f47619f070dfc6c0a88999d345b1a34b`, via `git show`, in `/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f`.

## Entries

**None.** The amendment list (`amendment_list.json`) holds no entry. I could not show for any rule in scope (M1: the four audit-3 rules; R1: every rule of units R1a, R1b and R1c for the ten R1 survivors whose bare name is not in `M` or `EXCL`; C1: no entry by the text) that, on every item its lineage's generator can build, it carries out the steps a correct solver must carry out and returns the generator's answer by those steps. So no rule has a showing section.

Everything I considered, and why each one still counts, is in `CONSIDERED_AND_COUNT.md`. Two R1 cases came closest, and I set out the full reasoning for them there:
- `a4:direction_ignored_q_over_p` for `R1.equivalence_exchange_rates_r6`. By reading the code, it is right on every item. It does not carry out the direction step, and it agrees only because of a regularity in the generator.
- The inclusion–exclusion closed forms for `R1.venn_counting_r5`. By reading the code, each is right on every item at one or two levels and wrong at the others.

Both are flagged in `REPORT.md` as PENDING LEAD REVIEW.

Astra review: NOT_PERFORMED. This is not Astra validation and not human approval.
