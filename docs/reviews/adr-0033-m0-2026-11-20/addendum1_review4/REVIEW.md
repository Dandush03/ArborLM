# Check 4 of ADR-0033 addendum 1, draft 4 (narrow scope)

**Verdict: APPROVABLE AFTER REQUIRED CHANGES.** 0 blocking, 4 required (H1–H4), 6 notes (H5–H10).

- Ran as: `arbor-auditor` role, Claude Opus 5.5 (`claude-opus-5-5`), 2026-11-26. I wrote none of the addendum, ADR-0033, the earlier reviews or the implementation. This is independent engineering and mathematical evidence. It is not Astra validation and not human approval. Scientific questions are marked PENDING LEAD REVIEW. No model was run, nothing was downloaded, no sealed value was read, and no git state was changed.
- Reviewed: `docs/decisions/ADR-0033-addendum-1-lineage-clusters.md` at `471a1edb` (`claude/m0-spec`). SHA-256 `96b0c07f…ba78` both in the working tree and in `git show 471a1edb:`. I read the diff against `9788a8ef`. Parent ADR-0033 is `7719f6d4…ec90b`, which matches the citation. Also read: review 3 (`addendum1_review3/REVIEW.md`); `HUMAN_LEAD_WORDS_6.md` (worktree `agent-a0c9d741…`, `04c979f6`); `studies/m0/core.py` at `9bcec484` and seed constants and `stream(` call sites at `04c979f6`, read only through `git show` / `git grep`.
- Drafter's inputs reproduce: `partition_vector_rev4.py` `3b28dbbb…527f`, output `c4fbae36…ec8d`; `addendum1_rev4_arithmetic.py` `f4883502…b94d`, output `807eaba0…afe7`. I re-ran both and the outputs are byte-identical (`rerun_drafter_*.out.txt`).
- Environment: macOS 27.2.1 arm64, uv 0.12.15, CPython 3.12.14, the locked environment of worktree `agent-a0c9d741ea96ce52f`, standard library only. Commands were run from that worktree, with `D` = this folder and `S` = `…/arborlm-consolidation-experiment-2b31c1/docs/reviews/adr-0033-m0-2026-11-20/addendum1_scripts`:
  - `uv run --locked python -I -B $D/partition_check4.py $S/partition_vector_rev4.py > $D/partition_check4.out.txt`. This loads the drafter's file read-only, and only for the differential test of part 3.
  - `uv run --locked python -I -B $D/arithmetic_check4.py > $D/arithmetic_check4.out.txt`. **This is a failed attempt and I kept it.** Its integration bound was wrong for large non-centrality, so every cell of table (c) printed 5.000. Everything above table (c) is identical to attempt 2.
  - `uv run --locked python -I -B $D/arithmetic_check4b.py > $D/arithmetic_check4b.out.txt`. Attempt 2, with the bound fixed. This is the one cited.
  - `uv run --locked python -I -B $S/{partition_vector_rev4,addendum1_rev4_arithmetic}.py > $D/rerun_drafter_*.out.txt`
- Process disclosure:
  - I read the drafter's `partition_vector_rev4.py` before I wrote my partition code. My code is my own (BFS components, an explicit `_randbelow` shuffle loop, separate counting), but it is not a blind from-text implementation.
  - The concrete maps of V6–V8 are copied from the drafter's script, because the addendum describes them only in words.
  - I wrote the files with a shell heredoc. No other path was written.

## Scope 1. Review 3, G1–G7

| Item | Status | Where |
|---|---|---|
| G1 | **fixed** | §4 item 8: "No stream with the label `cluster-partition` is computed on any map of written lineages other than the map of record". The same item and stages 1–2: the map and the candidate list are hashed before stage 3. Stage 0: "Every seed is fixed here … None is chosen fresh". What remains (who decides which runs enter the manifest) is new, in H1 and H2. |
| G2 | **fixed** | Stage 4, "How a count is made": `stream(400002, "capacity", e, id, str(v))`; key set per lineage and level; 40 × T + 1,000; 500 retries; "No set of used texts or keys is shared"; union for the cluster; re-draw "from the start of the same stream". The "largest set" claim is kept with its proviso. |
| G3 | **fixed** as to naming the governing partition: "The partition first computed governs for good" (§4 item 7; A20, carried as a lead ruling and disclosed as such). The new rules have gaps (H3). |
| G4 | **fixed** for (a), (b) and (c): step 1 with item 17, steps 2 and 3 in clusters with item 20, and V6–V8, where V6 has the three properties asked for. The account of draft 3's item 9 is wrong (H4). |
| G5 | **fixed**: §7 items 2 and 4 are drafted as R-31 to R-38 and marked as the option favourable to passing; §13 item 18, with the line "observed before" in the preamble of the new items. |
| G6 | **fixed**: §13 item 19 is open with F as the deadline; §9 item 4: "Draft 3's fallback … NOT COMPUTED … is withdrawn". |
| G7 | **fixed**: every row of the reviewer's table was checked by grep for "propos", "until he decides", "if approved", "his to decide" and the like. No residual undecided wording remains on a decided item. The remaining hits are quotations of ADR-0033, item 11, or the new items 17–20. |

## Scope 2. The placement of groups and V1–V8 (`partition_check4.out.txt`)

- **V1–V8 reproduce exactly** under every option the text lists: item 17 (a) pass and (b) ignore; item 20 (a), (b) and (c). There are 0 mismatches with the drafter's printed part A and with the draft 3 outputs for V1–V5.
- The figures quoted in §13 items 17 and 20 all reproduce: V6 changes two R1 clusters (R1.e and R1.g); V7 is 1/3 against 2/2 when counted in groups, and 2/2 under both readings when counted as drafted; V8 is 3, 1 and 4 of 6.
- The explicit shuffle loop of §4 equals `random.shuffle` on all five streams.
- **The rule can be executed without a further choice** once items 17 and 20 are taken. `build_item`'s `part` and `ident` arguments do not reach `lin.build(level, rng)`, so they create no choice.
- **Random maps.** I ran 4,000 random maps (seed 20261126; 0–9 lineages per evaluation; candidate probability 0.8; random links and borderline pairs), comparing my code with the drafter's `partition()` under 6 option pairs:
  - 0 disagreements.
  - With the borderline pairs removed, all eight option combinations agree on all 4,000 maps, as the text claims.
  - No group is ever split across parts.
- **Does the held-out part always get at least as many clusters? No.**
  - Under the drafted option, per evaluation, A > B in 1,345 of 14,091 evaluation-instances (9.5 %).
  - In every one of them a_e > ⌊N_e/2⌋, so the cause is step 2. Step 3 never takes A above ⌊N_e/2⌋ (0 cases), as item 20 claims.
  - With the borderline pairs removed, the rate is 270 (1.9 %).
  - Step 2 ends with B < A in clusters in 973 of 4,000 maps with borderline pairs, against 0 without them.
  - Summed over the four evaluations, B < A in 461 maps.
  - These rates depend on my made-up map distribution (H5).

## Scope 3. Re-record (§4 item 7, A20)

See H3. Two things in short. First, rules (ii), (iii) and (v) presuppose a new map, but stage 1 forbids any change of link or borderline pair after the hash. Second, if the map may change, the new judgements are made with the split in view and can move chosen clusters to part B. The following cases are not covered:
- a part cluster merged with a cluster that had no part and now has a candidate, where (ii) and (iv) give different answers;
- a lineage new to the map;
- whether stage 4 restarts after a re-record.

## Scope 4. Seeds (A21)

- **No collision.** At `04c979f6` the only streams on 400002 are `generate_pool`'s `stream(400002, "development", "", e, p, lineage, level)` (`ggen.build_pools`, two tests). The new first labels `capacity` and `cheap-rule` differ from `development`, so no joined string can coincide (the ids contain no `|`). Every other row of ADR-0033 §12 is a different seed.
- The implementation's existing `capacity` streams are on 409001 (`ggen.py:205`) and 953601 (`lineage_gates.py:181`), so they are different strings.
- The label `cluster-partition` appears nowhere in `studies/`, `tests/` or `docs/` at `04c979f6`, nor in the two untracked `.bak` files. The word `cheap-rule` appears there only in prose.
- **The manifest is not enough** (H1), and the derivation for unseeded scripts leaves a choice (H2).

## Scope 5. Stage 4 (`arithmetic_check4b.out.txt` parts 2–4)

- **Stage 4 can be run as written.**
- My stage-4 code reproduces example 4b under A23. Under review 3's simultaneous reading the strong lineage c1.x is also lost, so registration falls from 4 to 3 clusters.
- Since the fixed point re-tests (ii) on every surviving cluster, A23 weakens nothing at the fixed point.
- k × D_lin(G, k) ≥ D(G) for every G ≤ 400 and k ≤ 20.
- **Knife-edge (slack exactly 0)**, G ≤ 40:
  - k = 2: G = 1, 2, 4, 5, 7, 8, 10, 16, 20, 22, 23, 25, 26, 29, 31, 36, 40.
  - k = 4: G = 1, 2, 4, 5, 8, 10, 20, 25, 36, 40.
  - k = 5: G = 1, 2, 4, 5, 8, 10, 16, 20, 25, 32, 40.
  - Never at k = 3, 6, 7 or 8.
  - The maximum slack at G ≤ 19, k ≤ 8 is 160 keys.
  - The text gives k = 2 only (H6). The k = 2 list for G ≤ 19 is correct.
- The proviso of the "largest set" claim can fail: in a made-up sequence, the count is 99 at target 100 and 200 at target 200. The text calls it unchecked (H7).

## Scope 6. Section 6 at G = 2 to 5 (`arithmetic_check4b.out.txt` part 1; my own method, integrating over the normal variable with closed-form χ² CDFs)

Every figure printed in the G = 2–4 table reproduces:
- t quantiles 6.314, 2.920, 2.353;
- floor rows;
- (b) "not at any τ" for 0.02; 0.0012 (0.0044) and 0.0063 (0.0078) for 0.03; 0.0092 (0.0116) and 0.0147 (0.0166) for 0.05;
- (c) 0.072 (0.052), 0.029 (0.025), 0.023 (0.021); 0.401 (0.287), 0.135 (0.115), 0.093 (0.084); 1.316 (0.942), 0.441 (0.375), 0.301 (0.273).

The other figures checked also reproduce:
- power at τ = 0, δ = 0.05, G = 2: 0.9566 / 0.9952;
- G = 5, δ = 0.02: 0.9935 / 0.9971, and CR0 reachable up to 0.0016;
- G = 6: 0.0010 / 0.0033;
- the CR0 increments 0.0012–0.0016 (G = 5), 0.0008–0.0011, 0.0006–0.0009, 0.0005–0.0008, 0.0004–0.0006;
- tables (a), (b) and (c) at G = 5–19.

No discrepancy.

## Scope 7. The sixteen decided items

- Items 1–16 of §13 each show the option in the `HUMAN_LEAD_WORDS_6.md` table, and I found none that differs.
- Item 2's remainder (the CR form) is correctly split off as item 19.
- One misstatement concerns item 9's mechanics (H4).
- Sentences that weaken a requirement beyond the sixteen:
  - rule (v) of §4 item 7 suspends decided item 9 after a re-record, and is not listed as such in A20 (H3);
  - §7 items 2 and 4 under item 18 (a), which is open and disclosed as favourable to passing.
- I found no other weakening sentence.

## Findings

**H1 (REQUIRED). §4A stage 0, §7 item 2, A21: the manifest closes the set of cheap-rule runs, but nothing fixes which runs go into it, and every result is already seen.** "A manifest lists … every run that enters the pooled estimate" is circular. Whoever writes it at stage 0 chooses membership with the per-run figures in view, and hashing afterwards prevents only later changes.

The record has real choices of this kind:
- failed attempts (`audit3_m1/shortcuts_a3_attempt1.py`, `audit4_m1/shortcuts_a4_attempt1.py`, `final_m1/rules_a5_attempt1.py`);
- two pooling versions (`final_c1/f4_pool.py`, `f4b_pool_v2.py`);
- runs before and after the repairs on different generator code;
- throwaway seeds (5, 17, 410301–410303, 777103, 777105, 424242).

Figures sit near the bound: `graph_shortest_route_r6` gives 0.149, 0.158, 0.169 and 0.173.

Smallest fix: fix membership by rule in the text: every run of a counted-rule script on each lineage's final generator version, whose output is committed at a named commit, excluding only runs that the record already marked as failed attempts before draft 4, listed by name. An auditor checks completeness against git history. Any lineage whose drop or keep status under the manifest differs from R-38 is reported to the human lead.

**H2 (REQUIRED). §4A stage 0: the derived seed for an unseeded script is not unique.** In `sha256("400002|cheap-rule|" + its file name)`, "file name" can be the base name or the repository path, which give two integers. The text also does not say how the integer enters the script: a module constant edited (which changes the file hash in the manifest) or an argument. Both readings can be computed before choosing. Smallest fix: "the base name, as the second label of the derivation of section 4; the integer replaces the script's seed by a one-line change, recorded with the new file hash."

**H3 (REQUIRED, PENDING LEAD REVIEW). §4 item 7 against §4A stage 1; A20.**
- **(a) Contradiction.** Stage 1 says that after the map's hash "no link or borderline pair is added or withdrawn". Yet rules (ii), (iii) and (v) deal with a new map that joins, separates or adds borderline pairs.
- **(b) If a re-record may change the map, something is choosable after the split is seen.** The new link and candidate judgements are made with the split visible. Through (ii), linking any part-A cluster to any part-B cluster moves it to B. Through (iv), making a no-part lineage a candidate places it in B. So "leaves nothing to choose after a split has been seen" overstates the rule: it leaves moves toward part B.
- **(c) Cases not covered:**
  - a part-A cluster merged with a cluster that had no part and now has a candidate, where (ii) (lineages of different parts? "no part" is not a part) and (iv) (the cluster "had no part"?) give A or B;
  - a lineage new to the map (for example after a domain-list change) that joins an existing part cluster;
  - whether stage 4 restarts from the new candidate list, which could bring back a lineage dropped at capacity under the first record at a new G.
- **(d)** Rule (v) suspends decided item 9 after a re-record. That is a lead ruling that weakens a decided item, and A20 does not say so.

Smallest fix:
- state whether a re-record may change the map; if not, delete (ii), (iii) and (v);
- if it may: allow changes only by the map's auditor with written reasons, and add "a cluster with a candidate that contains a lineage that had no part, or lineages of different parts, is in part B; a lineage new to the map is in part B; stage 4 is run again from the new candidate list";
- name (v) in A20 as an exception to item 9;
- reword the claim to "leaves only moves toward part B".

**H4 (REQUIRED). §4 item 9, §13 items 9 and 20, A24: draft 3's item 9 is misdescribed, and with it what the human lead decided.**
- §4 item 9 says that what is placed is "Not decided, because draft 3's item 9 did not say … how a group of several clusters is placed".
- In fact draft 3 §4 item 9 (`9788a8ef`, line 89) said "N_e, a_e, |L_e| and k_e are counted in groups", and draft 3's §13 item 9 pointed to it ("mechanics in section 4 item 9").
- The lead recorded that the sixth decision accepts each item "as that section words it". Draft 4's own item 20 says "draft 3's item 9 counted N_e, a_e and k_e in groups".
- So decided item 9 referenced option (c), and decided item 5 asks for the larger half held out in clusters. Item 20 resolves a conflict between two decided items. It does not fill a gap.

Smallest fix: say that, and present (c) as the mechanics item 9 referenced, so that the human lead sees he is choosing between his own items 5 and 9.

**H5 (NOTE, PENDING LEAD REVIEW). §4 step 2 and step 5; summary row 20.** Once a group holds several clusters, step 2 can leave part B smaller than A, both overall and per evaluation. In my random maps this happens in 24 % of maps at step 2 and in 9.5 % of evaluations (against 0 % and 1.9 % without borderline pairs). Decided item 5 (iii)'s "larger half held out in both steps" therefore no longer holds at step 2. The text says so by an example; the frequency was not shown. No vector exercises a group that makes a_e > ⌊N_e/2⌋.

**H6 (NOTE). §4A stage 4 and §12 item 15: the knife-edge is listed for k = 2 only.** Slack is also zero for k = 4 (G = 1, 2, 4, 5, 8, 10) and for k = 5 (G = 1, 2, 4, 5, 8, 10, 16), and never exceeds 160 keys at G ≤ 19. In practice, any overlap of more than a few dozen keys between siblings fails the whole cluster. Fix: give the full list and the 160 bound.

**H7 (NOTE). §4A stage 4.**
- The monotonicity proviso can fail when the attempt budget binds, as my constructed example shows. The text already calls it unchecked, and the fixed point is well defined without it.
- Separately, capacity streams carry no part label, so each lineage's counts can be previewed before stages 1 and 2. No sentence forbids that, unlike the partition streams. The effect is small because working capacity figures already exist.

**H8 (NOTE). §13 item 20 (c): the drafter's rendering of "as draft 3's item 9 read" differs from that text in the group identity.** Draft 3 uses the smallest cluster identity in the group; the drafter uses the smallest among candidate clusters. The two give different parts in 269 of 4,000 random maps (under item 17 (a)). V6–V8 are unaffected.

**H9 (NOTE). §13 items 17 and 20 and the summary table.** The recommendations are "the drafter's, for the coordinating lead to confirm". They should be confirmed, or marked unconfirmed in the summary table, before the text goes to the human lead.

**H10 (NOTE). §4A stage 0, §12 item 7.** The seeds of the cheap-rule runs on record include values outside the requested block 400001–409999, among them 410301–410303, 777103, 777105, 424242, test-block 953xxx values and the audit seeds 5 and 17. Through the manifest they enter G-gen's record, so they belong on the seed-registry auditor's list along with the labels.

## Files

`partition_check4.py` / `.out.txt`; `arithmetic_check4.py` / `.out.txt` (failed attempt 1, kept); `arithmetic_check4b.py` / `.out.txt`; `rerun_drafter_partition_vector_rev4.out.txt` (= `c4fbae36…ec8d`); `rerun_drafter_addendum1_rev4_arithmetic.out.txt` (= `807eaba0…afe7`). Hashes in `SHA256SUMS.txt`.

Astra review: NOT_PERFORMED
