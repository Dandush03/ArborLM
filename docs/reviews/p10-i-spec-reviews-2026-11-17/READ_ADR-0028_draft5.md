# Confirmation read of ADR-0028 DRAFT 5 (P10-I-S5), engineering part

- Reader: `arbor-auditor` subagent, Claude Opus 5.5 (`claude-opus-5-5`, as the session reports it). I wrote REVIEW3 and REVIEW4, so section 1 judges fixes to my own findings. I wrote no part of ADR-0028.
- Date: 2026-11-18, about 04:00 to 04:30 UTC. Draft: worktree `agent-a9976922e8c647b3b`, branch `claude/p10-i-s5`, commit `d2c52a8`, 463 lines. I read the diff `2d92c27..d2c52a8` (2 files, +435 / −211). I wrote nothing to that tree. `REVIEW4_ADR-0028.md` there matches my copy byte for byte (SHA-256 `4f39025f…1263d`).
- Delegation record: `docs/reviews/p10-i-direction-2026-11-17/DELEGATION_2026-11-18.md`, section 7, commit `fa60cc4` on `claude/p10-i-r`.
- Environment: macOS 27.2.1, Mac17,6, 18 cores, 51,539,607,552 B RAM. Scripts ran under `/opt/homebrew/bin/python3 -I -B` (CPython 3.15.1), which is **not** the platform of record.
- The machine was **NOT quiet**. The P10-I-R count rehearsal and a P10-I-S3 synthetic rehearsal were running, and the 1-minute load was 4.86 to 6.06. Probe timings are descriptive only.
- `Astra review: NOT_PERFORMED`. This read is not Astra review and not human approval.

## Verdict

**CONFIRMED WITH THE LISTED CORRECTIONS** (section 8: C-1 and C-2 required, C-3 to C-9 smaller).

Draft 5 closes every blocking item of REVIEW4. My own 64 MiB probe turned up one new hazard (C-1). Without that correction, a build artefact could fix EQ-A at BYTES NOT CONFIRMED before E2's first pass.

## 1. Disposition of REVIEW4 edits and findings

| Item | Disposition | Note |
|---|---|---|
| X-1 | FIXED (one detail PARTLY) | The record quotes the four sentences verbatim, dated 2026-11-18 UTC. The channel is implied ("later messages of the human lead") but not stated. C-9 |
| X-2 | FIXED in substance | M measures; K produces nothing frozen. `plan.json` holds definitions only, and the freeze refuses any hash but K's. The rehearsal geometry fits (section 2). Rehearsal seeds are 5 + 5 per stage |
| X-3 | SETTLED by scope; FIXED by tiling | Section 2 |
| X-4 | SETTLED (EQ-C withdrawn) | |
| X-5 | FIXED | "printed beside its second attempt": no pass has a second attempt on the same tiles. C-6 |
| X-6 | FIXED for the load rule | NEW PROBLEM: the idle baseline itself can be taken on a loaded machine. C-2 |
| X-7 | FIXED | 1, 3, 8 and 64 pages, at depths 1 and 32 |
| X-8 | FIXED | |
| X-9 | FIXED | A whole-file permutation |
| X-10 | FIXED | Request lists; there is no routing table |
| X-11 | FIXED | |
| X-12 | FIXED | Spare 280006 / 280206 |
| N1 | FIXED | Section 2 |
| N2 | FIXED | |
| N3 | SETTLED (EQ-C withdrawn) | |
| N5 | FIXED | |
| N6 | FIXED, with C-2 | |

## 2. Tiling, verified by simulation

Script: `r5_0028_tiling_sim.py`, output in `.out`, exit 0. It re-implements §4.3 and rulings 3 and 4 independently, using `random.Random` in place of `torch.randperm`; disjointness does not depend on the generator. Seeds tried: 1, 2, 3 and 287001.

**Registered geometry.** Six repeats (five plus the spare), 6 depths, 4 sizes, n(s) = 400 / 400 / 160 / 64, tiles 7 / 20 / 20 / 64.

- 3,996 tiles dealt out of 4,096, with no short pass.
- Segments per pass: 448, 420, 160 and 64.
- Duplicate pages: **0**.
- Totals: 36,864 requests; 251,136 pages; 4,114,612,224 B.
- Without the spare: 30,720 requests; 209,280 pages; 3,428,843,520 B. These match §4.2 and §10.
- Predicted bytes per pass: 6,553,600 / 19,660,800 / 20,971,520 / 67,108,864. These match §5.2.
- Minimum tiles needed per pass: ⌈400/64⌉ = 7, ⌈400/21⌉ = 20, 160/8 = 20, 64. The deal has no slack at s = 8 and s = 64, and that is still enough.

**Rehearsal geometry.** Five repeats, 840 of tiles 0 to 895, 0 duplicates. A **sixth (spare) rehearsal repeat is infeasible**: it would need 1,008 tiles, more than the 896 available. The draft defines no rehearsal spare, so the text should say none exists (C-5).

**Writes.**

| Quantity | Bytes |
|---|---|
| Planned | 5,502,926,848 |
| Planned plus one rebuild of the main file | 9,797,894,144 |
| Headroom under the 10 GB cap after the plan | 4,497,073,152 |
| Headroom after a rehearsal-file rebuild | 3,423,331,328 |
| Writes under Decision 1 | 1,207,959,552 |

- After a rehearsal-file rebuild the headroom is below one 4 GiB file, so the main file could no longer be rebuilt. §6's wording on this is wrong (C-4).
- The 10 GB cap is 0.4997 % of one full drive write and 1,808 s at 5.53 MB/s.

## 3. EQ-A, EQ-B, EQ-D: labels, margins, stops

**EQ-A.** Computable and deterministic. "Every pass of every repeat attempted" makes the label honest. It cannot become NOT EVALUABLE through TIMING SPREAD or MACHINE NOT QUIET, and that is correct.

**EQ-B.** The three rules are mutually exclusive in each repeat, and no two labels can each hold in 4 of 5 repeats. "Otherwise" closes the table, so each outcome gets exactly one label.

- m_t = max(0.10, 2·CV_R) is taken from M and fixed in the config before `plan.json` exists, which is before any registered read.
- If m_t would exceed 0.30, the result is NOT EVALUABLE (TIMING SPREAD), written into the config. Sound.

**EQ-D.** Descriptive, with no threshold. NEW, small problem: validity is per block (§5.4), so every cell has the same number of valid repeats. "At least 20 of 24 cells" is therefore the same test as "at least 4 valid repeats" and can never separate cells. Say so (C-3).

**Stops.** ENGINEERING STOP, PAUSED and the order of NOT EVALUABLE reasons are defined. After a stop, the stage must run again "on tiles not yet read". For E2 that is infeasible on the same file, because only 100 tiles plus the spare are free. C-7 settles it.

**HARNESS-LIMITED.** h(k) is the median of 400 cached single-page requests on the control file. The tag applies when h(k) is above 0.25 × the cell's median. It is computable and descriptive. Two gaps (C-8):

- The control file is never warmed. Reads with F_NOCACHE do not fill the cache, so a normal read must warm it first.
- The draft does not say which h(k) sets the tag: R1's or E2's.

**Threads and the counter: probe evidence.** Script `r5_0028_thread_probe.py`, output in `.out`. It wrote 67,108,864 B (counter equal to the logical bytes) with F_NOCACHE and F_FULLFSYNC beside the script, then deleted the file (deletion confirmed). The machine was not quiet.

| Pass | Depth k | Size s | Median latency | Pages/s | Max in flight | Mean in flight |
|---|---|---|---|---|---|---|
| Region 0 | 1 | 1 page | 71.6 µs | 13,618 | | |
| Region 1 | 8 | 1 page | 84.6 µs | 85,548 | 8 | 7.80 |
| Region 2 | 32 | 1 page | 249 µs | 96,648 | 32 | 28.7 |

- **Concurrent device reads do occur from `os.pread` threads.** At depth 8 the pages per second rose 6.3 times while the median latency rose only 18 %.
- Depth 32 adds only 13 % over depth 8. This probe cannot tell whether the harness or the device sets that limit; the HARNESS-LIMITED tag is the right treatment. Settled descriptively; R1 still re-checks it under the platform of record.
- **The per-process counter covers all threads.** It was exact in three multi-thread passes (k = 8, 32, 32) on regions with no cached pages. Settled for this machine; R1 re-checks it.

**NEW FINDING (behind C-1).** Three of the seven uncached passes counted **fewer** bytes than requested:

| Pass | Shortfall |
|---|---|
| Region 0, depth 1 | 1,048,576 B (64 pages) |
| Region 0, 64-page re-read | 1,048,576 B (64 pages) again |
| Region 3, depth 4, 3-page requests | 1,032,192 B (63 pages) |

- Region 3's pass read pages 3072 to 4094 and skipped page 4095. So the 63 missing pages are the file's **last** 1 MiB less the one unrequested page.
- Regions 1 and 2 were exact on first and repeat reads.
- So one 1 MiB chunk in the first 16 MiB (presumably the first) and the last 1 MiB were already in the page cache. They stayed there across later uncached reads, as probe 1D predicts.
- The probe slept 5 s between build and reads, in a folder that Spotlight indexes (`mdutil -s` enabled; `mdfind -onlyin` lists 63 items; `r5_0028_spotlight_check.out`). The third review's probes read immediately and saw exact counts.
- **Hypothesis, not proven:** a system reader (for example a Spotlight importer reading a new file's head and tail) cached them. Localising it would need another write beyond my 64 MiB allowance, so I did not try.
- **Consequence under draft 5.** Tiles 0 and 4095 are in the deal with probability 3,996/4,096 each. EQ-A would be BYTES NOT CONFIRMED by an event before E2, and nothing in E2 could avoid it. The 10-minute settle does not help, and the build's verification read cannot detect it because it checks hashes, not the counter.

## 4. Quiet rule, alone-stages, pattern, writes, access

- R1, M, K and E2 run alone. E1 must not overlap another study's wall-time stage. The process filter makes E2 refuse while P10-I-R is alive, which is correct and consistent with the record's "parallel only where no stage takes a timing measurement".
- The baseline gap (C-2): R1's idle window has no validity condition. If it is taken while other studies run (load 4.9 to 6.1 today), the ceiling becomes about 6.5 and "quiet" means nothing.
- The 30 s I/O window is compared with a 95th percentile of 10 s samples, but the draft does not say how. C-2 rules it.
- Engineering pattern: sound (§12).
- Write accounting: sound apart from C-4.
- Nothing needs administrator access, a download or a package outside the lock. Every tool named was confirmed in REVIEW4. The probe used stdlib and `ctypes` only.

## 5. Seeds against SEED_REGISTRY.md revision 3

The registry is identical in both trees: SHA-256 `7211706f…4f39`; checker `e4623604…c67594`. Checker run from the draft tree; output `r5_seedcheck_0028.out`, exit 1. That exit is the known ADR-0029 self-collision. ADR-0028 data 280001–289999: **0 actual collisions**.

Each new value lies in S5's own blocks:

| Value | Block | Assigned? |
|---|---|---|
| 287001 | auxiliary 287001–288999 | listed only as that block's bound; unassigned |
| 280206 | registered 280001–286999 | unassigned (the arm-order row stops at 280205) |
| 289051 | R1 | unassigned |
| 289213–289220, 289222–289230, 289241, 289242 | rehearsal | unassigned |

- A grep of `docs`, `studies`, `configs`, `src` and `tests` finds none of them outside ADR-0028, the registry and the review texts.
- Derived generator states are domain-separated by SHA-256 strings, so the checker's +1000k informational pairs do not apply.
- **All are free.** Two roles change meaning and revision 4 must record them: 289013 becomes the control-file contents, and 289212 becomes M's repeat-2 order.

## 6. Scientific part and separation

- §3.2's body and the §5.6 scientific label are byte-identical to draft 4 (`r5_0028_sci_compare.out`).
- The value stays SCIENTIFIC NOT EVALUABLE (PREREQUISITES NOT MET).
- §1 forbids joining the two lines.
- §5.5 carries "ARITHMETIC ONLY — NOT MEASURED — NOT A READ PATH".
- §14 excludes memory, accuracy, the trained tree, routing cost and storage need.
- No engineering label can be read as a result about ArborLM.

## 7. EC1, the write budget, Decision 1

**My judgement** (not human approval).

- **Write budget: answered by his own words.** "if you need 200gb or 250gb for the test im also ok with that". The 10 GB cap is 4 % of that.
- **EC1 for the engineering part: answered.** The words are "we could do a better test in my ssd not sure why not" together with "auto approve everything until you complete P10-I". They are verbatim, dated, and committed in `fa60cc4`. EC1 is now defined by his permission, not waived by the lead, so section 3's "the lead does not waive an entry criterion" is not breached.
- **Decision 1 for the engineering part (implementation, R0, R1, M, K) may be taken by the lead under section 7's first reading** ("the lead takes every P10-I approval"). Three conditions:
  1. this read's corrections are applied;
  2. the approval record says it is taken under that delegation and reports the scope and EC3 choices to him first (as §2.3 does);
  3. the frozen tree contains `fa60cc4`'s record.
- Whether a delegated Decision 1 counts as "recorded human approval" under AGENTS.md is governance: `PENDING LEAD REVIEW`.
- The scientific part is not covered.

## 8. Corrections (old → new)

- **C-1 (REQUIRED)**
  - §13 ruling 13, after "it precedes every registered pass).", add: "Each verification read is counter-checked like a pass. After the 10-minute settle and immediately before E2's harness figure, the whole file is read once more, uncached and counter-checked (the pre-E2 sweep). A short count means the file was polluted before E2: it is rebuilt under the write budget before any registered pass, and EQ-A is not affected."
  - §7, R1 list, add: "the rehearsal file is built in the `.noindex` directory, left 10 minutes, then swept uncached with the counter; a short count is CACHE NOT DEFEATED".
  - §6 Spotlight row: "If the directory is indexed: PAUSED before E1." → "If the directory is indexed, or R1's post-settle sweep is short: PAUSED before E1."
- **C-2 (REQUIRED)**
  - §8 load bullet, add: "R1's idle window is valid only if the no-other-study, idle-time and power conditions hold at every sample; otherwise it is retaken under the waiting rule."
  - Disk bullet: "over a 30 s window at or below the 95th percentile of R1's idle window" → "whose mean rates over a 30 s window (read bytes, write bytes, read operations, write operations, each per second) are at or below the 95th percentile of the same rates over R1's sixty 10 s intervals".
- **C-3** §5.3 EQ-D, after "otherwise.": add "Validity is per block, so every cell has the same count of valid repeats; the 20-of-24 rule is equivalent to at least 4 valid repeats."
- **C-4** §6: "A rebuild of the rehearsal file uses most of the allowance, and a later pollution" → "After a rebuild of the rehearsal file, 3.42 GB remain under the cap, less than one 4 GiB file, so a later pollution". §3.1: "(at most 1.21 GB written)" → "(1.21 GB planned; 2.28 GB with one rebuild of the rehearsal file)".
- **C-5** §13 ruling 11, add: "M and K have five repeats and no spare (a sixth needs 1,008 tiles of 896); an invalid rehearsal block is recorded, not replaced."
- **C-6** §5.3 EQ-A: "every failing pass is printed beside its second attempt" → "every failing pass is printed beside the same cell's pass in the replacing block, if any".
- **C-7** §9 ENGINEERING STOP: "run again on tiles not yet read" → "run again on tiles not yet read; in E2, on a rebuilt file (charged; PAUSED if the cap does not allow it). EQ-A covers every pass with both counter snapshots in every attempt, including a stopped one".
- **C-8** §5.4 harness figure, add: "The control file is first read once without F_NOCACHE to warm it. The tag uses E2's h(k); R1's is printed."
- **C-9** §2.3: "committed as `fa60cc4`" → "committed as `fa60cc4`; the words came in the human lead's conversation with the lead on 2026-11-18 UTC. The branch is rebased on that commit before the freeze."

**Implementer's remaining guesses, with my rulings.**

- **Byte order of "first 8 bytes … modulo 2⁶³"** (§4.1, ruling 4): big-endian, `int.from_bytes(d[:8], "big") % 2**63`.
- **R1's use of the band:** counter passes in rehearsal n(s) at k = 1 and k = 32 over tiles 896–951, dealt in order, with the 289011 order, each re-read once. Working-set re-reads (32, 64 and 128 tiles from 896) run last, at offsets from 289051.
- **Pass order of the rehearsal M and K repeats:** as ruling 5 with their own seeds.

## Commands

All run from `experiments/_scratch/reviews3/`; outputs are beside the scripts.

- `git -C <draft> log/diff/status/show`; `shasum -a 256`; `grep -rnoE` over both trees; `ps -Ao`; `sysctl`; `df -k`; `mdutil -s`; `mdfind -onlyin`.
- `timeout 300 python3 -I -B r5_0028_tiling_sim.py` → `.out`
- `timeout 300 python3 -I -B r5_0028_thread_probe.py` → `.out` (64 MiB written and deleted)
- `(cd <draft> && python3 -I -B docs/reviews/p10-i-direction-2026-11-17/seed_registry_check_r3.py)` → `r5_seedcheck_0028.out`
- Inline comparison script → `r5_0028_sci_compare.out`, using `r5_adr0028_d4.md` and `r5_adr0028_d5.md` (extracted by `git show`).

No sudo, no install, no network, nothing under /tmp. No failed checker attempts in this read.

`Astra review: NOT_PERFORMED`.
