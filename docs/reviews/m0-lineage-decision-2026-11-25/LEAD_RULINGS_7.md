# M0 lineage repair: lead rulings after the independent final checks (2026-11-25)

By the scientific lead (Claude Fable 5.2). Final checks by four `arbor-auditor` subagents (Claude Opus 5.5), each with its own solver written from item text alone: `final_r1/`, `final_r2/`, `final_m1/`, `final_c1/`, copied by the lead unchanged from each auditor's `deliver/` directory. Cross-evaluation map proposed by a fifth `arbor-auditor`: `cross_evaluation_map/`. Nothing here registers a lineage; no model has been run on any M0 item.

## What the final checks found

| Evaluation | Key mismatches (auditor's text-only solver) | Items with no unique answer | Largest pooled excess on the counted rules, survivors | Lineages / clusters after R-38 |
|---|---|---|---|---|
| R1 | 0 / 126,000 | 0 | 0.126 | 10 / 8 |
| R2 | 0 / 133,000 | 0 | 0.141 | 16 / 16 (plus `to_base_wide` held) |
| M1 | 0 / 304,500 | 0 | 0.087 | 29 / 17 (eight held on capacity; 16 clusters if they are dropped) |
| C1 | 0 / 94,500 (two Python versions) | 0 | 0.111 | 26 / 17 (15 without the two variants) |

Full M0 suite on the repaired code: 1,331 passed, 2 xfailed, 0 failed (`experiments/_scratch/m0_fix4_suite_20261125/pytest_m0_full.txt`); ruff clean.

## Rulings

- **R-38 (new cheap rules count).** The lead's brief to the final auditors said rules they newly found would be reported and would not decide a drop. That is withdrawn before any use: a cheap rule or closed form found in the final check counts like any other, because dropping is the conservative direction and needs no repair. Dropped under it or under R-32:
  - R1 `graph_shortest_route_r6` (pooled 0.163 over four runs: 0.149, 0.158, 0.169, 0.173);
  - R1 `conditional_decision_tree_r6` (new rule "root light, then the commonest action": 0.198);
  - R2 `digit_root` (new rule "digit sum once, first digit": 0.20 at every level);
  - R2 `interval_scheduling` (new rule "fewest clashes first": 0.23 to 0.51);
  - C1 `sieve_marking_f4` (closed form, 1.000 at every level).
  The classes not counted stay not counted (R-31): R2 `crt_smallest`'s truncated search (0.37, classed partial) does not drop it. What would drop if those classes counted is in each report and goes to the human lead: R1 to 6 clusters or fewer, R2 by about ten lineages, C1 to 15 clusters.
- **R-39 (same treatment for capacity).** R2 `to_base_wide` (whole item space at level 0 is 15,928 against 27,680) is held under R-36 like M1's eight, not dropped; the R2 implementer's NOT_REGISTERED mark for it is read as held. Its cluster stands through `from_base` either way.
- **R-40 (pending points, left as they are).** Reported, not acted on: R1 Venn levels 0 and 1 differ only in the question and number size; R2 `dictionary_rank` barely rises from level 1 to 2 and `from_base` shares 317 texts across levels; M1 `gcd_lcm` has a false general rule exact at levels 3 to 6 and its mean log answer dips from level 2 to 3; C1 within-shape rates of 0.30 (`slices_f4`) and 0.17 (`binary_search_f3`). None is above the bound as R-34 applies it. They are listed for the human lead.
- **R-41 (manifests are stale).** The implementers' fix-4 manifests and notes predate R-38 and R-39 (and `NOTES_FIX4_R2.md` still shows 19 survivors in places). The set of record for any later step is the fix-4 manifests minus `cross_evaluation_map/drops_after_final_checks.txt`; a consolidated manifest is to be built before G-gen, not now.
- **R-42 (cross-evaluation counts after the drops).** `cross_evaluation_map/s04_recompute_after_final_checks.out.txt`: strong pairs only, 7 cross-evaluation clusters, parts of R1 4/4, R2 8/8, M1 8/9, C1 8/9 whatever the shuffle; strong and borderline merged, R1's smaller part is 2 or 3 clusters, the others 8. No split of the real clusters with the registered seed has been computed.
- **R-43 (stop).** The work the human lead's fifth decision covered is finished. Registration, a third review of addendum 1, and anything else wait for the human lead's decisions (addendum 1 draft 3, section 13).

## Slips this round

Implementers: `sed -i` on `/dev/null` once (R1); `ruff check --fix` over other implementers' files (M1; suite unaffected); a test left hanging to its 900 s timeout (R2). The lead: an ambiguous G in the capacity brief (R-30); crediting the two-sided reading to the human lead (R-33); the brief line withdrawn by R-38. A background `cat` (pid 47844, child of 47842) left by the C1 implementer of fix round 3 is still running; not signalled.

Astra review: NOT_PERFORMED
