# Third review of ADR-0028 (P10-I-S5, physical SSD-backed memory), engineering part

- Reviewer: the `arbor-auditor` subagent, model Claude Opus 5.5 (`claude-opus-5-5`, as the session reports it). I did not write any revision of ADR-0028 or of the earlier reviews.
- Date: 2026-11-18, about 03:45 to 04:30 UTC. Branch `claude/p10-i-r`, HEAD `ef5596b`, tree clean at the start. Draft: `docs/decisions/ADR-0028-p10-i-s5-physical-ssd-memory.md`, revision 3, 282 lines (last changed in `169190f`).
- Scope set by the coordinator: **the ENGINEERING SSD PERFORMANCE line only.** The scientific line stays SCIENTIFIC NOT EVALUABLE (PREREQUISITES NOT MET), as the draft says. I checked that reasoning only against the current ADR-0024 text.
- `Astra review: NOT_PERFORMED`. This review is not Astra review and not human approval.

## Verdict

**NOT READY** for approval of implementation and rehearsal of the engineering benchmark (stages E1 and E2).

The cache method can be made to work on this machine **without administrator access**. My probes show this: the per-process counter is exact, uncached reads bypass the page cache, and a cold state is reachable without `purge`. But the draft leaves the benchmark's content to "a later revision" (§13): what S-TREE is, which ANN, the layouts, the workload, the store size, page size, candidate budgets and margins. An implementer would have to invent the study (section D lists the guesses). Some of the fixed rules also need changing now that the device has been probed (F1 to F4).

**Smaller scope that could be approved after text edits:** stage E0 alone (R0 and R1, the method rehearsal, at most 2 GB written), with edits E-1 to E-7 in section C. It still needs the human lead's own approval of the 2 GB write (§11 item 2). The delegation of 2026-11-18 §3 and §6 excludes the SSD write budget.

**Is it evaluable on this machine without administrator access?** Yes for the engineering line, as far as the probes go. Not measurable without administrator access or a tool install: lifetime wear and bytes written, and anything inside the drive (controller cache, NAND traffic). None of these is needed for a host-side engineering label if EC3 is restated (F6).

## A. Device facts checked on this machine (read-only, plus 56 MiB of probe writes)

Environment: macOS 27.2.1 (26B131), Mac17,6, Apple M5 Max, 18 cores, `hw.memsize` 51,539,607,552, `hw.pagesize` **16,384**. The probes ran under `/opt/homebrew/bin/python3` 3.15.1, stdlib only, with `-I`. That is **not** the platform of record (the project `.venv`, CPython 3.12.14). R0 must repeat the probes under the platform of record. During the probes a local `pytest` run (P10-S0 dry workers) was active, with load average 3.2 to 6.0, so the machine was **not quiet**. Every timing below is descriptive only.

| Fact | Value | Command |
|---|---|---|
| Drive | APPLE SSD AP2048Z, firmware 241.40.4, 2,001,111,162,880 B, internal, Apple Fabric, TRIM yes, device block 4,096 B | `system_profiler SPNVMeDataType SPStorageDataType`; `diskutil info disk0` |
| Data volume | disk3s5, APFS, FileVault on, hardware AES, allocation block 4,096 B; container 1,995,165,736,960 B | `diskutil info /System/Volumes/Data` |
| Free space | 713,070,936 KiB available (680.0 GiB); container free 730,184,597,504 B | `df -k / /System/Volumes/Data`; `diskutil info /` |
| Health | `SMART Status: Verified` is readable without administrator access. Lifetime bytes written, percentage used and temperature are **not** readable: `smartctl` is not installed; `ioreg` shows only `"NVMe SMART Capable" = Yes` and `"AppleNANDStatus" = "Ready"` | `diskutil info disk0`; `which smartctl`; `ioreg -l -w0 \| grep -i smart` |
| Writes since boot | disk0 driver `Bytes (Write)` 3,893,175,054,336 over 703,521 s (boot 2026-11-09 19:23:40 local): **5.53 MB/s, about 478 GB/day** | `ioreg -r -c IOBlockStorageDriver -l -w0`; `sysctl -n kern.boottime` |
| Snapshots | `tmutil listlocalsnapshots /` and `/System/Volumes/Data`: none. `diskutil apfs listSnapshots disk3s5`: "No snapshots". `tmutil destinationinfo`: "No destinations configured". The probe directory reports `[Included]`. All run without administrator access | as named |
| Spotlight | `mdutil -s`: indexing **enabled** on `/` and `/System/Volumes/Data` | `mdutil -s / /System/Volumes/Data` |
| Power and thermal | AC power, battery 100 %, `powermode 0`, no thermal or performance warning recorded, `sleep 0 (sleep prevented by Claude)`, `disksleep 10` | `pmset -g`; `pmset -g batt`; `pmset -g therm` |
| User idle | `HIDIdleTime` readable without administrator access (10,868 s at the time) | `ioreg -c IOHIDSystem -r -d 1 -k HIDIdleTime` |
| RAM state | free 181,903 pages × 16 KiB = 2.98 GB; file-backed 14.18 GB; swap used 842 MB | `vm_stat`; `sysctl vm.swapusage` |
| Background I/O | `iostat` 5.3 to 17.8 MB/s and 197 to 338 transfers/s; over a 5 s window disk0 wrote 532 MB and read 185 MB (pytest active) | `iostat -d -c 3 -w 2 disk0`; probe 1 `F_idle_5s` |
| `purge` | `/usr/sbin/purge` is present. **Not run**: it flushes the whole machine's cache while another session's checks were running. My belief that it needs `sudo` on current macOS is **untested** | `which purge`; `man purge` |
| Locked dependencies | `torch==2.8.0`, `psutil==7.0.0`; **no numpy** in `uv.lock`. `psutil.Process().io_counters` does **not exist** on macOS (`False`) | `pyproject.toml`; `grep '^name = ' uv.lock`; `.venv/bin/python -I -c ...` |

### Probes

Scripts and outputs are in `experiments/_scratch/reviews3/`: `ssd_probe_0028.py` → `ssd_probe_0028.attempt1.out`; `ssd_probe2_0028.py` → `ssd_probe2_0028.attempt1.out`; `ssd_probe3_0028.py` → `ssd_probe3_0028.out`. They wrote 32 + 16 + 8 = **56 MiB** in total, and each file was deleted (`"deleted": true`). The command for each was `timeout 180 python3 -I experiments/_scratch/reviews3/<script> > <out>`.

Counters: (P) is the per-process `proc_pid_rusage(getpid(), RUSAGE_INFO_V2)` fields `ri_diskio_bytesread` and `ri_diskio_byteswritten`, called through `ctypes` on `/usr/lib/libSystem.B.dylib`; (V) is the Data volume's APFS `Statistics` ("Bytes read from block device", "Bytes written to block device") from `ioreg -a -r -c AppleAPFSVolume -l`; (D) is the disk0 `IOBlockStorageDriver` `Statistics`. All three need no administrator access.

| # | Step | Logical bytes | (P) read | (V) read | Reading |
|---|---|---|---|---|---|
| 1A | 32 MiB written with `F_NOCACHE`, then `F_FULLFSYNC` | — | write 33,554,432 (exact) | write 35,676,160 | (P) charges the study's own writes exactly |
| 1B | First read after the uncached build: 512 random 16 KiB pages, `F_NOCACHE` and `F_RDAHEAD` 0, `pread` | 8,388,608 | **8,388,608** | 8,388,608 | Cold, ratio **1.000**, no administrator access needed |
| 1B2 | The same pages again, `F_NOCACHE` | 8,388,608 | 8,388,608 | 8,388,608 | Uncached reads leave nothing in the cache; repeatable |
| 1C1 / 1C2 | Ordinary cached reads of 512 other pages, first pass and second pass | 8,388,608 each | 8,388,608 / **0** | 8,388,608 / 0 | Positive control works: the counter sees caching |
| 1D | **`F_NOCACHE` read of the pages 1C left in the cache** | 8,388,608 | **0** | 0 | **`F_NOCACHE` does not bypass pages already resident.** Any cached read of a store page by anything (the build, a checksum, the RAM arm, Spotlight, a human `shasum`) makes later "uncached" reads of that page hits |
| 1E | 4 KiB `F_NOCACHE` reads at the start of 256 fresh pages | 1,048,576 | **4,194,304** | 4,194,304 | Reads are done in 16 KiB VM pages: a 4 KiB request reads 16 KiB (amplification ×4) |
| 2(i) | 16 MiB **buffered** write (no `F_NOCACHE`) + `F_FULLFSYNC`, then `F_NOCACHE` reads | 4,194,304 | **0** | 0 | A buffered build leaves the store warm; the build path decides the cold state |
| 2(ii) | (confounded by 2(i): the whole file was cached) | — | 0 | 0 | **My own design error**: the sub-check said nothing. It is kept as `ssd_probe2_0028.attempt1.out` and repeated as probe 3 |
| 3 | 4 KiB `F_NOCACHE` reads, then 16 KiB `F_NOCACHE` re-read of the same 128 pages, then 128 fresh pages | 524,288 / 2,097,152 / 2,097,152 | 2,097,152 / 2,097,152 / 2,097,152 | same | Sub-page uncached reads leave nothing cached either |

Descriptive timing, not quiet, Python overhead included: 512 uncached 16 KiB reads in 36.9 ms and 37.7 ms (about 72 to 74 µs each), and 128 in 10.9 to 15.5 ms (85 to 121 µs each). Cached reads took about 1 µs each. The two back-to-back uncached passes over the same 8 MiB (1B, 1B2) differ by 2 %, so there is no sign of a device read cache at 8 MiB. That is one observation, made on a busy machine. For scale, P10-S1's T-OQ ran about 10,100 queries/s at batch 1 in RAM, about 99 µs per query (recomputed below). **One uncached page read costs about as much as T-OQ's whole query in RAM.**

Recomputations of the draft's quoted figures (`python3 -I` over `results/p10s1-run-2026-11-17/supplement/throughput_supplement.json`): T-OQ at batch 1 is 10,106 / 10,211 / 10,132 q/s at 1,024 / 4,096 / 16,384 slots; F-OQ 19,177 → 7,292; D-OQ 107,879 → 16,768; 30 figures in 26.918 s. All agree with §2 and §10. `value_bytes_per_query` is 1,024 in RESULTS.md, as quoted. 16,384 × 192 = 3,145,728 and 51,539,607,552 / 3,145,728 = 16,384, as stated. 64 GB / 2,001,111,162,880 B = **3.20 %** of one full drive write. At the machine's mean write rate since boot, 64 GB is **3.2 hours** of its ordinary writing.

Seeds: `python3 -I docs/reviews/p10-i-direction-2026-11-17/seed_registry_check_r3.py` (SHA-256 `e4623604…c67594`) → `experiments/_scratch/reviews3/seedcheck_r3_0028.out`, `RESULT: FAIL`, exit 1. All 34 problems are ADR-0029's own config and tests matched against ADR-0029's own allocation, which is the known self-collision handled by ADR-0029 §19 ruling 6. Section [6] was skipped because `arborlm` could not be imported under this interpreter. **ADR-0028: 0 collisions** (lines 118 and 125). Other reviewers' outputs in `experiments/_scratch/` show the same FAIL.

## B. Answers to the coordinator's questions (a) to (g)

**(a) Store size and resident budget.**

- With the discipline the probes support (store written with `F_NOCACHE`, every read of every store file with `F_NOCACHE`, no read-ahead, 16 KiB-aligned whole pages), the page cache is excluded **per read**. The per-process counter verifies this exactly (1B, 1B2, 3). The store therefore does **not** need to exceed RAM for the measurement to be of the host block path.
- A size-based cold state ("store well above free RAM") is **not valid** here. Free RAM is about 3 GB, but inactive and file-backed pages (14 GB) are reclaimable, and the cache can grow to most of 48 GiB. Even a store twice the size of RAM gives a large hit rate under random access. It would need 96 GiB or more per layout and would still not be exact.
- What the size must satisfy:
  - (i) The disjoint-page requirement: pages per query × queries × arms × repeats × patterns ≤ pages in the store.
  - (ii) A working set far beyond any device-side read cache. Its size is unknown, so R1 measures it with back-to-back uncached re-reads at growing working sets.
  - (iii) Realism for the index: the number of leaves and the tree depth.
- 16 GiB per layout (89,478,485 rows of 192 B; 349,525 key pages of 16 KiB) is enough for (i) and (iii) at about 1,000 queries per arm per repeat. 8 GiB is the smallest I would defend, pending R1's device-cache test.
- **The resident budget** can only be enforced as an accounting rule: the bytes of the arrays each arm holds (routing data, centroids, keys), counted exactly from their shapes, and cross-checked with `ri_phys_footprint` from the same `proc_pid_rusage` call (readable, 24,150,568 B in probe 2). macOS has no per-process memory limit without administrator access, and `RLIMIT_RSS` is not enforced. The OS page cache is kept out of every arm's "resident" by the `F_NOCACHE` rule and its per-pass verification, not by a limit.

**(b) Cold cache without administrator access.**

- **Works**, measured: an `F_NOCACHE` write followed by `F_FULLFSYNC`, then `F_NOCACHE` + `F_RDAHEAD`=0 `pread` of whole 16 KiB pages. Ratio 1.000 on the first and on repeated passes.
- **Fails**, measured: a buffered build (2(i)), and any cached read of a page before the cold pass (1D).
- Cannot be verified from software: the drive's internal caches. Latency is the only signal.
- `purge` is **not needed** under this discipline. If R1 or a registered pass finds a store polluted (counter below the predicted bytes), there are three recoveries: (1) the human lead runs `sudo purge` (untested that it needs `sudo`; it would be his action); (2) restart the machine; (3) delete and rebuild the store, charged to the write budget.
- R1 must show, under the platform-of-record interpreter, on the KV arm and then on every arm's real build-then-read path:
  - the exactness of (P) against the predicted bytes;
  - the positive control, on a separate R1 file only;
  - the pollution control (1D);
  - the 4 KiB amplification (1E);
  - the device-cache test;
  - background rates and load at idle.

**(c) Device counters.** (P), (V) and (D) are readable without administrator access, and so is the driver's `Operations (Read)` / `Total Time (Read)`, which gives device service time independent of Python overhead in quiet windows. (P) is the right primary counter. It counts the bytes the process sent below the cache: 0 on cache hits, 16 KiB per page on uncached reads. Other processes cannot inflate it. (V) and (D) are system-wide: they matched exactly in short windows, but carried 170 MB and 185 MB of others' reads in a 5 s window. They confirm reads reached the block layer and the driver. They **cannot** confirm that the NAND was read rather than a controller cache. Do not use: `getrusage` `ru_inblock` (0 throughout; the draft's "resource usage" could be read as this), `psutil` (no `io_counters` on macOS), and `fs_usage` (needs administrator access).

**(d) Write budget.**

- 64 GB is 3.20 % of one full drive write and 3.2 hours of this machine's mean write rate since boot.
- Endurance is not readable. Under the draft's placeholder of 300 full drive writes, 64 GB is 0.011 %.
- 64 GB is **safe**. A store larger than RAM is **not needed** for the cold, uncached regime (a). It would be safe on wear (for example 2 × 96 GiB is about 206 GB, roughly 10 hours of the machine's own writing), but against the 500 GB free floor it leaves about 180 GiB of headroom and gains nothing exact.
- My recommended total is ≤ 40 GB: two layouts of 16 GiB, the S-FLAT key region, and rehearsal.
- Free space: 680 GiB now. After 64 GB it is still above the 500 GB floor.
- Interference, all detectable without administrator access:
  - Time Machine: no destination is configured and there are no local snapshots. Check with `tmutil listlocalsnapshots` and `diskutil apfs listSnapshots disk3s5` before E1, before each block, and after deletion.
  - Spotlight: indexing is enabled. Exclude by putting the store in a directory whose name ends in `.noindex`. This is untested here; verify it with `mdfind -onlyin <dir> .` (expect empty) or `mdls`.
  - Any reader that pollutes the cache (Spotlight importer, XProtect, iCloud) is caught by the exactness rule (F1).
  - The store directory must be outside any synced folder and outside any frozen worktree, at a path recorded in the plan.

**(e) Baselines inside the lock.**

- KV: a flat file of fixed-size rows; the address gives the offset. Trivial.
- ANN: IVF-flat (one-level k-means in torch, centroids in RAM, posting lists of keys and values contiguous on device) is implementable. IVF-PQ is implementable, but its codes (about 8 B per row, 716 MB at 89.5 M rows) exceed any budget R that equals a tree's routing data.
- A graph ANN (Vamana/HNSW) in pure Python at 89 M points is not buildable in hours.
- What is lost:
  - comparability with published systems (DiskANN, SPANN);
  - tuned SIMD distance code;
  - DiskANN's in-RAM compressed vectors;
  - parallel I/O at queue depth above 1, which is how graph indexes hide latency. QD1 disables it for every arm.
- Consequence for reading a result: a positive label against a home-written IVF is weak evidence; a negative one is informative. The draft should say so. Note also that SPANN is itself centroids in RAM (with a tree over them) and posting lists on SSD. "Tree over centroids" against "flat scan of centroids" is close to a design choice inside SPANN (see F9).

**(f) Wall time.**

- Queries per second and latency are wall-time readings and they enter the positive label. So **R1, E2 and S must run alone**.
- Bytes per query is not wall time. Under the discipline above it is **determined by the layout** (16 KiB × distinct pages), and the counter only confirms it.
- E1 (the build) has no registered timing, but it writes 16 GB or more at device speed. It must not overlap any other study's wall-time stage. It can share the machine with CPU-only training if memory allows (k-means over 89.5 M × 16 float32 keys is about 5.7 GB resident; the draft has no memory guard, F12).
- Quiet check, all without administrator access:
  - load average (`sysctl -n vm.loadavg`);
  - disk0 driver bytes and operations over a window before and after each block, against R1's idle figures;
  - `HIDIdleTime` above a fixed figure (the human lead is not using the machine);
  - `pmset -g batt` on AC power, `powermode` not low, `pmset -g therm` no warning;
  - no other ArborLM stage running (process list).
- If the check fails: the block is PAUSED, with the failed readings recorded, as the draft says.

**(g) What the engineering result can say.**

It can say how one hand-written hierarchical-partition read path and one hand-written IVF compare. The setting is fixed: synthetic vectors, one Apple SSD, 16 KiB uncached reads forced at queue depth 1, a store that **fits in RAM** and is only made to behave as if it did not, at a recall of at least 0.90 and equal in-process bytes. In that setting it reports device bytes (computed and verified) and wall time.

It cannot say anything about:

- the trained ArborLM tree (T-OQ) or any learned routing;
- training, capacity or quality;
- whether storage is needed (the store fits in RAM);
- other drives or queue depths;
- the published ANN systems.

Suggested sentence for §14: "A label on the engineering line describes one synthetic read path against one in-project baseline under forced uncached reads on this drive. It is not a measurement of ArborLM's trained memory, its routing or its usefulness, and no sentence about the project's objective may cite it."

### Smallest engineering study worth running

| Stage | Content | Writes | Hours | Machine |
|---|---|---|---|---|
| R0 | Device record (section A commands), the hygiene checks, the probes repeated under the platform of record | ≤ 64 MiB | 0.2 | shared |
| R1 | 1 GiB KV file: exactness, positive control on a separate file, pollution control, alignment, device-cache test with a growing working set (256 MiB to 1 GiB, re-read back to back), idle background and load figures, repeat variability of latency | ≤ 2 GB | 0.5 to 1 | **alone** |
| E1 | One store size, 16 GiB of rows (192 B: key 16 × float32, value 128 B) in two layouts (tree leaves, IVF posting lists), plus an S-FLAT key region of 5.3 GiB | about 38 GB | 0.5 to 2 (torch k-means CPU, estimate) | not alongside another study's wall-time stage |
| E2 | 5 repeats × {S-TREE, ANN, KV} × about 1,000 queries; S-FLAT on device on a small registered subset only (see F10) | 0 | under 1 of device time, plus quiet waiting | **alone** |
| Total | | **≤ 40 GB** (cap 64 GB) | about 3 to 5 charged | |

## C. Findings

Severity: BLOCKING / REQUIRED / ADVISORY.

**F1 — BLOCKING (rule change, evidence-based). §7 "Cold state reachable", "Ratio upper bound", the closing paragraph; §5 condition 3; §9.** The floors 0.9 / 1.1 / 0.05 allow up to a tenth of an arm's bytes to be cache hits, which is P7-A's mechanism again. They are also unnecessary: on this machine (P) equals the predicted device bytes **exactly** (1B, 1B2, 3, 1E). Replace them with an exactness rule: for every registered pass, (P) bytes read = 16,384 × (number of distinct whole pages the pass requests, counting the page amplification of sub-page requests). Any shortfall makes the pass invalid, named STORE PAGES CACHED. Any excess is COUNTER CONTAMINATED. Old → new text in E-2.

**F2 — BLOCKING. §7 and §4: the build and every read path must be uncached, and the RAM arm must not warm the store.** Probes 1D and 2(i) show that `F_NOCACHE` does not bypass resident pages and that a buffered build leaves the store warm. The draft only says "the build path matters". Add E-3.

**F3 — BLOCKING for approving E1/E2. §4, §13: the arms are undefined.** S-TREE's algorithm (a k-means tree? T-OQ's routing applied to synthetic keys? branching, leaf size, beam), the ANN kind ("clustered or graph"), the layouts (one shared file or one per arm; the draft says both "the same store bytes" and "16 GB per layout"), the key and value sizes, the page size, the workloads and patterns, the store size and the candidate budgets are all deferred. A rehearsal "against the candidate plan" (§12; ADR-0029 §19 ruling 5) is impossible without them. They need a revision 4, not a freeze-time choice.

**F4 — REQUIRED. §5 engineering label: margins.** "m_b and m_q … each at least twice the repeat-to-repeat coefficient of variation" does not fix a value ("at least"). Under F1, bytes per query is deterministic given the layout, so its CV is about 0 and m_b would be about 0. Fix exact values now, with reasons. For example, m_b = 0.10 fixed (reason: a layout difference under a tenth of the bytes is not an engineering finding), and m_q = max(0.10, 2 × CV of S-TREE's and ANN's per-repeat queries per second, measured in R1 on reduced stores). State over which quantity the CV is taken.

**F5 — REQUIRED. §5: bytes are computable before any device read.** Under F1 an arm's bytes per query is a function of its layout and candidate set. That is P7-A's arithmetic. Require the plan to register each arm's **predicted** pages per query from the in-RAM run before E2, and say in §1 that the device measures **time** and verifies bytes. Note too that if S-TREE and IVF index the same leaves, IVF's exhaustive centroid scan picks the nearest leaves exactly, so at equal recall S-TREE cannot read fewer pages by construction. The positive label is then reachable only through a structural difference the revision must name. `PENDING LEAD REVIEW`.

**F6 — REQUIRED. §3.1 EC3, §9 HEALTH COUNTERS UNREADABLE.** As written, the engineering part is NOT EVALUABLE unless `smartctl` is installed (a tool install, reserved for the human lead) or the human lead reads the counters. Readable without administrator access: SMART status "Verified", free space, and driver bytes written since boot. The planned 64 GB is 3.2 hours of the machine's ordinary writing. Proposed EC3: "SMART status Verified (`diskutil info disk0`), free space, and disk0 driver bytes written since boot are recorded before and after each write stage; lifetime counters are recorded if the human lead supplies them, and are descriptive." This changes a safety gate, not a scientific threshold, and it touches the write budget, so it is **the human lead's decision, not the delegation's**.

**F7 — REQUIRED. §5 measures: the counter API.** "The per-process disk I/O counters of the process's resource usage" can be implemented as `getrusage` (`ru_inblock` = 0 throughout the probes) or `psutil` (no `io_counters` on macOS). Name it: `proc_pid_rusage(getpid(), RUSAGE_INFO_V2)`, fields `ri_diskio_bytesread` and `ri_diskio_byteswritten`, through `ctypes` (stdlib; no new package). All registered reads happen in one process, with no child readers. Counter snapshots (`ioreg` subprocess calls take tens of milliseconds) stay outside the timed region.

**F8 — REQUIRED. Engineering stops (ADR-0029 §20 ruling 11).** §9 says the study "stops … on an I/O error" with no outcome name, and there is nothing for a code error. Add: a code error inside an item, or an environment error (I/O error, out of memory, full disk), refuses the registered analysis of that stage. The outcome is ENGINEERING STOP (named cause) and it is never recorded as NOT EVALUABLE. A drive health warning is PAUSED and goes to the human lead. Also add the precedence of NOT EVALUABLE reasons: checks are evaluated in the order listed in §9, the first failing reason is the label, and every failing reason is printed.

**F9 — REQUIRED. §4 ANN baseline and the lock.** §11 item 4 recommends a dependency amendment. That is a package outside the lock (not delegable), and as far as I know none of the obvious libraries reads through a user-supplied `F_NOCACHE` `pread` at QD1 (for example, faiss's on-disk inverted lists use memory mapping). This is not tested; no download was made. Recommend the in-project IVF-flat as the deciding ANN. Graph ANN is out of scope at this scale in Python, and §14 says so. Add the asymmetry (a positive result against an in-project IVF is weak evidence; a negative one is informative) and the SPANN note to §14.

**F10 — REQUIRED. §10 cost: S-FLAT on device.** At 16 GiB the key region is 5.33 GiB, 349,525 pages. At QD1 and 72 to 121 µs per page (descriptive) that is about 25 to 42 s **per query**. 1,000 queries × 5 repeats would be 35 to 60 hours. S-FLAT's device bytes are BY CONSTRUCTION and decide nothing (§5). So: compute the recall reference exactly in RAM, from keys loaded with `F_NOCACHE` into process memory, and time S-FLAT on device on a registered subset of 10 queries per repeat, printed only. The draft's "2 to 6 hours" holds only with this rule.

**F11 — REQUIRED. §12, §8: rehearsal order, caps, frozen inputs.** "rehearsed end to end against the frozen plan itself before Decision 2" puts the freeze before the rehearsal. Use ADR-0029 §19 ruling 5: a candidate `plan.json` is written first, rehearsed against, its SHA-256 recorded, and the freeze refuses any other hash. The charged-hour cap ("proposed 8 hours") has no rule. Use ADR-0029's rule (charged + 2 × projected remaining, set before the counting rehearsal). The store path must be outside every frozen worktree.

**F12 — REQUIRED. No memory guard.** A 16 GiB store "fully in memory" for the RAM arm, plus k-means over 5.7 GB of keys, on the human lead's 48 GiB working computer while other studies may run. Add a guard (for example, refuse to start if the projected peak exceeds a fixed figure, abort if `ri_phys_footprint` passes it), and say whether the RAM arm loads the whole store or only the rows each query needs. Recommend the latter, read with `F_NOCACHE`.

**F13 — REQUIRED. §5: KEYS RESIDENT regime.** With budget K + R, an ANN arm may hold all keys and search exactly. It then reads exactly S-FLAT's 8 value rows, so S-TREE cannot beat it on bytes. Like the S-FLAT comparison, that line is tied or lost by construction. State this beside the regime, as the draft already does for S-FLAT.

**F14 — ADVISORY. §5 value parity.** "Value parity of the SSD read within dtype tolerance": bytes read from a file must be **bit-identical**. A tolerance would hide corruption. Use SHA-256 per page.

**F15 — ADVISORY. §5 RECALL GAP.** It is flagged only when ANN's recall exceeds S-TREE's. Make it symmetric (|gap| > 0.05).

**F16 — ADVISORY. §10 seeds.** The registry (revision 3) has assigned R1 = 289001, 289011–289013, 289021, 289031 and rehearsal = 289201, 289211, 289212, 289221, 289231. Cite them in the table.

**F17 — ADVISORY. §6, §2 device facts.** Free space is now 680.0 GiB (this review). Background writes vary by two orders of magnitude (about 1 MB/s in the first review; 106 MB/s over 5 s here with pytest running). The quiet I/O figure matters more than the draft implies. Add that the probes in this review were made under a non-record interpreter.

**F18 — ADVISORY. §11 item 1.** The reason given for holding E1/E2 until R-DIAGNOSIS (the read path benchmarked may not survive) does not apply to a synthetic k-means tree that is not T-OQ. Either S-TREE is defined as T-OQ's routing (then the dependence holds), or the hold should be justified differently.

**Earlier findings (REVIEW2).**

- S5-N1: FIXED (§3.2 Q1 matches replacement Y1).
- S5-N2: FIXED, against ADR-0024's current §13. Lane L is "not specified enough to approve" and L-CAPACITY has only OMITTED values, which `grep` of ADR-0024 lines 19 and 312–321 confirms.
- S5-N3: FIXED (scientific; not re-derived).
- S5-N4: FIXED for S-FLAT; the same issue appears for ANN under KEYS RESIDENT (F13).
- S5-N5: PARTLY (F16).
- S5-N6 to S5-N10: FIXED.

### Edits for E0-only approval (exact text)

- **E-1** (header, line 3): add after the status sentence: "Approval under the delegation of 2026-11-18 can cover stage E0 (R0 and R1) only, and only together with the human lead's own approval of its 2 GB write (section 11 item 2). Stages E1 and E2 need a revision 4 that fixes the items of section 13."
- **E-2** (§7 table, row "Cold state reachable", "What R1 must show"): replace "a first read pass has cache ratio (counted bytes over logical bytes requested) at least 0.9" with "every uncached read pass has per-process device bytes read exactly equal to 16,384 × the number of distinct whole 16 KiB pages it requests (sub-page requests count their whole page)". Replace the row "Ratio upper bound" with "Exactness: per-process bytes above the predicted figure → COUNTER CONTAMINATED; below it → STORE PAGES CACHED; either makes the pass invalid". Delete "and arms whose ratios differ by more than 0.05 are not compared" and the sentence beginning "0.9, 0.1, 1.1 and 0.05 are proposals", and put in their place: "The exactness rule was chosen after the third review's probes on this machine (2026-11-18), before any registered observation. With it, no arm can benefit from cache hits." Delete "ratios 0.9, 0.1, 1.1, 0.05" from §9's threshold row, and replace CACHE RATIO NOT MATCHED in §5 and §9 with STORE PAGES CACHED.
- **E-3** (§7, new paragraph after the table): "Read discipline, from the third review's probes: stores are written only with `F_NOCACHE` set and closed with `F_FULLFSYNC`; every read of a store file by any part of the study (arms, the RAM arm, checksums, parity checks) uses `F_NOCACHE` with `F_RDAHEAD` 0 and whole 16 KiB pages at 16 KiB offsets; `F_NOCACHE` does not bypass pages already in the cache, so a store read once with caching is polluted until evicted. The positive control runs only on R1's own file. Recovery from a polluted store is a rebuild charged to the write budget, a restart, or `purge` run by the human lead."
- **E-4** (§5 Measures, first bullet): replace "Primary counter: the per-process disk I/O counters of the process's resource usage." with "Primary counter: `ri_diskio_bytesread` and `ri_diskio_byteswritten` of `proc_pid_rusage(getpid(), RUSAGE_INFO_V2)`, read through `ctypes`, in the single process that issues every registered read; not `getrusage` (its block counts stay 0 on this machine) and not `psutil` (no I/O counters on macOS)."
- **E-5** (§9, after "The study stops and returns…"): "A code error inside an item, or an environment error (I/O error, out of memory, full disk), refuses the registered analysis of its stage with the outcome ENGINEERING STOP (cause) and is never recorded as NOT EVALUABLE (ADR-0029 section 20, ruling 11). NOT EVALUABLE reasons are checked in the order of the list above; the first failing one is the label, and all failing ones are printed."
- **E-6** (§8, row R1, Notes): append "; R1 runs under the platform-of-record interpreter; the quiet check also requires `HIDIdleTime` of at least 600 s, no other ArborLM stage running, AC power and no thermal warning; R1 records disk0 driver bytes and operations over a 10-minute idle window."
- **E-7** (§12, second bullet): replace "against the frozen plan itself before Decision 2" with "against the candidate plan file itself, whose SHA-256 is recorded in the rehearsal record; the freeze refuses unless the file it commits has that hash (ADR-0029 section 19, ruling 5); the charged-hour cap is set before the counting rehearsal by ADR-0029's rule (charged + 2 × projected remaining)".

## D. Implementer's guesses (benchmark stages), with the ruling I would recommend

1. **What S-TREE is.** Recommend: hierarchical k-means (branching b, depth fixed), internal centroids in RAM, leaves as posting lists of key+value rows on device; or T-OQ's routing if the lead wants the link to ArborLM (then F18's hold applies).
2. **ANN kind.** IVF-flat in torch; number of lists chosen so its centroids fit budget R.
3. **Layouts.** One physical file per arm (its own layout), the same logical rows. KV reads the IVF file by address. Without this, arms reading the same pages in one block share device cache.
4. **Row format and page.** Key 16 × float32 (64 B), value 128 B, row 192 B, 85 rows per 16 KiB page, padding recorded; posting lists page-aligned.
5. **Workload.** Keys from a fixed Gaussian mixture; queries = stored keys plus noise. Two patterns: uniform over clusters (primary) and skewed (descriptive). Disjoint pages per repeat made by assigning clusters to repeats.
6. **Queries per repeat and the definition of QPS.** 1,000; QPS = queries / wall time of the pass including routing CPU, `perf_counter_ns`, counter snapshots outside. Latency per query printed.
7. **Counter API.** As E-4.
8. **"Logical bytes" in the ratio.** Removed by E-2 (predicted whole pages).
9. **Margins.** Fixed values (F4).
10. **Device-cache factor and the "repeat pass".** R1's growing-working-set re-read test fixes a size below which re-reads are faster. Registered repeats keep working sets above it and disjoint; "faster than its first pass" is then not needed.
11. **Recall reference and S-FLAT on device.** As F10.
12. **KV addressing.** It reads the pages holding S-FLAT's exact top-8 rows in the IVF layout.
13. **RAM arm.** Rows loaded with `F_NOCACHE` per query; bit-identical (F14).
14. **Order of the NOT EVALUABLE checks and engineering stops.** As E-5.
15. **Partial layout on PAUSE.** The build is written in checksummed 1 GiB chunks and resumes at the first chunk not verified; bytes rewritten are charged.
16. **Quiet figures.** From R1's idle window: the disk0 read and write rates and operations ceilings are fixed at the freeze at R1's idle 95th percentile; plus the E-6 conditions.
17. **Settling interval after E1.** 10 minutes idle with the driver counters below the quiet figures.
18. **Memory guard.** F12.
19. **Store location and hygiene.** A `<name>.noindex` directory outside any worktree and outside synced folders; snapshot and Spotlight checks as in (d).
20. **Operating-point selection.** Chosen on R1 or rehearsal queries from the registered candidate grid, then fixed; the registered repeats only verify recall ≥ 0.90. Otherwise the operating point is chosen on the measured queries.
21. **"Block".** One block = one repeat of every arm, arm order from that repeat's seed.
22. **Threads.** `torch.set_num_threads(1)`; one Python thread issues every read.
23. **EC3 content.** F6.
24. **KEYS RESIDENT ANN.** F13.

## E. Open choices (§11) under the delegation

| Item | Recommended option | Sound? | Take by delegation? |
|---|---|---|---|
| 1 Engineering before qualification | E0 early, hold E1/E2 for R-DIAGNOSIS | E0 early is sound; the hold's reason needs F18 | It is EC1, the human lead's own entry decision (DIRECTION §8; delegation §3: "The lead does not waive an entry criterion"). The human lead's remark "we could do a better test in my ssd not sure why not" should be put to him as the explicit question and recorded verbatim. **Not by delegation** |
| 2 Write budget, endurance | 64 GB, 0.05 % | Sound (64 GB is about 3.2 hours of the machine's own writing) | **No**: delegation §3 and §6 exclude the SSD write budget |
| 3 Administrator access and tool install | The human lead runs them | Sound. Per the probes, none is needed except lifetime counters (`smartctl`) | **No** |
| 4 Baselines | A dependency amendment | **Not sound as the default**: package outside the lock, and unclear that any library honours the read primitive | **No**; take the in-project option (F9) |
| 5 Scientific part | Leave NOT EVALUABLE | Sound | Yes |
| 6 R_min, U, ratios, 4 of 5, budget R | As drafted | R_min 0.90 and 4 of 5 sound; the ratios should be replaced (F1); U is scientific, not reviewed here | The ratios: take E-2 instead. The rest: yes |
| 7 Entry per part | — | — | **No** (human lead) |

## F. Commands run (all read-only except the three probes, which wrote 56 MiB under `experiments/_scratch/reviews3/` and deleted it)

`date -u`; `uptime`; `ps -Ao pid,etime,%cpu,rss,command`; `sw_vers`; `sysctl -n hw.memsize hw.ncpu hw.pagesize vm.pagesize hw.model machdep.cpu.brand_string kern.boottime vm.loadavg`; `sysctl vm.swapusage`; `df -k / /System/Volumes/Data`; `diskutil info /`, `diskutil info /System/Volumes/Data`, `diskutil info disk0`; `system_profiler SPNVMeDataType SPStorageDataType`; `ioreg -r -c IOBlockStorageDriver -l -w0`; `ioreg -a -r -c AppleAPFSVolume -l`; `ioreg -l -w0 | grep …`; `ioreg -c IOHIDSystem -r -d 1 -k HIDIdleTime`; `tmutil listlocalsnapshots /` and `/System/Volumes/Data`; `tmutil destinationinfo`; `tmutil isexcluded experiments/_scratch`; `diskutil apfs listSnapshots disk3s5`; `mdutil -s / /System/Volumes/Data`; `pmset -g`, `pmset -g batt`, `pmset -g therm`; `man purge`; `vm_stat`; `iostat -d -c 3 -w 2 disk0`; `which smartctl brew purge iostat fs_usage`; the three probes; the seed checker; `python3 -I` recomputations quoted in section A. No `sudo`, no install, no network, no training, no registered checkpoint or sealed value opened. `purge` was not run.

`Astra review: NOT_PERFORMED`.
