# M0 fresh run: amendment audit report (ADR-0033 addendum 1, approved 2026-11-26 as draft 7 with one amendment)

- **Role:** amendment auditor (section 4A stage 1S point 8, last bullet; section 12 items 29 and 30; section 13 item 23).
- **Model I ran as:** Claude Opus 5.5 (`claude-opus-5-5`), in an `arbor-auditor` context.
- **Independence:** I wrote none of the lineages, none of the rule scripts and not the closed list. I am not the context making the second derivation.
- **Not done, as the brief requires:** I ran no rule on any item, generated no item, opened no run output or past figure (no `.txt`, `.jsonl`, `.log` or `.json` result file of any run), and did not consult which lineages are near the bound.
- **Read-only everywhere else:** I wrote only inside `/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_fr_amendment_audit_20261126/`. I made no edit, commit, stage or push anywhere.

**Astra review: NOT_PERFORMED.** This audit is independent engineering and mathematical evidence. It is not Astra validation and not human approval. No result here is a success of anything.

## Inputs (exact)
- **Approved text:** `git -C /Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/arborlm-consolidation-experiment-2b31c1 show 2c944302:docs/decisions/ADR-0033-addendum-1-lineage-clusters.md`. My copy's SHA-256 is `154d16a0597dc8b2d41179ded63a5da3e6e92aa4f7b414fefda1f93cd4d0923c`.
- **Human lead's words:** `/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f/docs/reviews/m0-lineage-decision-2026-11-25/HUMAN_LEAD_WORDS_9.md`.
- **Code:** `b78e58b1f47619f070dfc6c0a88999d345b1a34b`, read through `git show` in `/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f`.
- **Survivor list of record:** `studies/m0/manifests/survivor_list_of_record.json` at that branch's tip `206d45a9b91cd38413c12e543e4d988d4d85d05f`. SHA-256 `0b658145a825490647b99eeab449bd442057fcd177a0be848fafa1868a87be0d`; I read the ids only.
- **Closed list:** `git show 2c944302:docs/reviews/adr-0033-m0-2026-11-20/addendum1_scripts/addendum1_rev7_uncounted_rules.json`, read only to see which rules are already entries. SHA-256 `ccea7d78754480830f3887d27ac808e207c60ef4c4a444e47fe6a3fc4c2cd24d`, which equals the hash the text states.

## Commands and environment
- **Source extraction (no execution):** `git show b78e58b1:<path> > experiments/_scratch/m0_fr_amendment_audit_20261126/work/src/<flattened name>`, run for every `.py` file under `studies/m0/` and under `final_r1/`, `audit3_m1/`, `audit4_m1/`, `final_m1/` and `audit4_r1/`, plus `audit4_c1/s5*` and `audit4_c1/s4_rules_v2.py`.
- **Rule-name enumeration, parse only.** I ran it from the implementation worktree:
  `uv run --locked python /Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_fr_amendment_audit_20261126/deliver/scripts/enumerate_r1_rule_names_v2.py /Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_fr_amendment_audit_20261126/deliver/r1_rule_names_enumerated.json`
  - Python 3.12.14, from the locked environment; standard library only (`ast`, `json`, `subprocess` for `git show`). It imports and executes no repository file.
  - Attempt 1 (`scripts/enumerate_r1_rule_names.py`) failed with `AttributeError: 'Assign' object has no attribute 'keys'` before writing any output. That was my bug: a helper returned the assignment node, not its dict. It is kept, and attempt 2 differs from it only in that line and the header.
- **No other script was run.** The counterexamples in `CONSIDERED_AND_COUNT.md` are hand arithmetic on values inside the builders' stated ranges.

## Counts
| Evaluation | Entries on the amendment list | Considered and left counting |
|---|---|---|
| M1 | **0** | 4: `a3:k_minus_remainder_ignores_exact_fit` (division_counting), `a3:largest_le_sqrt` (prime_factors), `a3:fermat_misapplied_e_mod_p_plus_1` (last_digit_power), `a3:parity_fraction_of_total` (slot_permutations: no survivor lineage has this stem) |
| R1 | **0** | every in-scope name for the 10 survivors: 196 (lineage, name) pairs as parsed across units R1a, R1b and R1c, less 27 parsed keys that are not rule names (compass 17, grid 8, knights 2), so 169 rule names, all left counting (`CONSIDERED_AND_COUNT.md`) |
| C1 | **0** | `EFF_F`: no entry, as the text requires (the fact is below) |

`amendment_list.json` is `{"commit": "b78e58b1f47619f070dfc6c0a88999d345b1a34b", "entries": []}`, with SHA-256 `a861df02fb54662b0aa6f8ff151ec12c7f627fa3c8cc532a09db78f7516ccaf1`.

## C1 `EFF_F`: can its components be read apart from what `s5_analyse_v2.py` writes? No.
File: `docs/reviews/m0-lineage-decision-2026-11-25/audit4_c1/s5_analyse_v2.py` at `b78e58b1` (SHA-256 `b6ed2ec95426058a79a8f39ffeff55f7dbc0c4f93fc350a273ca2166a0c6f0df`).
- **Written as one number.** `EFF_F` is written only as `round(eff(its, ("S", "G", "M", "F")), 3)`, one rounded number per lineage and level (line 86).
- **How it is formed.** `eff()` (lines 34-62) works per fold (lines 37-39). On the training fold it picks, for each shape, the best of the shape's most frequent key and every rule whose prefix is allowed (lines 44-53). It scores that choice on the other fold (lines 54-61).
- **The choices are not written.** The per-shape choice `choice[sh]` (line 53) is a local variable and appears in no output, and neither do the per-fold hit counts.
- **The `G.*` rules are not written.** Single rules are written only for the prefixes `S`, `F`, `M` and `H` (line 79). No `G.*` rule is written anywhere, though `EFF_F` can choose one.
- **The written figures are of a different kind.** The single-rule figures that are written (`rate_in_shape`, `share_of_level`, line 82) are whole-shape rates rounded to 3 decimals. They are not the train-fold choice scored on the test fold that `EFF_F` is made of. `MF_in_shape_cv` (line 83) is a separate cross-validated figure.
- **So the components of `EFF_F` cannot be read apart from what `s5_analyse_v2.py` writes.** This agrees with the text (point 6, fourth bullet).
- **One further fact, reported and changing nothing.** `s5_analyse_v2.py` reads per-item records (lines 68-69) written by `audit4_c1/s4_rules_v2.py`. Each record carries `i`, `key`, `shape`, `R` (that item's prediction of every rule) and `err` (`s4_rules_v2.py:610`, written at 618-620). Those records are an output of units C1a and C1c, so the composite could in principle be re-formed rule by rule from them, but only by new code. The text holds no rule for forming the composite from its parts, and no run copy may add one (point 3; point 8, C1 bullet of the amendment). Whether that counts as "read apart from committed outputs" is the text's call, and the text answers it: `EFF_F` counts whole. **PENDING LEAD REVIEW only if the lead wants that reading re-examined.**

## Found by reading code, outside or at the edge of the scope (PENDING LEAD REVIEW; I changed nothing)
These are consequences of the text as approved, derived from code alone and not from any figure.

1. **`R1.equivalence_exchange_rates_r6`: an in-scope, counted rule is right on every item by construction.**
   - The rule is `a4:direction_ignored_q_over_p`, in the `.aud` output of R1a and R1b (`studies/m0/r1_fix4_a4_heur.py:229-245`; `final_r1/a4copy/heuristics4.py:226-242`).
   - The generator writes every rate in path order from `x` toward `y` (`studies/m0/lineages_r1_fix4_a.py:124` with `_spine`, `lineages_r1_fix3_b.py:24-31`). So "always multiply by q/p" equals the answer on every item.
   - I left it counting: it skips the direction step a correct solver must perform, and it agrees only through a regularity of the generator (full argument in `CONSIDERED_AND_COUNT.md`).
   - Under point 8 (exact rows), an exact R1 rule that is on neither list counts. So this rule's excess is 1.0 at every level by construction, and it drops the lineage in the fresh run. Past audits set such rows aside by result (`audit4_r1/final_table4.py:60`; `final_r1/pool_final.py:56`), which the approved text no longer does.
   - The same regularity means the items never test whether a reader respects the direction of a rate. That is a construct question about the lineage, for the lead.
2. **`R1.venn_counting_r5`: counted closed forms are right on every item at five of the seven levels.**
   - The ask is fixed per level (`lineages_r1_fix3_d.py:350`). By algebra on the regions, these in-scope rules of `h_venn` (`.aud` with `a3:` and `.impl` without, in R1a and R1b) equal the answer on every item:
     - `ignore_triples` at level 0;
     - `sizes_minus_2pairs` at level 1;
     - `pairs_minus_3triples` at levels 3 and 6;
     - `pairs_minus_2triples` at level 4.
   - None is right at every level, so none is the lineage's procedure under the per-lineage test. They count.
   - Under the text, the lineage's excess at those levels is 1.0 by construction. Past audits set these rows aside as exact.
   - **Whether a per-level showing was meant is a question about the wording ("per lineage") that only the lead can answer.**
3. **`a3:parity_fraction_of_total` reaches no survivor.** The amendment's M1 case names it "for the lineage of its partner" (`slot_permutations`). No survivor-list id has that stem: `M1.slot_permutations_r4` is NOT REGISTERED (R-26, `studies/m0/lineages_m1_fix4.py:277`). The case is void, not decided.
4. **The R1 `considered_and_counted` list of the closed-list table is empty.** Point 8 says that for each evaluation the table holds the rules that were considered and count, with the reason. For R1 its list is `[]` (the R1 counted classes are described only in `notes`). This is for the second-derivation comparison, not for this audit.
5. **The M1 PROC reasons describe partial procedures.** Three of the four M1 partners in `PROC` (`audit4_m1/short_summary_a4.py:11, 19, 22`) carry reasons that themselves describe a partial or idle-step procedure: wrong on exact fits; drops a cofactor above √n; right only where e ≤ p. So the closed list's `im:` entries for those three lineages leave uncounted rules that are not the full procedure on every item. That follows the text's mapping (committed label → uncounted) and is not within this audit's power to change. I note it because the amendment's test, applied to the `im:` partners, would not have uncounted them.

## Mistakes of my own (kept)
- The enumeration attempt 1 failure, described above.
- My first draft of `CONSIDERED_AND_COUNT.md` cited several builder line ranges one or two lines off. I corrected them after re-reading. The first draft is kept at `/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_fr_amendment_audit_20261126/work/CONSIDERED_AND_COUNT_draft1.md`. No decision changed.
- In the first version of this report I wrote "less 21" for the parsed keys that are not rule names. Counting them again gives 27 (compass 17, grid 8, knights 2). I corrected it before the hashes.
- The parser also returned helper-dict keys that are not rule names, for example the compass turn amounts and the grid step table. I listed them and set them aside by hand (`CONSIDERED_AND_COUNT.md`, "Where the rule names come from").
- The Write tool refused paths in this directory (a worktree hook), so every file here was written with a shell heredoc or `python3` writing inside this directory, as the brief allows.

## Tests
Not applicable: I changed no repository code and ran no test suite.
