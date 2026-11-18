# Fourth review of ADR-0028 (P10-I-S5), DRAFT 4, engineering part

- Reviewer: `arbor-auditor` subagent, model Claude Opus 5.5 (`claude-opus-5-5`, as the session reports it). I wrote none of ADR-0028's revisions. I did write REVIEW3, which draft 4 answers; so section 1 below is me judging fixes to my own findings. Read it with that in mind.
- Date: 2026-11-18, about 04:00 to 04:30 UTC. Draft: worktree `agent-a9976922e8c647b3b`, branch `claude/p10-i-s5`, commit `2d92c27`, `docs/decisions/ADR-0028-p10-i-s5-physical-ssd-memory.md` (459 lines). Diff from `ef5596b`: 2 files, +571 / −140 lines. I read that tree only; I wrote nothing to it.
- Environment: macOS 27.2.1, Mac17,6, 18 cores, 51,539,607,552 B RAM. Stdlib scripts ran under `/opt/homebrew/bin/python3 -I -B`. The torch timing ran under the draft worktree's `.venv` (CPython 3.12.14, torch 2.8.0, one thread). The machine was **not quiet**: no study was running, but 1-minute load was 1.95 to 3.54. No store and no probe file were written. The only writes are this file and the scripts and outputs beside it.
- `Astra review: NOT_PERFORMED`. This is not Astra review and not human approval.

## Verdict

**READY AFTER THE LISTED EDITS** (edits X-1 to X-12 in section 6). Without them it is NOT READY, for four reasons:

1. **The plan builder is infeasible as written.** It exhausts by repeat 2 or 3 (section 3).
2. **K is circular with `plan.json`, and the rehearsal geometry contradicts it** (section 5).
3. **EQ-C is close to insensitive by construction.** Routing costs about 3 times the I/O (section 3).
4. **The quiet check cannot pass** at the end of a block, and probably not at idle either (section 5).

Each edit is spelled out. Edits X-3 and X-4 change the content of a registered question or design ceiling before any observation. Mark them `PENDING LEAD REVIEW`: they need the lead's acceptance, not only a clerk's application.

## 2. Is "decided by construction" right? (answered first)

**Within the arms draft 4 defines, yes, and I confirm each step.**

- **Same pages.** `studies/p9/model.py` `_top_tree` (lines 371–394) scores every router row, takes `stable_top(routes, VISIT=2)` and adds `log_softmax` of the routes over all branches as the prior. `studies/p10s1/index.py` scores every centroid and visits lists in descending score until 512 candidates. With fixed 256-row lists that is exactly 2 lists. In draft 4, IVF's centroid table **is** the routing table (§4.3). So S-TREE and IVF-2 read the same two key pages.
- **Recall.** For a fixed candidate set C, the top 8 of C by cosine contain all of E∩C, where E is the exact top 8. Every E member outranks every non-E member, and ties go to the lower id on both sides. So IVF-2's recall is the maximum any reranking of C can reach, and S-TREE's recall can only be equal or lower.
- **KEYS rung.** Collapses to X-RES. **S-FLAT** loses on bytes.

**But the equality is partly the draft's own definition.** Its "IVF" is the tree minus the prior: centroids are the branch means and lists are the generator's branches. It is not a k-means IVF with nearest-centroid assignment. So the claim says less than "trees cannot beat IVF".

The honest regimes where a tree-shaped layout and an IVF layout read different pages at equal recall:

- **(a) Data-dependent partitions.** Fixed-capacity leaves against nearest-centroid lists of unequal size. Pages per query vary with list size, and so does tail latency. This is real for ArborLM: T-OQ has fixed 256-slot leaves, and P10-S1's F-OQ-IVF has k-means lists with a recorded p99 of candidates. But pages per query are computable in RAM from P10-S1's own trained keys and index, with no device. It belongs in a **RAM-only analysis or the redesign, not in this study**. Draft 4 is right not to invent it on synthetic data.
- **(b) A multi-level router with only its upper levels resident.** This is honest only when routing data approach RAM. Here R = 22.4 MB against 48 GiB, so the regime does not exist at 16 GiB. It would need on the order of 10^11 rows. It belongs in the **redesign**. Even then, SPANN-style systems put a tree over the IVF centroids, so "tree versus IVF" becomes a choice inside one design.
- **(c) A budget that fits the tree's routing data but not the IVF's centroids.** This is the same array here (N/256 rows of 64 B each), so the regime does not exist.
- **(d) Values read only for the selected slots.** Both arms already do this, through the separate value region.
- **(e) Hot-page reuse under a skewed workload.** A balanced tree concentrates repeated reads on few pages, which a cache would serve. It is excluded by the cold regime (§1). It is honest and relevant to "without losing speed", and it belongs in the **redesign**.

One small correction to §5.2. "Their time differs only by a few arithmetic operations": my timing has S-TREE's routing at about 1,144 µs median against IVF-2's 893 µs. The `log_softmax` over B = 349,525 routes is O(B), about 28 % more routing time. That is "one extra pass over B route scores", not "a few operations". It remains BY CONSTRUCTION and is not a device question.

**What this benchmark will tell the human lead toward "enhance memory with SSD without losing speed nor accuracy":**

- What one uncached 16 KiB page costs on his drive at queue depth (QD) 1, and the full distribution. The third review saw about 72 to 121 µs, about one whole T-OQ query in RAM (99 µs).
- Whether a 3-page branch read is cheaper per page than three 1-page reads (EQ-B). That is a layout fact, and it is near-certain physics: per-command latency dominates transfer.
- That bytes are predictable exactly from the layout (EQ-A), which licenses doing future layout work by arithmetic in RAM.

**What it will not tell him:**

- Anything about accuracy, the trained tree, learned placement, or "tree of weights" search. Accuracy is a validity condition on invented data.
- Parallel I/O at QD above 1. That is the main lever real SSD indexes use to "not lose speed": 2 key pages plus 2 value pages issued together cost about one page's latency, not four. `os.pread` releases the GIL, so a threaded QD sweep is possible inside the lock with no install.
- Warm or hot-page caching.

**Is it worth 19.5 GB and 4 to 6.5 hours?** Partly.

- EQ-A on the 16 GiB store adds little to R1's exactness check.
- EQ-C as drafted is dominated by CPU routing (section 3, finding N3).
- EQ-B needs about 196,000 disjoint pages (3.2 GB).

A smaller study would tell him more. Candidate: R0 and R1, plus EQ-A and EQ-B, plus a QD sweep (1, 2, 4, 8, 16 threads × request sizes) on one roughly 4 GiB file. That is about 5 GB written and about 2 to 3 hours. The QD × size cost table would let the redesign predict latency for any layout by arithmetic. This is a scope choice: `PENDING LEAD REVIEW`. If the full study is kept, X-1 to X-12 make it implementable.

## 1. Disposition of REVIEW3 findings and edits

| Item | Disposition | Note |
|---|---|---|
| F1 exact counter | FIXED (§7) | The EQ-A label wording overclaims; NEW PROBLEM N5, edit X-5 |
| F2 uncached build and reads | FIXED (§7 discipline) | When page hashes are computed is a guess: G4 |
| F3 benchmark undefined | FIXED in content | NEW PROBLEMS: plan infeasible (N1); rehearsal geometry against the candidate plan (N2) |
| F4 margins | PARTLY | Rule fixed (max(0.10, 2·CV_R), 0.30 ceiling). CV_R is taken in K on the 1 GiB store with B_r = 21,845, whose routing is 16 times cheaper, so the arms' CV does not represent the registered run (X-4) |
| F5 bytes by construction | FIXED (accepted; contest withdrawn; prediction registered) | Request lists against the prediction: G3 |
| F6 EC3 | FIXED and sound | See section 4 |
| F7 counter API | FIXED | |
| F8 engineering stop; order of reasons | FIXED | Which reasons apply to which EQ is unstated (X-8) |
| F9 in-project IVF | FIXED | |
| F10 S-FLAT cost | FIXED (10 on device; reference in RAM) | Counter exactness for 1 MiB requests is not tested in R1 (X-7) |
| F11 order, caps, frozen inputs | PARTLY | `plan.json` holds m_t and quiet figures that K produces, yet K must run against the identical file; "every pass" is in `plan.json` (§12) but generated by P after the freeze (§5.3) (X-2) |
| F12 memory guard | FIXED | Exact-search chunking under 12 GiB is a guess: G8 |
| F13 KEYS rung | FIXED (X-RES) | |
| E-1 | SUPERSEDED by §2.3, conditionally | The quotes are **not** in the committed `DELEGATION_2026-11-18.md` at `2d92c27` (grep: no "250", no "ssd test"). X-1 |
| E-2 to E-5 | FIXED | |
| E-6 | PARTLY, NEW PROBLEM | Load ≤ 1.0 is read at block end, after the stage's own single-threaded process has run for minutes, so the 1-minute load includes itself. Idle load here was 1.95 to 2.13 with nothing of ArborLM running (6 samples, 5 s apart). X-6 |
| E-7 | PARTLY | Circularity, as F11 |

## 3. Registered questions

**N1 — BLOCKING. §4.4, §13 ruling 7: disjoint-page plan infeasible.**

- Model: `r4_0028_disjoint_sim.py`, stdlib. A query has its own branch plus p−1 uniform other branches for key pages and its own branch's 2 value pages. SWEEP is drawn at uniform offsets; acceptance requires every page unused; factor 3.
- Result as drafted: SWEEP s = 64 gets 333 of 400 in repeat 2, then 113, 28 and 5. IVF-8 gets 793, 514 and 362 of 1,000 in repeats 3 to 5. Even with no SWEEP, IVF-8 exhausts in repeat 3.
- With SWEEP on a fixed grid in a reserved band (`r4_0028_disjoint_sim2.py`), 1,000 queries still exhaust IVF-8 in repeat 3; **500 queries per pass fit with margin** (12 % of key pages used by repeat 5).
- Real nearest-neighbour hubness would make this worse. Exhaustion is an ENGINEERING STOP before any device read, so nothing is lost, but the study as written cannot complete. Edit X-3.

**N3 — REQUIRED. EQ-C is nearly insensitive.**

- One-thread routing at B = 349,525 (`r4_0028_route_cost.py`): S-TREE 1,144 µs median, IVF-2 893 µs, IVF-8 889 µs.
- I/O at 4 to 10 pages × about 80 µs is about 0.3 to 0.8 ms.
- So t_cpu is 55 to 80 % of L. A 30 % deviation in per-page cost moves g by only about 6 to 13 %, under m_t ≥ 0.10. X-RES is far more CPU-bound still (an exact search over 89.5 M keys).
- COST MODEL HOLDS is then reached almost by construction. Redefine g on the I/O part (X-4). `PENDING LEAD REVIEW`.

**N4 — ADVISORY.**

- EQ-B's outcome is near-certain (ρ about 1/3 by NVMe physics). That is acceptable as a confirmation, but §5.4 should say so.
- SWEEP samples only the value region, which is written after the key region. A recency effect inside the drive (an SLC cache) would bias c_r(1) against key-page reads. X-9.

**N5 — REQUIRED. EQ-A wording.** BYTES CONFIRMED EXACTLY with "at least 4 of 5 repeats" lets a failing pass sit under a label named "exactly". X-5.

**Other checks on the label rules.**

- Labels: EQ-B's and EQ-C's tables each reach exactly one label ("otherwise" and "first match"). I enumerated the arm-state combinations (WITHIN / DEARER / CHEAPER / unclassified over 7 arms) and found no gap.
- σ fitted on IVF-2's recall: **not a fit to any registered outcome.** EQ-A, EQ-B and EQ-C do not use recall. σ shifts only v, the value pages per query, and the printed matched table. It uses an independent calibration seed and is disclosed. Acceptable.
- Positive control: R1 only, on its own file. Correct.
- Read discipline: matches what my probes found. It is missing one item: no file writes or prints between snapshots (G10).

## 4. Writes, free space, hygiene, EC1/EC3, administrator access

**Arithmetic, all reproduced:**

- 67,108,864 × 2 + 1,073,741,824 + 1,073,725,440 + 17,179,852,800 = 19,461,537,792.
- One rebuild of everything except the probes adds 19,394,428,928, for 38,855,966,720 in total.
- 40e9 / 2,001,111,162,880 = 2.00 %; 19.46 GB is 0.97 %. 40 GB at 5.53 MB/s is 2.01 h.
- 1,048,575 × 16,384 = 17,179,852,800. 5,461 × 64 + 21 = 349,525.

**Free space and access.** Free space now is 704,360,584 KiB, which is 721.3 GB. After the 40 GB cap that still leaves more than 500 GB. Nothing in the plan needs administrator access: `tmutil addexclusion` without `-p`, `caffeinate`, `mdutil -s`, `ioreg`, `diskutil` and `proc_pid_rusage` all run without it. `.noindex` is untested, and R0 checks it.

**EC1 and the write budget.** "if you need 200gb or 250gb for the test im also ok with that" answers the write budget plainly. Together with "we could do a better test in my ssd …", the 75 GB download permission and "auto approve everything until you complete P10-I", it answers EC1 for the engineering part. Both answers hold **only once the words are verbatim in the committed delegation record, with date and source, before Decision 1**. At `2d92c27` they are not. The task message says he "said he wants the SSD test"; that sentence is not among the §2.3 quotes and should be added verbatim if it exists (X-1).

**EC3 restated** is sound:

- SMART `Verified`, `df` and the driver's bytes written are recorded before and after each writing stage.
- Lifetime counters print NOT READABLE.
- A non-Verified status is PAUSED.
- 40 GB is 2 % of one drive write.
- It is a safety gate, not a scientific threshold, and the human lead's 250 GB words cover its purpose. Confirming it with him, as §11 item 3 does, is right.

## 5. Engineering pattern

**N2 — BLOCKING. §8, §12, §5.3, §10.**

- **(i)** `plan.json` lists "σ, m_t, quiet figures … every pass". But m_t and the quiet figures come out of K, and K must run against a file whose SHA-256 the freeze then requires. And "every pass" is written by P **after** the freeze.
- **(ii)** M and K run "against the candidate plan" on a store of 21,845 branches. The registered passes need about 17,000 key pages per repeat and cannot run there.
- **(iii)** K needs 5 repeats for CV_R, but the registry gives the rehearsal one workload seed (289211) and one arm-order seed (289221).
- Edit X-2.

**N6 — REQUIRED (E-6 above).** The quiet check's load rule. Edit X-6.

**Run alone and on time.**

- Run alone, correctly: R1, M, K and E2. E1 must not overlap another study's wall-time stage. C and P can share the machine under the memory guard.
- E2 also cannot overlap P10-I-R's registered stages: its process filter would fail the quiet check.
- Hours: 4 to 6.5 charged is plausible from my figures. That covers P's roughly 46,000 exact searches, multi-threaded (minutes of arithmetic plus top-k), and E2 with about 1 ms of routing per query.
- Quiet waiting under the current rule could reach the 4 × 6 h limit, then MACHINE NOT QUIET.
- Memory guard: K + R + 1 GiB is about 6.4 GiB, which holds only if exact search is chunked (G8).

## 6. Edits (exact)

- **X-1** (§2.3, after "this section is not that record."): add "Decision 1 is not taken until `DELEGATION_2026-11-18.md` contains each sentence above verbatim with its date and the channel it came through; EC1 and EC2 are met only from that record." In §3.1 EC1, replace "It is recorded in the delegation record before Decision 1." with "It is met only when the delegation record holds those words verbatim (section 2.3)."
- **X-2** (§12, Frozen inputs): replace "`freeze/plan.json` (store geometry, seeds, σ, m_t, quiet figures, store path, every pass)" with "`freeze/plan.json` (registered and rehearsal geometries, seeds, σ, store paths, candidate counts and acceptance rule; not m_t, not the quiet figures, not the passes); K's record (m_t, CV_R, quiet figures) as a separate frozen file; the prediction record of section 5.3 (every pass), whose SHA-256 is frozen by E2's refusal rule". In §8, row M, replace "against the candidate plan" with "against the candidate plan's rehearsal geometry (B_r = 21,845; 100 queries per pass; X-RES 20; SWEEP 40 per size; 5 repeats)". In §10, rehearsal column: workloads 289211–289215, arm order 289221–289225, SWEEP 289241–289245 (289212 becomes a workload seed, no longer unused).
- **X-3** (§4.4 and §9 design ceilings; `PENDING LEAD REVIEW`): "S-TREE, each IVF-p and KV: 1,000. X-RES: 200" → "S-TREE, each IVF-p and KV: 500. X-RES: 100"; "from at most three times" → "from at most ten times"; add to §4.3's SWEEP row: "Offsets: a fixed grid of non-overlapping aligned segments inside a band of the value region reserved for SWEEP (the value pages of branches 0 to 97,999); no query's own branch lies in the band; segments are assigned to repeats and sizes by the SWEEP seed." Recompute §10's request counts.
- **X-4** (§5.4 EQ-C; `PENDING LEAD REVIEW`): replace the definition of g with "g(a, r) = median over arm a's single-page requests in repeat r of their request latency / c_r(1) − 1, where c_r(1) is the median over SWEEP's s = 1 requests of the same region mix (X-9); t_cpu(q) and L̂ are printed descriptively". In the m_t paragraph replace "among c(1), c(3) and each read-path arm's median latency" with "among c(1), c(3) and each read-path arm's median request latency".
- **X-5** (§5.4 EQ-A): replace "every pass of at least 4 of 5 repeats, and every S-FLAT query" with "every pass of every repeat attempted, including any repeat later run again, and every S-FLAT query"; add "A repeat run again after a rebuild is printed with the failed attempt beside it."
- **X-6** (§8 quiet check): replace "1-minute load average at most 1.0" with "1-minute load average, read before a block's first pass process starts and again after the last one has exited and 120 s have passed, at most R1's idle-window 95th percentile plus 0.5 (fixed at the freeze in K's record)". In §9's threshold row, replace "Load 1.0" with "Load ceiling by that rule".
- **X-7** (§7, R1 list): after "a first and a repeated uncached pass" add "for requests of 1, 3, 64 pages and 1 MiB".
- **X-8** (§9, after the NOT EVALUABLE list): "MACHINE NOT QUIET and TIMING SPREAD apply to EQ-B and EQ-C only; EQ-A uses every pass whether or not its block was quiet."
- **X-9** (§4.3 SWEEP row): "400 per size" → "400 per size in the value band, plus 400 single-page requests per repeat in the key region at pages no query uses (the key pages of branches 0 to 97,999); c_r(1) is reported per region".
- **X-10** (§13, new ruling 14): "Each pass loads the routing table file written by P (SHA-256 in the prediction record), computes its requests live, and asserts they equal the prediction record's list for that query before issuing them; a difference is ENGINEERING STOP (PREDICTION MISMATCH). P computes the routing table on one thread."
- **X-11** (§7 item 6): add "Expected page hashes are written by P; hashes of read pages are computed after the pass's last snapshot (S-FLAT: after each request, outside that request's timer and excluded from its query latency, which is recorded as the sum of request times plus scoring time)."
- **X-12** (§8): add "If a block is discarded, it is repeated with workload seed 280006 (and 280007, 280008 for further ones), whose passes P plans as spares."

## 7. Implementer's guesses, with recommended rulings

- **G1** Generator draw order inside a block: centres for 1,024 branches, then key noise per branch in order, then values; float32 `torch.randn`; noise = randn × 0.25 × σ; `F.normalize` eps 1e-12. Rule exactly this.
- **G2** Routing table: dtype float32, mean over 256 then normalize, one thread (X-10).
- **G3** Live requests against predicted requests: X-10.
- **G4** When the parity hash runs: X-11.
- **G5** Rehearsal geometry and counts: X-2.
- **G6** Where SWEEP offsets come from: X-3, X-9.
- **G7** Spares: X-12.
- **G8** Exact-search chunking: at most 1,048,576 keys × 256 queries per score block; merge top-8 per chunk with ties to the lower id. The recall reference uses the same float32 cosine.
- **G9** Recall: mean over the pass's queries of |selected ∩ exact| / 8. "IVF-2 recall ≥ 0.95" in C is that mean. If no IVF-p meets the floor, print "NO ROUTING ARM AT FLOOR" in the matched table.
- **G10** No print or file write between snapshots; stdout buffered in memory.
- **G11** Arm-order permutation: `torch.randperm(8, generator=manual_seed(seed))` over the order of ruling 7.
- **G12** K's disjointness: within K only, on seeds disjoint from M's.
- **G13** Rows of S-FLAT's "per repeat" figures: two per repeat, run after block 5, printed by repeat.
- **G14** Calibration key set: generated with 289041 at full B, one σ at a time, freed between σ values (memory guard).

**Seeds.** `python3 -I -B docs/reviews/p10-i-direction-2026-11-17/seed_registry_check_r3.py` in the draft tree (SHA-256 `e4623604…22c67594`) → `r4_seedcheck_0028.out`, exit 1. That is the known ADR-0029 self-collision only, with ADR-0028 data 280001–289999 at **0 collisions**.

- 287001–287005 lie in S5's auxiliary block 287001–288999, which is empty. 289041, 289042 and 289051 lie in the R1 block 289001–289199, unassigned. 289241 lies in the rehearsal block 289201–289299, unassigned. All are free.
- Recommendation: calibration is a registered input, so move it to the auxiliary block as 287101 and 287102 rather than R1's block.
- Spares 280006–280008 are already registered (X-12).
- The registry revision 4 is a lead or auditor action before the freeze. I have not written it.

## 8. Open choices under the delegation

| Item | Recommended option | Delegable? |
|---|---|---|
| 1 | EC1 by the human lead's words | Yes, only after X-1 |
| 2 | 40 GB cap | Yes, sound, within his 250 GB |
| 3 | EC3 restated | Sound; confirm with him as drafted |
| 4 | One file, no k-means IVF | Sound (section 2(a): it is a RAM question) |
| 5 | S-FLAT 10 queries | Sound |
| 6 | σ rule | Sound (not an outcome fit) |
| 7 | m_t, 4 of 5 | Sound after X-4 and X-5 |
| 8 | Scientific part stays NOT EVALUABLE | Sound |
| 9 | Decisions 1 and 2 | The lead's |
| Scope | Full study or the smaller QD-sweep study of section 2 | Choose by delegation only with the lead's recorded reasoning: it changes what P10-I tells the human lead |

None of the choices needs administrator access, a download, a package outside the lock or a paid service.

## Commands

All run from the reviews folder, outputs beside them:

- `git -C <draft> log/diff/status`; `grep` of ADR-0029, `DELEGATION_2026-11-18.md` and `SEED_REGISTRY.md` in the draft tree; `sysctl -n vm.loadavg` (six samples, 5 s apart); `ps -Ao`; `ioreg -c IOHIDSystem`; `df -k`; `date -u`; `sw_vers`.
- `timeout 300 python3 -I -B r4_0028_disjoint_sim.py` → `.out`
- `timeout 300 python3 -I -B r4_0028_disjoint_sim2.py` → `.out`
- `timeout 120 <draft>/.venv/bin/python -I -B r4_0028_route_cost.py` → `.out` (descriptive; not quiet)
- The seed checker, as above.

No sudo, no install, no network, no probe writes, no store, no registered checkpoint or sealed value opened.

`Astra review: NOT_PERFORMED`.
