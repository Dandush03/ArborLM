# Check 5 of ADR-0033 addendum 1, draft 5 (narrow scope: what draft 5 changed)

**Verdict: APPROVABLE AFTER REQUIRED CHANGES.** 0 blocking, 8 required (J1–J8), 5 notes (J9–J13).

- Ran as: `arbor-auditor` role, Claude Opus 5.5 (`claude-opus-5-5`), 2026-11-26. I wrote none of the addendum, ADR-0033, the earlier reviews or checks, or the implementation. This is independent engineering and mathematical evidence. It is **not** Astra validation and **not** human approval. Scientific questions are marked PENDING LEAD REVIEW. No model was run, nothing was downloaded, no sealed value was read, no run output was read, no rate, pooled figure or lineage status was computed, and no git state was changed.
- Reviewed: `docs/decisions/ADR-0033-addendum-1-lineage-clusters.md` at `56a018dd` (`claude/m0-spec`). SHA-256 `a2682091da40c7243f8c2e97f5ab6fd3951daa8a2adb77c3bd300e29cc2a8eff`, the same in the working tree and in `git show 56a018dd:`. I read the diff against `471a1edb` and check 4 (`addendum1_review4/REVIEW.md`).
- Human lead's records, read-only, in worktree `agent-a0c9d741ea96ce52f` (HEAD `8818af01`): `HUMAN_LEAD_WORDS_6.md` `a8e5c276…6984` and `HUMAN_LEAD_WORDS_7.md` `152e9b8c…40b6`. Both match the hashes the addendum cites.
- Record of runs read through `git show`, `git ls-tree`, `git log` and `git diff` only, at `b78e58b1` and `7cd0ac5a`. I read script headers, `NOTES_FIX4_M1.md` sections 1–8, the run and command lines of `FINAL_M1.md`, `AUDIT_M0_M1_1.md` and `AUDIT4_M1.md`, the header of `pool_a5.py`, the header of `final_c1/f4b_pool_v2.py`, and the R-38 lines of `LEAD_RULINGS_7.md`. **Disclosure:** some of those lines carry per-lineage figures, and I saw them. I did not use them, did not compute any status, and do not report which lineages would change.
- The drafter's new script reproduces its cited hashes: `addendum1_rev5_arithmetic.py` `0c6fae6c…7273`, output `b0a1637b…ad37`. I did not re-run it. Part A agrees with check 4, and part B is reproduced independently below.
- Environment: macOS 27.2.1 arm64, uv 0.12.15, CPython 3.12.14, the locked environment of worktree `agent-a0c9d741ea96ce52f`, standard library only. Commands were run from that worktree, with `D` = this folder:
  - `uv run --locked python -I -B $D/seed_check5.py > $D/seed_check5.out.txt`
  - `uv run --locked python -I -B $D/membership_m1_check5.py /Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f > $D/membership_m1_check5.out.txt` (read-only `git` subprocesses only)
- Process: the Write tool refused this path because it is outside this session's worktree. Every file here was written with a shell heredoc. No other path was written. Both scripts ran first time; there are no failed attempts.

## Scope 1. H1–H4 of check 4

| Item | Status | Sentence |
|---|---|---|
| H1 | **partly fixed** | Draft 5 adds a written rule: §4A stage 0 points 1–10, "Now nobody chooses. The rule below is applied to git history by an auditor, and the manifest is its output." Applied to M1 (scope 2), it still needs judgement in at least nine places. Two of them, the definition of the further pooling script and the class of a rule, can be exercised with the figures in view (J1–J4). |
| H2 | **fixed** | §4A point 7: "the script's **base name**, that is its file name with its extension and without any directory … The integer enters the script by a one-line change that seeds its random generator with that literal integer. The change is made in a copy beside the original". Small residue in J10. |
| H3 | **fixed** | §4 item 7: "No re-record may change it"; "Rules (ii) to (v) are withdrawn"; A20 names rule (v) as having "suspended decided item 9"; the old claim is replaced by "What can still happen after a split has been seen: a lineage can be removed for a failed condition." Two new inconsistencies are in J5 and J7. |
| H4 | **fixed** | §4 item 9: "Draft 4 said here that draft 3's item 9 'did not say' how a group of several clusters is placed. That was wrong. … Two decided items were in conflict; it was not a gap." §13 items 9 and 20 and A24 agree. |

## Scope 2. The membership rule, applied mechanically to one evaluation: M1

`membership_m1_check5.out.txt` lists every `.py` file of the M1 record at `b78e58b1`: 70 files. For each it gives whether the file draws items and names rules, the seeds written in its text, the commit that added it, which named and unnamed record files mention it, the files matched by the name patterns of point 5, and a static check for point 4(b).

**Result for M1. The rule puts these in and these out without a judgement:**
- **In** (point 1 record, final version):
  - `studies/m0/m1_fix4_battery.py --n 2000` (own 410302, a4 17, a3 5), recorded in `NOTES_FIX4_M1.md`;
  - `final_m1/rules_a5.py fresh 4000 2611252`;
  - `final_m1/rules_a5.py repro 2000`, which is the same functions on the same streams as the battery, so it is counted once (point 4).
- **In** (earlier round, items unchanged, recorded under `docs/reviews/…`):
  - `audit4_m1/shortcuts_a4.py 2000` (seed 17) on every `_r3` id that fix 4 did not revise, deduplicated against the battery's a4 part where the streams are the same;
  - `audit3_m1/shortcuts_a3.py` (seed 5, N = 1,000) and `audit_m1/shortcuts_audit.py 1000` (seed 777003), for **`M1.tiered_pricing`**, the one final id carried unchanged since batch 1.
  - My static check (part 4 of the output) found that none of the M1 generator files present at `1b33b7b2`, `9e32b317`, `163fa419` or `a325156e`, nor `core.py`, changed by `7cd0ac5a`. Point 4(b) asks for byte identity of items, which needs execution at two trees; I did not execute anything.
- **Out by name:** `audit3_m1/shortcuts_a3_attempt1.py`, `audit4_m1/shortcuts_a4_attempt1.py`, `final_m1/rules_a5_attempt1.py` with `rules_repro_n2000_attempt1.json`.
- **Irrelevant either way to a final id:** runs on `_r2` ids, on batch-1 ids other than `tiered_pricing`, and on the five `_r3` ids that fix 4 replaced by `_r4`. Under §0's id they are runs "for" lineages that are not candidates. Also irrelevant: `digit_puzzle_extra_a3.py` (digit_puzzle only) and `m1_fix3_failing_first.py` (pre-fix shapes).

**Places where I had to make a judgement (M1):**
1. **Which files count as a record (point 1).** The M1 implementer's batch-1 and rev2 screens are recorded only in `studies/m0/manifests/m1_batch1_manifest.json` (`"shortcut_seed": 953703`) and `m1_batch1_rev2_manifest.json` (`"shortcut": 777103`), plus a usage template and a `SEED` constant in their own text:
   - `m1_shortcut_check.py`, seed 953703, run through `m1_batch1_gates.py`;
   - `m1_shortcut_check_rev2.py`, seed 777103, `--set rev2|batch1`.

   Neither manifest is a file point 1 names. Whether a docstring usage line plus a `SEED` constant "records a run" is not said. The same holds for `m1_fix3_shortcuts.py`'s run, recorded in `NOTES_FIX3_M1.md`, which point 1 does not name either; in M1 it is a duplicate of the battery's own part. The batch-1 and rev2 runs bear on `M1.tiered_pricing`.
2. **What a rule script is (point 3, "scores rules against generated items for the bound").**
   - Taken literally, "for the bound" excludes every script written before the bound of 2026-11-25 21:45 (`9bcec484`). That includes `shortcuts_a3.py`, `shortcuts_a4.py` and `s4_rules_v2.py`, which the drafter's own list includes. So the phrase cannot be meant literally, and what it does mean is not said.
   - Borderline M1 scripts:
     - `audit4_m1/subclass_a4.py`: seed 29, N = 4,000, subclass sizes of "the new tells"; recorded in `AUDIT4_M1.md`.
     - `audit_m1/overshoot_audit.py`: real generator against a counterfactual, `stream(777007, "overshoot", …)` and hard-coded `Random(1000 + lv)` and similar.
     - `m1_rev2_gates.py` (seed 777105, on check 4's list) and `m1_batch1_gates.py`.
     - the summarisers: `shortcuts_summarise.py`, whose v1 the record says mis-tagged three rules.
   - My text proxy flags 35 of the 70 M1 files.
3. **Item identity for 4(b).** The test needs execution at both trees. It does not state the `PYTHONHASHSEED` (records use 0 and 1), or whether the comparison is per level or per run. For runs whose code was never committed, the "commit that first records the run" already holds the later code, so the test passes trivially (J2).
4. **The "that is" clause of 4(b)** against the pre-repair class (J2). M1 is not affected; R2 `crt_smallest` is the case the text itself names.
5. **Re-execution "at the tree of `7cd0ac5a`" (point 6).** `final_m1/*.py` does not exist at that tree, and every recorded command uses scratch paths (`$S/…`). I read the point as "generators of `7cd0ac5a`, scripts as at `b78e58b1`" (J9).
6. **Deduplication (point 4).** Whether the battery's a3 part at seed 5 (N = 2,000) uses the same stream labels as audit 3's seed-5 run (N = 1,000), so that the shorter run is a prefix. This can be settled by reading code; I did not verify it.
7. **The class of a rule (§7 item 4).**
   - `pool_a5.py` (M1) does not print two readings. It applies one: audit 4's `PROC`, "and the audit-3 rule of the same name and definition for the same lineage (an extension by name, flagged)". The text's sentence covers only a script that prints "an auditor's reading and an implementer's side by side", so whether the extension is "the auditor's class" is a judgement.
   - The rules of `shortcuts_audit.py` and `m1_shortcut_check(_rev2).py` that run on `tiered_pricing` were never classed by a fourth-audit or final auditor (J4).
8. **The base of an excess (§7 item 2, point 8).** `shortcuts_audit.py` prints an in-sample and a held-out most-frequent-answer rate. `m1_shortcut_check.py` uses the in-sample constant. `pool_a5.py` pools each source's stored (rate − base). The further script must choose (J3).
9. **Matching rules across files.**
   - Point 4 deduplicates "the same function, in the same file or copied unchanged".
   - `pool_a5.py` pools by "the SAME rule definition" and also pools `echo_best_position` across three files as "(same algorithm)".
   - For rules of earlier scripts, the further script must decide what counts as one rule (J3).

**So the rule does not yet determine membership from git history alone for M1.** Points 1 and 3 and the further pooling script leave choices. The rule's core (the record at `b78e58b1`, the generator at `7cd0ac5a`, exclusions by class, "a seed's name excludes nothing", re-execution) is mechanical.

**The drafter's seven calls:**

| Call | Stated in the text as a rule? | Stricter or more favourable for passing? | Exercisable after seeing results? |
|---|---|---|---|
| (a) earlier-round runs in where items are byte-identical | Yes, point 4(b), but with the "that is" clause that contradicts the pre-repair class (J2) | Neither by construction. It adds runs whatever they show, so no selection, but its effect on a pooled figure can go either way. "Strictest" in §12 item 19 means "no selection", not "lowers passes" | Barely. The test is mechanical given execution, apart from J2 and point 3 |
| (b) superseded scripts excluded, five named | Yes, by class with reason, by name, and with a completion procedure | Favourable or neutral for the named M1 and C1 cases (each removed figure came from rules scored where they are the procedure or the program). Each defect was recorded by its own author before draft 4 | Little. Completion is by named patterns and by headers already in the record. "For a recorded scoring defect" is still a judgement (for example the summariser v1) |
| (c) throwaway seeds exclude nothing | Yes, point 5 last bullet and point 4 | Neutral to strict (no exclusion) | No |
| (d) outputs of record are re-executions at `7cd0ac5a` | Yes, point 6; "the re-execution still stands" | Neutral | Only through environment and path details (J9) |
| (e) one further pooling script, written and hashed before use | Stated as an obligation, **not as a rule**. Its content is not fixed | Undetermined | **Yes.** Its author has the record's per-run figures available, so hashing before running it on member runs does not make it blind (J3) |
| (f) the script list is the drafter's reading | Yes, "the rule governs, not this list" | Including more scripts generally adds counted rules (stricter); judging a script not to be a rule script is favourable | **Yes**, through the predicate of point 3 (J1) |
| (g) the rule class is the final auditor's class | Stated in §7 item 4 and §12 item 19, but in conflict with §7 item 4's opening ("the classes the fourth-audit auditor … counted", R-31) | Depends on the evaluation. C1's auditor reading (STRICT) is stricter than the implementer's. M1's final-auditor extension by name to audit-3 rules can only remove counted rules, so it is favourable | **Yes.** The drafter chose it after seeing reports that carry figures (point 10 discloses this). Unclassed rules have no stated default (J4) |

## Scope 3. Re-record and the drafter's additions

- **Consistent:**
  - §4 item 7 and §4A stage 1 now agree: the map is frozen at its hash and a later record differs only by removals.
  - The candidate list closed at the stage-2 hash agrees with stage 2.
  - "Stage 4 continues and is not started again" agrees with the fixed point: removals only, nothing brought back, a monotone G.
  - The case "defect in hashed code" is listed and not ruled on (§12 item 22), and the top list carries it.
  - The three cases check 4 found uncovered cannot arise.
- **New inconsistency (J5).** §3 item 6 says the map file lists "the registration status of each lineage" and is "frozen at F by hash". §8 says a NOT REGISTERED lineage "is marked … with its reason in the map of record". Statuses are known only after stages 2–5 and change at a re-record. The stage-1 hash would then cover a file that must change, and there are two freeze points, stage 1 and F.
- **Still choosable after the split is seen (J7).**
  - A re-record may remove a lineage when "an engineering stop … shows that a registered lineage fails a condition", including "a counted rule of the hashed scripts beyond the bound" (§7 item 10). The manifest is closed, so such a finding needs a new run. Nothing fixes which lineages or seeds are re-checked after the record.
  - A check run on one part only, after the split is visible, could therefore remove lineages from that part. This moves no cluster, but it shapes which procedures are held out.
  - What the human lead decides on a recorded departure is left open by design (§12 item 22). That is disclosed.

## Scope 4. Section 13 against the human lead's records

- Items 1–16: each option shown agrees with the `HUMAN_LEAD_WORDS_6.md` table. Item 5 is reworded as "the aim being that the held-out part has the larger half in both steps (it usually does, and not always)", where the table says "the larger half held out in both steps". `HUMAN_LEAD_WORDS_7.md` requires exactly this correction ("the text must not claim the held-out part is always the larger"), and item 5 points to item 20. Consistent (J13 is a wording note).
- Items 17–21: each agrees with the `HUMAN_LEAD_WORDS_7.md` table. Item 18 adds "including those the final auditors found" (R-38) and the report of differences, both in the lead's reading of the seventh decision.
- `grep always`: every occurrence is "not always" or "usually … not always" (lines 11, 99, 112, 435, 443, 463, 484, 506, 614). There is **no "always" claim** about the larger half.
- Weakening sentences beyond the decided items: none new in the rule text itself. The class reading of §7 item 4 can act as one for M1 (J4); it is carried as the drafter's reading in §12 item 19 but is not marked as a possible weakening.

## Scope 5. H2 seed derivation

The text is unambiguous for the integer. From the text alone (`seed_check5.out.txt`):
- **`m1_fix3_shortcuts.py` → `'400002|cheap-rule|m1_fix3_shortcuts.py'` → 3326396545411272323.** That script is in fact seeded (410302), so point 7 would not apply to it; it is used only as a named example.
- My code reproduces the drafter's part B exactly: 1035349750409085599 for the base name `example_rules.py`, 15176297000423028348 for the path.
- Without the extension the integer would be 3494842782195840892. The text excludes that reading ("with its extension").
- No collision with the `development` label on 400002.
- What is left is small (J10).

## Scope 6. "What still needs the human lead"

- **Incomplete (J8).** Item 1 enumerates what approval carries without his item-by-item decision. That list omits rows that §15 marks "Lead after review", "approved with this text" or the drafter's:
  - A9 (the teaching ban extended to unregistered lineages);
  - A10 (the partition at G-gen's record);
  - A16 (the t rule in the confirmation step);
  - A23 (the drafter's reading of the union condition);
  - A21's derivation for unseeded scripts;
  - the §7 item 4 class reading;
  - the obligation to write a further pooling script.
- **Missing default (J6).** Item 2 and stage 0 point 9 send every R-38 difference to him "before G-gen's record" and hash the manifest "after he has answered". Neither says what governs if he does not rule otherwise. His answer is then an unbounded choice made with the statuses in view.
- **Wording (J8).** "Nothing in section 13 is left for him to choose" contradicts item 10 (approval open) and item 11 (domain list and others, nothing decided).

## Findings

**J1 (REQUIRED; before approval, or a condition carrying the exact wording). §4A stage 0 points 1 and 3: which files record a run, and what a rule script is, are not mechanical.**
- Defect:
  - point 1 names `NOTES_FIX4_*`, reports or logs under `docs/reviews/m0-lineage-decision-2026-11-25/`, and "a script's own text". Earlier runs recorded only in `NOTES_FIX1–3_*`, in `studies/m0/manifests/*.json` or in a usage template are left to judgement (M1: seeds 953703, 777103, 410302);
  - "scores rules against generated items for the bound" cannot be read literally, since audits 3 and 4 precede the bound, and has no stated alternative;
  - so "Now nobody chooses" overstates the rule.
- Smallest fix:
  - record: "any file of the tree of `b78e58b1` that gives the run's script, seed or seed labels and number of items; a `SEED` constant or usage template alone is not a record";
  - rule script: "any script that computes, on items generated by an M0 builder, how often a named rule's answer equals the key";
  - the known borderline kinds (subclass sizes, counterfactual or overshoot, gate wrappers, summarisers) listed with a stated default, in or out;
  - reword "nobody chooses" to "what is left to judgement is in section 12 item 19".

**J2 (REQUIRED; can be a condition). §4A stage 0 point 4(b) against point 5 "Pre-repair runs".** "It belongs to the narrow round or the final checks, that is, it is recorded in a `NOTES_FIX4_*.md` file" admits every run recorded in a fix-4 note. That includes the first `crt_smallest` battery, made on an uncommitted first version and recorded in `NOTES_FIX4_R2.md` §9, which point 5 names as excluded "as a run that fails 4(b)". The byte-identity test against "the commit that first records the run" also passes trivially for code never committed. Smallest fix: drop the "that is" clause and apply the byte-identity test to every run, comparing the items the recorded run drew with the items drawn at `7cd0ac5a`. Keep the named `crt_smallest` exclusion, and add "a run on code that was never committed is pre-repair if the record says so".

**J3 (REQUIRED, PENDING LEAD REVIEW; before approval, or a condition carrying exact default text). §4A stage 0 point 8: the further pooling script has an obligation but no definition.**
- Not fixed:
  - the base per run (in-sample against held-out most-frequent answer);
  - which rules from different files are "the same rule" (`pool_a5.py` pools `echo_best_position` across three files as "same algorithm");
  - how items on which a rule raised are counted;
  - how runs on different item sets per level are weighted.
- Its author can see the record's per-run figures, so hashing before running it does not make it blind.
- Smallest fix: write the definition in §7 item 2. For example: "for rule r, lineage x, level v: Σ n_i (rate_i − base_i) / Σ n_i over member runs i that score r on x at v; base_i is run i's held-out most-frequent-answer rate where printed, else its own base; one rule = one function in one file or a copy unchanged; an item on which r raised counts as a miss." The script must implement exactly that.

**J4 (REQUIRED, PENDING LEAD REVIEW; can be a condition). §7 item 4 and §12 item 19: the class of a rule.**
- The opening counts "the classes the fourth-audit auditor … counted (R-31)"; the closing and §12 item 19 make "the final auditor's class" of record "where a pooling script prints two readings".
- M1's `pool_a5.py` prints one reading that extends audit 4's `PROC` by name to audit-3 rules. That extension can only remove counted rules, so it is the favourable direction.
- Rules from earlier-round member scripts (M1: `shortcuts_audit.py` and `m1_shortcut_check(_rev2).py` on `tiered_pricing`) were classed by nobody.
- Smallest fix:
  - "a rule is counted unless the fourth-audit auditor of its evaluation classed it otherwise; a final auditor's further class, including an extension by name, applies only where the text names it";
  - mark the M1 extension and C1's STRICT reading with their directions;
  - state that an unclassed rule counts.

**J5 (REQUIRED; can be a condition). §3 item 6 and §8 against §4A stage 1 and §4 item 7.** The map file carries registration statuses and NOT REGISTERED reasons, which are set at stages 2–5 and at re-records. Yet the map is "frozen at its hash" at stage 1 and also "frozen at F by hash". Smallest fix: "statuses and reasons are recorded in a separate file keyed by lineage id; the stage-1 hash covers the map's lineages, clusters, links and borderline pairs; F re-hashes that same content".

**J6 (REQUIRED, PENDING LEAD REVIEW; can be a condition). §4A stage 0 point 9, top list item 2: no default when a status differs from R-38.** Smallest fix: "the status under the manifest governs; any other answer is a recorded departure, with the lineage, the two statuses and his reason".

**J7 (REQUIRED, PENDING LEAD REVIEW; can be a condition). §4 item 7 and §7 item 10: which checks may remove a lineage after the record.** Nothing fixes which lineages, seeds or scripts are re-checked after the split is visible, so a check aimed at one part could remove lineages selectively. Smallest fix: "after the record only the checks this text fixes are run, each on every registered lineage (the solver agreement on every pool item at the freeze; the hashed scripts on the manifest's runs); any other finding is a recorded departure to the human lead, like a map found wrong".

**J8 (REQUIRED; can be a condition). The top list, item 1, and §13 item 10.**
- The enumeration of what approval carries omits A9, A10, A16, A23, A21's derivation, the §7 item 4 class reading and the further pooling script.
- "Nothing in section 13 is left for him to choose" contradicts items 10 and 11.
- Smallest fix: "… and every row of section 15 whose 'Whose call' names the lead or the drafter, and the readings listed in section 12 item 19"; and "nothing among items 1–9 and 12–21".

**J9 (NOTE). Point 6.**
- The scripts of `final_*` are not in the tree of `7cd0ac5a`.
- Recorded commands use scratch paths and inputs, and some record `PYTHONHASHSEED` 1.
- Fix: "generators as at `7cd0ac5a`, scripts as at `b78e58b1`, with the recorded environment variables; any path substitution is listed".

**J10 (NOTE). Point 7 residue.**
- The text does not say which command line and N to use when several unseeded runs of one script are recorded.
- Nor does it say where the one-line change goes when a script uses several generators or the module-level `random`.
- The integer itself is unambiguous (scope 5).

**J11 (NOTE). §12 item 7 seed list.**
- M1 rule-like scripts also use 29 (`subclass_a4.py`), 777003, 777007 and hard-coded `Random(1000 + lv)` and similar (`overshoot_audit.py`), 2611252, 953703 and 777103, if those scripts are members.
- The list is quoted as unverified, so it goes to the seed-registry auditor with the manifest.

**J12 (NOTE). Point 5.** `short_trial_n200.json` is named as an excluded output but is not in the tree of `b78e58b1` (scratch only, per `AUDIT3_M1.md` and `AUDIT4_M1.md`). Say "(scratch; not in the record)".

**J13 (NOTE). §13 item 5.** Quote the sixth decision's words ("the larger half held out in both steps") beside the corrected "aim" wording, so that the human lead sees the change made under his seventh decision.

Whether J1–J8 are fixed before approval or written into it is the human lead's choice. J1 and J3 change what the rule determines, so if they are conditions, the approval should carry the exact replacement wording.

## Files

- `seed_check5.py` / `seed_check5.out.txt`
- `membership_m1_check5.py` / `membership_m1_check5.out.txt`
- Hashes in `SHA256SUMS.txt`.

Astra review: NOT_PERFORMED
