# Class table: comparison of the two derivations of the closed list (stage 1S point 8)

By the coordinating lead (Claude Fable 5.2), 2026-11-26. No rule script was run and no item generated.

- First derivation: `docs/reviews/adr-0033-m0-2026-11-20/addendum1_scripts/addendum1_rev7_uncounted_rules.json` on `claude/m0-spec` (SHA-256 `ccea7d78754480830f3887d27ac808e207c60ef4c4a444e47fe6a3fc4c2cd24d`).
- Second derivation: `../second_derivation/uncounted_rules_second.json` (SHA-256 `173a48f33aea5f5733d951224ea1b1524532cc0d7600cca61a35a4dd3df72205`), by an `arbor-auditor` context (Claude Opus 5.5) that did not open the first.
- Result: the two agree on every entry. R1 35 of 35 (rule and lineage scope); R2 35 of 35 class clauses (literal and class) and 3 of 3 new rules; M1 13 of 13 pairs; C1 66 of 66 (output, name) pairs, which are 63 distinct names.
- `compare_lists_v2.py` exits 1: its R2 comparison included the clause number, and the two derivations number differently (the first numbers `if` statements, so several literals share a number; the second numbers literals 1 to 35). `compare_r2_order.py` checks what matters: the same 35 (literal, class) pairs, in a consistent order. The comments in that script name the two numbering conventions the wrong way round; its checks are unaffected. Both outputs are kept as run.
- Nothing is struck. The class table to be hashed under point 9 (iv) is the first derivation's file, unchanged, together with the amendment list when the amendment auditor delivers it.
- The second auditor marked five of its judgements PENDING LEAD REVIEW (REPORT.md). In each the two derivations made the same call, so under point 8 ("where they differ, the rule counts") nothing changes. They are listed for the report to the human lead.

Astra review: NOT_PERFORMED
