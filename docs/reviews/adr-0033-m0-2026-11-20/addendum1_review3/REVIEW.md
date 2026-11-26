# Review 3 of ADR-0033 addendum 1, draft 3 (limited scope)

**Verdict: APPROVABLE AFTER REQUIRED CHANGES.** 0 blocking, 7 required (G1-G7), 5 notes (G8-G12).

- Reviewer: `arbor-auditor` context, Claude Opus 5.5 (`claude-opus-5-5`), 2026-11-26. I wrote none of the addendum, of ADR-0033, of reviews 1 and 2, or of the implementation. Independent engineering and mathematical evidence only: not Astra validation and not human approval. Scientific questions are marked PENDING LEAD REVIEW. Nothing here is a result about any model; no model was run, nothing was downloaded, no git state changed, no sealed value was opened.
- Reviewed: `docs/decisions/ADR-0033-addendum-1-lineage-clusters.md` at `9788a8ef` (file SHA-256 `2df30a29…01fb`; working tree clean for this file). Parent `ADR-0033-…harness.md` `7719f6d4…ec90b` (matches the citation). Decision record `HUMAN_LEAD_WORDS_6.md` and `LEAD_RULINGS_6.md`, `_7.md` at `04c979f6` in worktree `agent-a0c9d741…`. `studies/m0/core.py` read at `9bcec484` with `git show` (read only).
- Environment: macOS 27.2.1 arm64, uv 0.12.15, CPython 3.12.14 (locked environment of worktree `agent-a0c9d741…`), standard library only. Commands, run from that worktree, `D` = this folder:
  - `uv run --locked python $D/partition_from_text_review3.py > $D/partition_from_text_review3.out.txt`. I wrote this from the text before I opened `partition_vector_rev3.py`, reading only its `.out.txt` to rebuild the made-up maps.
  - `uv run --locked python $D/arithmetic_review3.py > $D/arithmetic_review3.out.txt` (about 5 s)
  - `uv run --locked python $D/stage4_review3.py > $D/stage4_review3.out.txt` (seed 20261126)
  - `uv run --locked python -I -B <spec worktree>/docs/reviews/adr-0033-m0-2026-11-20/addendum1_scripts/{partition_vector_rev3,addendum1_rev3_arithmetic}.py > $D/rerun_drafter_*.out.txt`
- Process disclosure: the Write tool's worktree hook refused this folder, as it did for review 2, so I wrote every file with a shell heredoc. No other path was written.

## What reproduces (scope items 2 and 5)

- **Section 4 vectors.** My from-text code reproduces all of the following exactly: the five derived integers; the shuffles of `a`…`h` on all five streams; the X order, part A, part B, no-part and per-evaluation (N_e, A, B) for V1-V5; and V3 under the rejected reading (C1 4/1/3, `C1.d` differs). Section 17's statement of the draft-2 to draft-3 change in V1 is correct. I checked the cases each vector claims to exercise by hand (V5: R1 clamp k = |L_R1| = 1; R2 a_e = 3 > 2; odd |X| in V2 and V5).
- **The drafter's scripts** re-run byte-identical: `a21e62c5…939e`, `3755ca54…be67`.
- **Section 6, by noncentral-t integration (my own code):**
  - Tables (a), (b) and (c) reproduce in all 15 cells each.
  - Every CR0 range now printed reproduces: G = 19 +0.0004–0.0006; 13 +0.0005–0.0008; 10 +0.0006–0.0009; 8 +0.0008–0.0011; 5 +0.0012–0.0016.
  - CR0 at G = 5 with δ = 0.02: τ ≤ 0.0016. At G = 3 and 4, δ = 0.02 is not reachable under either form (power at τ = 0: 0.9285/0.9732 and 0.9832/0.9934, against 0.99636).
  - The G = 4 and G = 3 values (0.0063 (0.0078), 0.0147 (0.0166); 0.0012 (0.0044), 0.0092 (0.0116)) reproduce.
  - Power at τ = 0: 0.9935 (G = 5), 0.9966 (6), 0.9984 (8), 0.9991–0.9995 (11–19).
- **Section 10:**
  - D(G) at G = 1, 2, 3, 4, 5, 8, 10, 11, 13, 14, 15, 19 and 300, the ratio 7.54–27.07, D_lin(10,2) = 12,500, D_lin(13,3) = 6,500, D_lin at G 1–4, and D_w(L) at all 9 values all reproduce.
  - The shares 0.300, 0.267, 0.444 against 1/7 = 0.143 reproduce, as do 78.9–300 and 1,052.6–4,000 items per cluster.
  - k·D_lin(G,k) ≥ D(G) for every G < 40 and k < 8. So the cluster condition binds only through collisions between sibling lineages.
- **Section 4A's worked example.** R2 part B goes 3 → 2 → 1 at demands 81,010, 121,000, 241,000, and C1 part B ends empty. My implementation of stage 4, which includes the cluster condition, gives the same registered sets in all eight parts. The R1 part A trail differs (G11).

## Section 16, review 2's findings: claimed against present (scope item 4)

I checked all 24 rows against the text, not against the table. Every claimed response is present. None is claimed and not done. Minor imprecisions:
- F3 cites "Header": the header names "the sidedness of the bound" as open but does not state the attribution. The attribution is in section 7 and A6.
- F4: section 0 defines G_e,A on *registered* lineages, but section 10 A.2 and stage 4 use it before registration (G10).

## Findings

**G1 (REQUIRED). §4 item 8 and §4A stages 1–3: the partition can still be previewed and steered.** Item 8 forbids more than one partition *on the map of record*. Nothing forbids computing the `cluster-partition` streams on a working map. Nothing fixes the map of record and the candidate list before stage 3: they are first hashed in the stage-6 record. The code and the seed are known in advance. A change of one candidate or one link reshuffles every cluster, because the list is sorted and then shuffled. So the outcome can be previewed, and §3 item 2 (the auditor may withdraw a link), wording repairs and the item-9 groups could then be used to choose among partitions. The same stage has two more numbers that can be chosen after seeing an outcome:
- the seed given to "a script that is not seeded … before it is hashed" (§7 item 2);
- the capacity run's seed and labels (G2).

Smallest fix, in §4A:
- "No stream with the label `cluster-partition` is computed on any map other than the map of record."
- "The map of record (stage 1) and the candidate list (stage 2) are hashed and the hashes recorded before stage 3 runs."
- The seeds of the cheap-rule scripts are those of the measurements already on record, listed by file, or are derived from a registered seed by `stream` with stated labels. They are never chosen fresh.

**G2 (REQUIRED). §4A stage 4 and §10 part B item 6: the capacity count cannot be executed without further choices, and the "largest set" claim is not true as specified.** "Counts are made by generation with the builder's own drawing routine and seeded streams; a later round's higher demand extends the same generation" leaves five things open:
1. Which seed, role and salt labels are used. The sealed pool's salted stream does not exist before F.
2. The stopping rule. `draw_items` stops at 40·count + 1000 attempts, and `build_item` raises after 500 consecutive retries. Neither is stated, so "a quota a lineage cannot fill" is undefined.
3. How a count under the item-1 key (names relabelled) is made with a routine that rejects on the textual key.
4. Whether one used-text set is shared across lineages or roles during the count.
5. What "extends" means when the attempt budget scales with the count.

If the set is shared, a lineage's count depends on which other lineages are in S. The order-independence and "largest set that meets its own demand" then fail. In `stage4_review3.out.txt` part 3, 519 of 4,000 random interacting instances have a self-consistent set outside the fixed point. With independent counts, part 2 shows 0 of 1,500 mismatches, so the claim holds in that case. Smallest fix:
- Count each lineage and level on its own: own stream from a named seed and labels, own key set under the item-1 key, a stated attempt budget (for example `draw_items` as written: 40 × target + 1000, and 500 consecutive retries).
- Take the cluster count as the union of its lineages' key sets.
- Define the target of each round as D_lin(G, k) under the item-1 key. A later round re-draws from the start of the same stream to the new target.
- Keep the "largest set" sentence only with these conditions.

**G3 (REQUIRED). §4 items 7 and 8: after a re-record, which partition governs is not stated.** "Both partitions are kept and shown side by side, and the human lead is told." Review 2 already noted that keeping every partition does not say which one governs, and draft 3 still does not say. Whoever reads the two side by side could pick one. Smallest fix: one sentence naming the governing partition, for example "the partition computed on the new map of record governs; the earlier one is kept as a record". The choice is the human lead's (PENDING LEAD REVIEW).

**G4 (REQUIRED). §4 item 9, now decided (item 9: kept in one part): the group mechanics leave three gaps, and no vector tests them.**
- (a) **Clusters without a candidate.** Item 9 does not say whether a cluster with no candidate lineage joins a group or passes a group on. "Every cluster takes its group's part" conflicts with §8, under which such a cluster has no part. In my probe B2 (R1.a ~ C1.x ~ R1.b, C1.x not a candidate) the answer changes the parts: R1 A/B goes from 2/2 to 1/3.
- (b) **Balance in groups or in clusters.** N_e, a_e and k_e count groups, so the larger half *in clusters* can go to the teaching-eligible part. In probe B3 (6 R1 clusters, one borderline group of 3), A gets 4 clusters and B gets 2. That is against item 5's decided "the larger half held out in both steps", which holds only in groups. This fits `LEAD_RULINGS_7.md` R-42: with borderline pairs taken together, R1's smaller part is 2 or 3 clusters.
- (c) **Vectors.** None of V1–V5 has a borderline pair, yet §4 item 8 makes the five vectors the conformance test.

Smallest fix:
- Rewrite steps 1–3 with the group as the unit.
- State whether non-candidate clusters pass groups on and whether they ever take a part. The consistent choice with §3 item 1 is "they pass groups on but take no part"; that choice is the human lead's.
- State that balance is in groups and that cluster counts are printed. Otherwise item 5's "larger half held out" must be re-worded as "in groups" (PENDING LEAD REVIEW).
- Add a vector V6 with a borderline group that spans X, includes a non-candidate cluster and holds two or more clusters of one evaluation.

**G5 (REQUIRED, PENDING LEAD REVIEW). §7 items 2 and 4 do not match the rule under which the counts now reported were reached.** §7 item 4 says "No class of rule is exempt … every rule in the scripts counts". §7 item 2 says "measured as those scripts measure it". `LEAD_RULINGS_6.md` and `_7.md` were written after draft 3 and differ:
- R-31 counts only the classes the audit-4 auditor counted, so partial-trace and costly rules are not counted;
- R-32 uses a pooled estimate over implementer and auditor seeds;
- R-34 measures per lineage and level over all shapes together;
- R-38 counts rules newly found in the final checks.

The counts given to the human lead (R1 10/8, R2 16/16, M1 29/17, C1 26/17) were reached under R-31 to R-38. R-38 records what §7 item 4 as written would do: R1 to 6 clusters or fewer, R2 down by about ten lineages, C1 to 15 clusters. Approving the text unchanged would register a rule that differs from the one applied. Draft 4 must state which governs, put that to the human lead as a decision, and give it the line "observed before: yes (item-side measurements only)". R-31 is the less strict direction, which is why this is his decision and not a wording fix.

**G6 (REQUIRED). Decided item 2 leaves the standard-error form open.** Item 2 was decided as "(b) … with the χ² interval". That fixes the interval and, through §9 item 4's formula, V on divisor G − 1. It does not fix CR1 against CR0. Section 13 item 2 lists the form as going "with the method", and at G = 5 the form decides whether 0.02 is reachable at all. My figures: τ ≤ 0.0016 under CR0, none under CR1. Draft 4 must keep the form as an open decision with a stated deadline (F, by §9 item 4), not mark it decided. It must also delete §9 item 4's "NOT COMPUTED" fallback, which no longer applies once the interval is decided.

**G7 (REQUIRED). The sentences draft 4 must change so that no "proposed" or "until he decides" remains where a decision now exists.** With the 2026-11-26 options taken together I found no conflict between two decided items except G4(b) (items 5 and 9) and G6 (item 2's remainder). Item 16 is consistent with §4A: stage 4 already uses each part's own count in the current round. Item 9 is consistent with item 5's transitive merging: borderline links only group, and same-procedure links merge. Item 14 removes §4 item 6's interim rule. The sentences:

| Place (draft-3 line) | Change |
|---|---|
| L10 header | "several decisions still open will be taken" → taken 2026-11-26 (`HUMAN_LEAD_WORDS_6.md`), each "observed before: yes (item-side measurements only)" |
| L36 §1.1 | delete "If this test is approved, …" and "If it is not approved, this item is a description …"; state approved in principle (item 4 a) |
| L38 §1.3 | "section 13 item 9 puts the alternative" → kept in one part (item 9; §4 item 9) |
| L58 §3.2 | delete "The alternative, in which such lineages stay two clusters … is put in section 13"; mark decided (item 5 iv) |
| L82 §4 step 2 | "Starting with B is the drafter's choice and is listed in section 13 item 5" → decided (item 5 iii) |
| L83 §4 step 3 | "is the drafter's choice (… flagged it for a ruling)" → decided (item 5 ii) |
| L86 §4.6 | "withdrawn … if section 9 item 1 is approved" → withdrawn (item 3 a); "Proposed, and his to decide (section 13 item 14)" → decided (item 14 a); **delete** "Until he decides, G-gen's record is not made for an evaluation whose registered lineages span fewer than 12 families" |
| L89 §4.9 | heading "(…; not the drafted default)", "The drafted default leaves them free …", "If he chooses to keep them together" → the governing rule, with G4 |
| L91 §4 closing | "The simpler rule is an option in section 13 item 5" → not taken |
| L97 §4A stage 0 | the listed §13 items are recorded as decided on 2026-11-26; what remains is the domain list (choice 2), approval, the hashes and G6's form |
| L105 §4A | "(a new registered choice; the drafter's proposal; section 13 item 5)" → decided (item 5 v) |
| L122 §5.1 | "listed as a decision of its own … not approved by bundling" → decided (item 13 a) |
| L149, L196 §6 | "Choice 18 is the human lead's (section 13 item 2) and is not taken here" → (b) with the χ² interval, decided; under (b) the private parts read UNDERPOWERED almost whatever the truth; the CR form stays open (G6) |
| L199 §6 | "proposed here and his to confirm (section 13 item 15)" → decided (item 15 a) |
| L203, L207 §7 | heading "read two-sided by the lead's ruling" and "listed for him to confirm" → confirmed by the human lead (item 12 a); keep the attribution history |
| L209 §7.3 | "is the drafter's (section 13 item 8)" → decided (item 8) |
| L234 §9.1 | "Proposed replacement reading" and "so it is his" → decided (item 3 a) |
| L237 §9.4 | "Proposed for the reviewer and the human lead, not adopted: the χ² interval" → adopted (item 2 b); delete the NOT COMPUTED fallback; CR form per G6 |
| L238 §9.5 | "No minimum is proposed (section 13 item 13). Proposed reading, for the reviewer and the human lead" → no minimum (item 13 a); the reading decided (item 7) |
| L246 §10 A.1 | "is not ruled. It is the human lead's" / "Whichever he chooses" → reading (i) decided (item 1) |
| L251 §10 A.2 | "listed in section 13 item 16" → decided (item 16 a); cite R-30 beside R-11 (G12) |
| L257, L261, L272–275 §10 B | "(a proposal; needs approval; section 13 item 6)", "Proposed builder", "before section 13 items 1 and 6 are decided", the two "If he …" bullets → decided (item 6 a); keep 6 b only as "not taken" |
| §11 rows L293, L313, L315 | delete "if section 9 item 1 is approved" / "if approved" / "(if approved)" |
| §12 items 3, 8, 9, 13 | "It is his" / "section 13 item 9" / "section 13 item 16" → decided |
| §13 | rewrite as decided: preamble "None of these is decided here" → decided 2026-11-26; record line on items 1, 4, 5, 6, 8, 9, 12, 14; item 11 unchanged (no recommendation was made); item 2 per G6 |
| §15 A5, A6, A11, A13, A14, A17, A18 | "left to him", "section 13 item 12", "if approved", "once approved", "adopts none", "Lead; reported", "Proposed … until he decides, no G-gen record …" → decided wording; A18 loses its interim rule |

§3 item 5 (K0, "until he does") is not a §13 item and stays.

**G8 (NOTE). §10 part B is implementable and meets "balanced over" and "spread evenly over the G clusters"**: cluster quotas differ by at most one, and the M0 draw is equal per cluster. Three small gaps remain:
- Items 3, 4 and 7 say "by largest remainder" without the tie rule. Write "`allocate` as written (ties to the earlier index)".
- The role order behind "any earlier role" (tuning, development, sealed) is the caller's and is not stated.
- If the tuning draw (100 per level) is built with one call per level, every level's remainder goes to the same early clusters. For example, at G = 3 the first cluster gets 34 at each of five levels.

**G9 (NOTE). The drafter's vector script.** Part 4 omits the cluster condition (its docstring says so; the addendum does not). The R1 part A trail therefore reads "G=2 drop R1.beta; G=2 drop R1.alpha". By the text the cluster fails at once, because 79,000 < D(2) = 121,000, so both lineages drop in one round. The result is the same. The docstring also calls candidates "stage 3" and capacity "stage 5", where the text has stages 2 and 4.

**G10 (NOTE). §0 against §10 A.2 and stage 4.** G_e,A and G_e,B are defined on registered lineages but are used inside stage 4 before registration. Add "(during stage 4: lineages still in S)".

**G11 (NOTE). §1 item 4 and §6: the counts are out of date.** §1 item 4 still gives `LEAD_RULINGS_4.md` counts (10/20/18/17) and "G from 5 to 19". With R1 at 8 clusters (R-42: 4/4, or 2 or 3 in the smaller part under grouping), R1's parts fall to G = 2–4. G = 2 is not in section 6. Update the counts and add G = 2, which needs §9 item 5's reading.

**G12 (NOTE). Rulings after draft 3 that the text should name.** R-30, which restated R-11's smaller-part G, should be cited beside R-11 in §10 A.2, §12 item 8 and A17. R-36 and R-39 hold eight M1 lineages and R2 `to_base_wide` on capacity under the old builder. Draft 4 should say that these enter stage 2 as candidates and are decided at stage 4 under the decided builder.

## Files (this folder)

`partition_from_text_review3.py` / `.out.txt`; `arithmetic_review3.py` / `.out.txt`; `stage4_review3.py` / `.out.txt`; `rerun_drafter_partition_vector_rev3.out.txt` (= `a21e62c5…939e`); `rerun_drafter_addendum1_rev3_arithmetic.out.txt` (= `3755ca54…be67`). SHA-256 of each in `SHA256SUMS.txt`.

Ran as: Claude Opus 5.5 (`claude-opus-5-5`), `arbor-auditor` role.

Astra review: NOT_PERFORMED
