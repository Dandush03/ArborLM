# P10-I programme-wide seed registry

> **Revision 3 — 2026-11-17 (UTC), `arbor-auditor` (Claude Opus 5.5), on the coordinator's request, against the third drafts of ADR-0027 and ADR-0028 on disk (uncommitted working copies on top of `551cf24`).** Changes:
> 1. **New checker file** `seed_registry_check_r3.py` (SHA-256 `e462360420321aa284b0e4d47b106806419ab616794a5c632fee70f122c67594`), as section 4.5 item 5 requires; the Revision 2 checker `seed_registry_check.py` is unchanged (SHA-256 `b078100689211a437d59d898e5a7fb04ee03fbcc2a388288e9f5e83dbe759289`). The new file adds named data values (`NAMED_DATA`) and asserts each lies inside an allocation of its own study, as it already did for initialisation values.
> 2. **ADR-0027:** Route B's 5 draw sets and 330401–330405 confirmed; Route A's 27 stream seeds confirmed at sets d = 1..9, offsets 0..2 (270001–270803; d = 6..9 lie inside the existing range 270001–276999, nothing moved) with 330401–330403; calibration 279001/279101 with 330491/330492 and rehearsal 279201 with 330495 confirmed for both routes. Shared values between the routes: safe because one entry runs one route; held alternatives for Route A if both are ever entered (section 4.7).
> 3. **ADR-0028:** engineering-part values confirmed as drafted (280001–280010, 280101–280103, 280201–280205, 280301–280303); R1 (6) and rehearsal (5) values, which the draft gives as counts only, assigned: R1 289001, 289011–289013, 289021, 289031; rehearsal 289201, 289211, 289212, 289221, 289231. Initialisation 3305xx unused unless the scientific part is entered.
> 4. Checker re-run: **RESULT: PASS** (56 allocations, 0 problems; 117 named initialisation and 97 named data values inside their studies; the drafts' new values show 0 collisions; 4 declared re-uses as in Revision 2). A planted named value outside its study (279999 under ADR-0028) made the new check fail. Nothing was moved away from a draft's proposal.

> **Revision 2 — 2026-11-17 (UTC), `arbor-auditor` (Claude Opus 5.5), on the coordinator's request, against the third drafts of ADR-0023, 0024, 0025, 0026 and 0029 on disk (ADR-0023 and ADR-0025 at `70f0793`; ADR-0024 and ADR-0029 as read on disk, since committed as `551cf24`).** Changes:
> 1. **Declared re-uses** are now a separate category (section 4.6) and the checker treats them explicitly (new section [7]: each re-used value must be a seed already in the inventory and must lie in no P10-I allocation; it is never counted as a collision). Entered: ADR-0023's identity gate, part (a), re-uses P10-S0's rehearsal set (base 209101, initialisation 2092) read-only; ADR-0029's stage A1 reproduction re-uses P10-S1's five registered draws and index seeds, and its adapter identity gate re-uses P10-S1's draw 1 with initialisation 2101.
> 2. **ADR-0025:** disjoint-draw permutation seeds 250916 (A's pool) and 250917 (B's pool) and Part Q rehearsal partition-side seeds 252901–252914 are **confirmed** as proposed. The rehearsal range is split so the two cannot meet: Part T rehearsal sets 252001–252899 (i = 0 only is used), Part Q rehearsal partition side 252901–252999.
> 3. **ADR-0024:** block X now runs on **fresh** draws. Draw sets 240501, 240601, 240701, 240801, 240901 and initialisation 330121–330125 are **confirmed** as proposed; block M keeps 240001–240499. Lane L entries (247001–247999, 330111–330115) are **PENDING**: whether lane L has data of its own is decided in ADR-0024's lane L revision, not here (this resolves the disagreement the reviewers found with revision 1's wording).
> 4. **ADR-0029:** every role of the third draft is assigned (bridge sets 290001–290401 in block 290001–299999, initialisation 330601–330605, I64 index seeds 298001–298003, rehearsal 299201 with 330692, test mode 330698/330699, tests 938001–938999). P10-S1's code whitelists 210001–219999 (`studies/p10s1/core.py:820`, `SEED_RANGE`), so the bridge runs through new adapter code, as the draft now states.
> 5. **ADR-0027 and ADR-0028** rows are unchanged; their roles are marked "to be stated by the drafts" (both are being revised).
> 6. The checker was re-run: **RESULT: PASS** (56 allocations, 0 problems; 4 declared re-uses, all found in the inventory, none inside an allocation). Revision 1's text and its attempt history are kept below; section 6 now shows the Revision 2 output. Nothing was moved away from a draft's proposal in this revision. The checker was edited in place on the coordinator's instruction, against section 4.5 item 5's "not edited after it is cited"; Revision 1's checker is identified by its SHA-256 in section 6, and later revisions should go to a new file.

**Standing.** This registry assigns seed values to the P10-I draft specifications ADR-0023 to ADR-0029, which are **DRAFTS, NOT APPROVED**. It revises no earlier study: no seed, record, code path or outcome of P1 to P10 (P10-S0, P10-S1, P10-S2 included) changes. It is not Astra validation and not human approval. `Astra review: NOT_PERFORMED`.

- **Author:** the `arbor-auditor` subagent, model Claude Opus 5.5 (`claude-opus-5-5`), launched by the lead's workflow on 2026-11-17. The auditor did not write any of the drafts or any earlier study code it inventories.
- **Repository state read:** worktree `arborlm-consolidation-experiment-2b31c1`, branch `claude/p10-i-specs`, HEAD `fd86a0b` (the drafts as revised after the independent reviews, ADR-0029 included). The task brief was written against `c525898`; ADR-0024 changed in between (its Lane R moved to the new draft ADR-0029, and its initialisation, calibration, rehearsal and test seeds now defer to this registry). The allocation below follows `fd86a0b`.
- **Files:** this file and `seed_registry_check.py` beside it (standard library only; it reads the repository and edits nothing). Nothing else was written. No training, no network, no git write.

## 1. Purpose

Six P10-I drafts proposed seed ranges independently. Two independent reviews found that some proposed initialisation seeds equal seeds that earlier studies **derive** (an initialisation seed s also seeds generators at s + 1000·k). This registry (a) lists every seed P1 to P10 used or reserved, literal and derived, rebuilt from the code and configs; (b) assigns one collision-free scheme to every P10-I study; (c) states the rule a later study follows; (d) provides a checker that asserts (b) against (a), and that a study's G9 gate can re-run before its freeze.

## 2. Derivation rules considered

| Rule | What it produces | Where the code uses it | How the checker applies it |
|---|---|---|---|
| R1 identity | the seed itself | everywhere | every value, both sides |
| R2 `s + 1000·k` | generator seeds of model components | `src/arborlm/pilot_model.py:110-124` (k = 1..5, P1, P2, P4, P5, P8 through `Memory`), `src/arborlm/p4_model.py:75-76` (DenseAdapter +3000, +4000), `studies/p9/model.py:272-279,486-487` (k = 1..5; used by P9-II, P10-S0, P10-S1), `studies/p9i/model.py:98-102,154-155` (k up to 8), `studies/p10s1/model.py:202-204`, `studies/p10s1/core.py:819` (`DERIVED_INIT_OFFSETS`), `src/arborlm/p7a_study.py:823`, `src/arborlm/p7b_budget.py:97` (synthetic trace +1000) | k = 1..**10** (margin over the widest use, 8). Applied to every initialisation-role value on both sides, to the rehearsal- and test-derived initialisation seeds of P9 and P9-I, and conservatively to every inventory literal below 100,000 (all P1 to P8 seeds and small constants) |
| R3 `s·1000 + index` | count-preserving null generators | `src/arborlm/p7a_core.py:351-353` (P7-A), `src/arborlm/p7b_core.py:439-444`, `src/arborlm/p8_core.py:123`, `src/arborlm/p8_sim.py:12`, `studies/p9/sim.py:326` | index 0..999 (the widest bound that keeps the rule injective; the code's indices are 0..80 for P7, 0..59 for P8, 0..99 for P9, `studies/p9/core.py:192`). Applied to every value ≥ 1,000 on both sides, which is a superset of the null seeds the code feeds it |
| In-set offsets | data, null, target, stream, swap, H8, mask, index seeds | `studies/p9/core.py:839-855` (+0..13, +20..22, +30..32; `Random(templates_seed + 1)` at `studies/p9/data.py:390`), `studies/p9ii/core.py:396-452` (+14..19, +40/41, +60/61), `studies/p10s0/core.py:426-471` (+0..19 at 0/20/60, +40..49, +50..52), `studies/p10s1/core.py:817-877` (+40, +50..59, +60), `configs/p10s2_transfer.toml:150-166` (+0..10) | enumerated per study in the inventory; for P10-I every allocation is a whole sub-range, so any in-set offset below 100 stays inside it |
| Data-derived initialisation | `init = rehearsal facts seed + (cell seed − first init seed)` | P9 (`configs/p9_diagnostics.toml:216`, c19) and P9-I (`studies/p9i/core.py:392-398`) outside registered runs | the resulting seeds (179001+100k+j, 188001+j, 900001+100k+j) are inventoried as initialisation seeds and expanded by R2 |
| Fixed-offset permutations | `20000/30000/40000/50000/60000/70000/80000 + index`, `9000 + pair`, `7000 + index`, `8000 + 10b + o`, `9001/10001 + seed` | P2, P4, P5, P8, P6, P1 diagnostic | enumerated |
| Hash derivation | 62-bit SHA-256 seeds | `studies/p9/data.py:69`, `studies/p9ii/core.py:863`, `studies/p10s0/core.py:690`, `studies/p10s1/core.py:1330` | not enumerable (see unknowns) |

Informational (not binding) checks in the checker: **W1**, R2 applied to *every* value of every role on both sides (a rule no code applies to data seeds); **W2**, R3 applied also to values below 1,000; **W3**, a scan for six-digit literals inside the P10-I allocations.

## 3. Part 1 — inventory of seeds used or reserved by P1 to P10

Generated by `seed_registry_check.py --tables` (constants read with `ast`, file and line from the code; nothing imported for this table). "R2 applies: yes" marks initialisation seeds; "yes (< 100000)" marks the conservative application to small literals. Rows 1 to 12, 61 and 62 are deliberate catch-alls that duplicate specific rows. Where a value list is long it is abbreviated (first values … last values, total count); the checker holds every value.

| # | Study | Role | Literal values / range | Rule (in-set derivation) | R2 applies | Source |
|---|---|---|---|---|---|---|
| 1 | E0 | config literal | 42, 101, 202 (3 values) | every integer under a key containing 'seed' (strides and offsets included, conservative) | yes (< 100000) | configs/e0_cpu_smoke.toml |
| 2 | P10S0 | config literal | 0, 20, 40, 44, …, 920001, 920999 (22 values) | every integer under a key containing 'seed' (strides and offsets included, conservative) | yes (< 100000) | configs/p10s0_qualification.toml |
| 3 | P10S1 | config literal | 40, 60, 100, 2111–2112, …, 921001, 921999 (16 values) | every integer under a key containing 'seed' (strides and offsets included, conservative) | yes (< 100000) | configs/p10s1_capacity.toml |
| 4 | P10S2 | config literal | 0–10, 100, 220001, 220101, …, 229001, 229999 (35 values) | every integer under a key containing 'seed' (strides and offsets included, conservative) | yes (< 100000) | configs/p10s2_transfer.toml |
| 5 | P1 | config literal | 42–44, 1000, 2000, 3000, 4000, 5000 (8 values) | every integer under a key containing 'seed' (strides and offsets included, conservative) | yes (< 100000) | configs/p1_ram_screen.toml |
| 6 | P2 | config literal | 101–103, 201–203, 301–303, 20000, 30000 (11 values) | every integer under a key containing 'seed' (strides and offsets included, conservative) | yes (< 100000) | configs/p2_optimization_followup.toml |
| 7 | P4 | config literal | 0, 401–403, 1000, 2000, …, 40000, 50000 (11 values) | every integer under a key containing 'seed' (strides and offsets included, conservative) | yes (< 100000) | configs/p4_frozen_capacity.toml |
| 8 | P5 | config literal | 0, 501–503, 1000, 2000, …, 60000, 70000 (11 values) | every integer under a key containing 'seed' (strides and offsets included, conservative) | yes (< 100000) | configs/p5_hierarchy_ablation.toml |
| 9 | P8 | config literal | 601–602, 80000, 91201, 91331–91333, 91341–91343, 91601–91605 (15 values) | every integer under a key containing 'seed' (strides and offsets included, conservative) | yes (< 100000) | configs/p8_locality_training.toml |
| 10 | P9 | config literal | 101–102, 301–302, 1701–1702, 170001, …, 171341–171343, 179001 (27 values) | every integer under a key containing 'seed' (strides and offsets included, conservative) | yes (< 100000) | configs/p9_diagnostics.toml |
| 11 | P9I | config literal | 1791–1792, 1801–1802, 182001, 900001 (6 values) | every integer under a key containing 'seed' (strides and offsets included, conservative) | yes (< 100000) | configs/p9i_interface.toml |
| 12 | P9II | config literal | 3–5, 40, 60, 100, …, 910001, 919999 (14 values) | every integer under a key containing 'seed' (strides and offsets included, conservative) | yes (< 100000) | configs/p9ii_addressing.toml |
| 13 | P1 | initialization | 42–44 (3 values) | torch/python seed; Memory(variant, seed) draws seed+1000..+5000 | yes | src/arborlm/pilot_config.py:22 |
| 14 | P1 | initialization (derived) | 1042–1044, 2042–2044, 3042–3044, 4042–4044, 5042–5044 (15 values) | seed + 1000k, k=1..5 (keys, values, wq, wo, router) | yes (< 100000) | src/arborlm/pilot_model.py:110 |
| 15 | P1 diagnostic | permutation | 9043–9045, 10043–10045 (6 values) | 9001 + seed, 10001 + seed | yes (< 100000) | src/arborlm/diagnose_memory.py:324 |
| 16 | E0 | initialization | 42 | torch.manual_seed(42) (engine.py); E0 torch/python seed 42 | yes | src/arborlm/engine.py:27 |
| 17 | misc | literal | 0–1, 12 (3 values) | Random(0) state restore, Random(1) (p7b_budget), Generator(0), Generator(12) (p10s0 synthetic) | yes (< 100000) | studies/p10s0/synthetic.py:185 |
| 18 | P2/P3 | initialization | 101–103, 201–203 (6 values) | backbone (default generator) and memory seeds; Memory draws seed+1000..+5000 | yes | configs/p2_optimization_followup.toml:5 |
| 19 | P2/P3 | data (order) | 301–303 (3 values) | batch-order seeds | yes (< 100000) | configs/p2_optimization_followup.toml:7 |
| 20 | P2/P3 | permutation | 20000–20026, 30000–30026 (54 values) | 20000 + cell index, 30000 + cell index; index = 9(b-101)+3(o-301)+(m-201) in 0..26 | yes (< 100000) | src/arborlm/p2_model.py:46 |
| 21 | P4 | initialization | 0, 401–403 (4 values) | Memory seed+1000..+5000; DenseAdapter seed+3000, +4000; baseline 0 | yes | src/arborlm/p4_config.py:21 |
| 22 | P4 | permutation | 40000–40026, 50000–50026 (54 values) | 40000 + index, 50000 + index (index 0..26) | yes (< 100000) | src/arborlm/p4_model.py:266 |
| 23 | P5 | initialization | 0, 501–503 (4 values) | as P4 | yes | src/arborlm/p5_config.py:23 |
| 24 | P5 | permutation | 60000–60026, 70000–70026 (54 values) | 60000 + index, 70000 + index (index 0..26) | yes (< 100000) | src/arborlm/p5_model.py:258 |
| 25 | P6 | permutation | 9000–9026 (27 values) | 9000 + pair_index (P5 cell index 0..26) | yes (< 100000) | src/arborlm/p6_common.py:196 |
| 26 | P6 | test | 91001 | constructed-tie fixture seed | yes (< 100000) | src/arborlm/p6_equivalence.py:48 |
| 27 | P7-A | permutation/panel | 91101–91103, 91201–91202, 91301–91303, 91401, 91501 (10 values) | named constants; null generator replicate_seed*1000 + cell index (rule R3) | yes (< 100000) | src/arborlm/p7a_core.py:44 |
| 28 | P7-B | permutation/panel | 91311–91313, 91321–91323, 91601–91605 (11 values) | named constants; null generator s*1000 + cell index (rule R3) | yes (< 100000) | src/arborlm/p7b_core.py:70 |
| 29 | P7-A/P7-B | test (budget) | 7001–7002, 8001–8002 (4 values) | synthetic_trace seeds 7001, 7002 and seed + 1000 | yes (< 100000) | src/arborlm/p7a_study.py:823; src/arborlm/p7b_budget.py:97 |
| 30 | P8 | initialization | 601–602 (2 values) | Memory(variant, seed) via P5 Model: seed+1000..+5000 | yes | src/arborlm/p8_core.py:88 |
| 31 | P8 | panel/permutation | 91201, 91331–91333, 91341–91343, 91601–91605 (12 values) | partition, panel null (s*1000 + cell index, rule R3) and order-shuffle seeds | yes (< 100000) | src/arborlm/p8_core.py:119 |
| 32 | P8 | permutation | 7000–7059, 9311–9313, 9321–9323, 9331–9333, 80000–80059 (129 values) | 80000 + index; 7000 + index (index 0..59); 8000 + 10*backbone + order | yes (< 100000) | src/arborlm/p8_core.py:113; src/arborlm/p8_eval.py:285; src/arborlm/p8_core.py:533 |
| 33 | P9 | data (registered) | 170001, 170011–170012, 170031, 170041, …, 171331–171333, 171341–171343 (21 values) | named data seeds; templates_seed + 1; null seeds | no | studies/p9/core.py:131 |
| 34 | P9 | initialization | 1701–1702 (2 values) | studies/p9/model.py: seed+1000..+5000 | yes | studies/p9/core.py:149 |
| 35 | P9 (+P9-I, P9-II) | rehearsal/calibration/DRY | 179001–179014, 179021–179023, 179031–179033, 179101–179114, …, 188021–188023, 188031–188033 (220 values) | draw k: 179001 + 100k + (0..13, 20..22, 30..32); k = 0..9 and DRY draw 90; code bound: any k >= 0 (see unknowns) | no | studies/p9/core.py:151; studies/p9/stages.py:74 |
| 36 | P9 rehearsal (as reserved by P9-II) | rehearsal (target, stream) | 179041–179042, 179061–179062, 179141–179142, 179161–179162, …, 179941–179942, 179961–179962 (40 values) | P9-II seed_values adds target +40/+41 and stream +60/+61 to every P9 rehearsal draw 0..9 | no | studies/p9ii/core.py:392 |
| 37 | P9 (+P9-I) | initialization (rehearsal-derived) | 179001–179002, 179101–179102, 179201–179202, 179301–179302, …, 179901–179902, 188001–188002 (22 values) | rehearsal init = rehearsal facts seed + (cell seed - first init seed), j = 0, 1; then +1000k | yes | studies/p9i/core.py:397 |
| 38 | P9-I | data (registered) | 182001–182020 (20 values) | base + 0..13 data, +14..16 / +17..19 nulls | no | studies/p9i/core.py:95 |
| 39 | P9-I | initialization | 1791–1792, 1801–1802 (4 values) | studies/p9i/model.py: seed+1000..+8000 (attention arms use +6000..+8000) | yes | studies/p9i/core.py:94; studies/p9i/core.py:93 |
| 40 | P9-I | test | 900001–900014, 900021–900023, 900031–900033, 900101–900114, …, 900221–900223, 900231–900233 (60 values) | base + 100k, k = 0..2, P9 rehearsal layout | no | studies/p9i/core.py:96 |
| 41 | P9-I | initialization (test-derived) | 900001–900002, 900101–900102, 900201–900202 (6 values) | test sets may run in rehearsal mode: init = facts + j; then +1000..+8000 | yes | studies/p9i/core.py:96 |
| 42 | P9-II | data (registered + reserve) | 190001–190020, 190041–190042, 190061–190062, 190101–190120, …, 191541–191542, 191561–191562 (384 values) | draws 1..14 at 190001 + 100(d-1), reserves [191401, 191501]; +0..19, +40/41, +60/61 | no | studies/p9ii/core.py:383 |
| 43 | P9-II | calibration/rehearsal (target, stream) | 179341–179342, 179361–179362, 179441–179442, 179461–179462, 179541–179542, 179561–179562 (12 values) | P9 rehearsal sets 3, 4, 5 plus target/stream offsets | no | studies/p9ii/core.py:383 |
| 44 | P9-II | initialization | 1891–1892, 1901–1902 (4 values) | 1901 + j; calibration 1891 + j; P9 model +1000..+5000 | yes | studies/p9ii/core.py:125; studies/p9ii/core.py:94 |
| 45 | P9-II | test | 910001–919999 (9999 values) | declared test range (whole) | no | studies/p9ii/core.py:389 |
| 46 | P10-S0 | data (registered, reserve, check, rehearsal) | 200001–200042, 200045–200046, 200049–200053, 200061–200080, …, 209149–209153, 209161–209180 (1173 values) | set base + fact-set offset [0, 20, 60] + 0..19; target +[40, 44, 48]+j; swap +[50, 51, 52] | no | studies/p10s0/core.py:421 |
| 47 | P10-S0 | declared namespace | 200001–209999 (9999 values) | S0_RANGE (whole, reserved) | no | studies/p10s0/core.py:429 |
| 48 | P10-S0 | initialization | 2001–2002, 2091–2092 (4 values) | P9 model via P9-II: seed+1000..+5000 | yes | studies/p10s0/core.py:144; studies/p10s0/core.py:145 |
| 49 | P10-S0 | test | 920001–920999 (999 values) | declared test range (whole) | no | studies/p10s0/core.py:425 |
| 50 | P10-S1 | data (registered, calibration, rehearsal) | 210001–210014, 210021–210023, 210031–210033, 210041, …, 219241, 219251–219261 (256 values) | set base + 0..13, +20..22, +30..32, +40, +50..59, +60 | no | studies/p10s1/core.py:812 |
| 51 | P10-S1 | declared namespace | 210001–219999 (9999 values) | SEED_RANGE (whole, reserved) | no | studies/p10s1/core.py:820 |
| 52 | P10-S1 | initialization | 2101–2105, 2111–2112, 2121–2122, 2191–2193 (12 values) | 2100 + r; seed block 21<extra><draw>; 2191-2193; DERIVED_INIT_OFFSETS +1000..+5000 | yes | studies/p10s1/core.py:486; studies/p10s1/core.py:490 |
| 53 | P10-S1 | test | 921001–921999 (999 values) | declared test range (whole) | no | studies/p10s1/core.py:816 |
| 54 | P10-S2 | data (registered + partition side) | 220001–220011, 220101–220111, 220201–220211, 220301–220311, 220901–220912 (56 values) | replicate base + offsets 0..10; partition 220901 and streams 220902..220912 | no | configs/p10s2_transfer.toml:150 |
| 55 | P10-S2 | calibration | 221001–221011, 221101–221111, 221201–221211, 221301–221311, …, 221801–221811, 221901–221911 (110 values) | 221001 + 100i + offset, i < draw_count | no | configs/p10s2_transfer.toml:150 |
| 56 | P10-S2 | rehearsal | 222001–222011, 222101–222111, 222201–222211, 222301–222311, …, 222801–222811, 222901–222911 (110 values) | 222001 + 100i + offset, i < draw_count | no | configs/p10s2_transfer.toml:150 |
| 57 | P10-S2 | declared namespace | 220001–228999, 229001–229999 (9998 values) | registered, calibration, rehearsal, test ranges (whole) | no | configs/p10s2_transfer.toml:150 |
| 58 | P10-S2 | test (stand-ins) | 1–6 (6 values) | standins data_seed_offset (default 0) + 1..6 | yes (< 100000) | studies/p10s2/standins.py:20 |
| 59 | Review diagnostics | initialization | 500001–500004 (4 values) | init seeds of the ADR-0019 design review scripts (c7 uses +1000..+4000) | yes | studies/p10s1/core.py:888 |
| 60 | Review diagnostics | unknown role | 941001 | listed by P10-S1/P10-S2 G9; origin not found in the repository | yes | studies/p10s1/core.py:888 |
| 61 | P9/P9-I/P9-II (as listed by P10 G9) | declared namespace | 170001–171343, 179001–179933, 180101–181900, 182001–182020, 190001–191599, 900001–900233 (5928 values) | OTHER_STUDY_RANGES of P10-S1 | no | studies/p10s1/core.py:885 |
| 62 | All code and tests | literal scan | 0–9, 11–13, 19, 21, …, 920001, 987654 (71 values) | integer literal right after manual_seed(, Random(, seed=, seeds=( (regex) | yes (< 100000) | 71 literals in src/arborlm, studies, tests |

Notes on bounds taken:

- **P9 rehearsal draws** (row 35): `studies/p9/core.py:842` accepts any draw ≥ 0, so the code's widest bound is unbounded (see unknowns). The inventory takes draws 0..9 (P9-I's `REHEARSAL_MAX_DRAW = 9`, P9-II's `P9_REHEARSAL_DRAWS = range(10)`) and the DRY draw 90 (`studies/p9/stages.py:74`).
- **Declared ranges are reserved whole** (rows 45, 47, 49, 51, 53, 57, 61): P9-II tests 910001–919999, P10-S0 200001–209999 and 920001–920999, P10-S1 210001–219999 and 921001–921999, P10-S2 220001–229999, and the P9/P9-I/P9-II ranges listed by P10-S1's G9.
- **P2 backbone seeds 101–103** are marked as initialisation seeds although no code adds 1000·k to them (they seed the default generator only); this is conservative.
- **Reserved for later studies, not used:** `studies/p9ii/core.py:391` `RESERVED_LATER = ((200001, 229999), (920001, 929999))`. P10-I's test ranges are placed in 932001–938999, outside it, for the reason in section 4.4.
- **ADR-only seeds:** ADR-0010 to ADR-0022 name no seed that is absent from the code and configs (scan of every number within 80 characters after "seed"; the hits were seeds already listed, dates, sizes or run identifiers).

Overlaps found **among earlier studies** (informational; computed with the rules the code actually applies, R2 at k ≤ 5, k ≤ 8 for P9-I; nothing is revised):

| Values | Seed A | Seed B |
|---|---|---|
| 182001, 182002 | P9-I rehearsal draw 0 initialisation 179001/179002 + 3000 (`wq`) | P9-I registered data seeds (facts, templates) |
| 190001, 190002 and 191001, 191002 | P9 DRY draw 90 initialisation 188001/188002 + 2000 (values) and + 3000 (`wq`) | P9-II registered draws 1 and 11 (facts, templates) |
| 7001, 7002 | P8 `7000 + cell index` (`src/arborlm/p8_eval.py:285`) | P7-A/P7-B budget synthetic-trace seeds; also P10-S0 initialisation 2001/2002 + 5000 (router generator, tree arms only) |
| 91201; 91601–91605 | P7-A order shuffle; P7-B partitions | P8, deliberate reuse (`src/arborlm/p8_core.py:119-122`) |

Whether the first three ran in a recorded run (which arm, which draw) was not checked against the records. **PENDING LEAD REVIEW** whether they deserve a note in those studies' records.

## 4. Part 2 — allocation for P10-I

### 4.1 Zones

| Zone | Values | Use |
|---|---|---|
| Data blocks | one 10,000-wide block per study, `X0001–X9999` | data, permutation, calibration and rehearsal seeds of that study only |
| P10-I initialisation row | **330001–330999** | every P10-I initialisation seed; one sub-row of 99 per study at 330001 + 100·i |
| Derivation reserve of that row | 331000–340999 | never allocated: holds `s + 1000·k`, k = 1..10, of every value in the row |
| P10-I test ranges | 932001–938999 | unit tests and DRY profiles, 999 per study |

Why one row: every initialisation value is in 330001–330999 and every R2 image is in 331001–340999, so no initialisation value can equal another's derived seed; two values of the row have equal R2 images only if they are equal (s + 1000k = s' + 1000k' forces s ≡ s' mod 1000); and R3 images (`s·1000 + i`, 330,001,000–330,999,999) are pairwise disjoint and far from everything. The row sits 20,000 above the highest P10-I data block, so even W1 (R2 applied to data seeds) cannot reach it from a P10-I data block.

### 4.2 Allocation table

Values are inclusive. "Used" counts what the draft needs; the rest of each range is headroom. Within a data block the study's own in-set layout applies (sets of 100 at base + 100·(d − 1); every in-set offset below 100).

| Study (draft) | Role | Range | Named values / layout | Used | Spare |
|---|---|---|---|---|---|
| **P10-I-S0 (ADR-0023)** | registered + reserve draw sets | 300001–306999 | draws 1–10 at 300001 + 100(d−1); reserves 1–4 at 301001, 301101, 301201, 301301; P10-S0 in-set layout | 14 sets | 56 sets |
| | permutation / controls / bootstrap | 307001–308999 | none needed by the draft | 0 | 1,999 |
| | calibration draw sets | 309001–309199 | 309001, 309101 | 2 sets | 0 (use the spare below) |
| | rehearsal draw set | 309201–309299 | 309201 | 1 set | 0 |
| | pipeline-check set | 309301–309399 | 309301 | 1 set | 0 |
| | spare | 309401–309999 | — | 0 | 599 |
| | initialisation | 330001–330099 | registered 330001 (odd draws; A6 on every draw), 330002 (even draws); calibration 330091 (draw 1), 330093 (draw 2); rehearsal and pipeline check 330092; test mode 330098, 330099 | 7 | 92 |
| | test | 932001–932999 | — | — | 999 |
| **P10-I-S1 (ADR-0024)** | block M registered draw sets | 240001–240499 | 240001, 240101, 240201, 240301, 240401 (as drafted); P10-S1 in-set layout | 5 sets | 0 |
| | block X fresh draw sets (Revision 2) | 240501–240999 | 240501, 240601, 240701, 240801, 240901 (as proposed by draft 3); fact tables of 131,072 facts; P10-S1 in-set layout | 5 sets | 0 |
| | spare draw sets | 241001–246999 | — | 0 | 60 sets |
| | lane L data sets — **PENDING** | 247001–247999 | held only. Whether lane L has data of its own (here, in ADR-0023's in-set layout, never mixed with P10-S1's layout in one set) or uses this study's draws is decided in ADR-0024's lane L revision | 0 until decided | 10 sets |
| | spare (was Lane R's index range in draft 1) | 248001–248999 | — | 0 | 999 |
| | calibration draw sets | 249001–249199 | 249001, 249101 (as drafted) | 2 sets | 0 |
| | rehearsal draw set | 249201–249299 | 249201 (as drafted) | 1 set | 0 |
| | spare | 249301–249999 | — | 0 | 699 |
| | initialisation | 330101–330199 | block M replicate r → 330100 + r (330101–330105); block X fresh draw r → 330120 + r (330121–330125, as proposed); lane L **PENDING** 330110 + r (330111–330115, held); calibration 330191 (draw 1), 330193 (draw 2); rehearsal 330192; test mode 330198, 330199 | 15 (+5 held) | 79 |
| | test | 933001–933999 | moved from draft 1's 924001–924999 (section 4.4) | — | 999 |
| **P10-I-S2 (ADR-0025)** | registered replicate sets | 250001–250899 | bases 250001, 250101, 250201 with the draft's offsets (+1, +2, +4, +10, +13) | 3 sets | 6 sets |
| | partition side, analysis, disjoint draws | 250901–250999 | 250901–250914 partition side, 250915 bootstrap; 250916 permutation of A's accepted pool, 250917 of B's (Revision 2, as proposed) | 17 | 82 |
| | calibration | 251001–251999 | 251001 + 100·i, same offsets (as drafted) | i = 0, 1 | 8 sets |
| | Part T rehearsal sets | 252001–252899 | 252001 + 100·i, same offsets; the draft uses i = 0 only | 1 set | 8 sets |
| | Part Q rehearsal partition side (Revision 2) | 252901–252999 | 252901–252914, mirroring 250901–250914 (as proposed) | 14 | 85 |
| | spare | 253001–259999 | the draft-1 test range 259001–259999 is released | 0 | 6,999 |
| | initialisation | 330201–330299 | role j = 0 stage-1 store, 1 appended rows, 2 M-joint store, 3 D1, 4 second adapter of D-append, 5 D-joint, 6 E-table, 7 router projection and keys. Registered replicate r (0..2): 330201 + 10r + j (330201–330228). Calibration draw i (0, 1): 330231 + 10i + j (330231–330248). Rehearsal draw 0: 330251 + j (330251–330258). Test mode 330298, 330299 | 50 | 49 (330261–330297 takes four more draws of 8) |
| | test | 934001–934999 | — | — | 999 |
| **P10-I-S3 (ADR-0026)** | registered streams and permutations | 260001–266999 | cell c = 9(B−101) + 3(O−301) + seed position (0..26), regime g (0..2), draw j (0..3): stream 260001 + 3c + g (260001–260081); P_all 260101 + c (260101–260127); P_used 260201 + 4c + j (260201–260308); X 260401 + 4c + j (260401–260508) | 324 | 6,675 |
| | spare | 267001–268999 | — | 0 | 1,999 |
| | calibration streams and permutations | 269001–269199 | calibration cell c (0..2): stream 269001 + 3c + g (269001–269009); P_all 269021 + c; P_used 269031 + 4c + j (269031–269042); X 269051 + 4c + j (269051–269062) | 36 | 163 |
| | dry-rehearsal streams and permutations | 269201–269299 | stream 269201 + g (269201–269203); P_all 269221; P_used 269231–269234; X 269251–269254 | 12 | 87 |
| | spare | 269301–269999 | — | 0 | 699 |
| | initialisation | 330301–330399 | registered 330301, 330302, 330303 (seed positions 0, 1, 2); calibration 330391; dry rehearsal 330392; test mode 330398, 330399 | 7 | 92 |
| | test | 935001–935999 | moved from 926001–926999 (section 4.4) | — | 999 |
| **P10-I-S4 (ADR-0027, conditional; Revision 3)** | registered data | 270001–276999 | **Route B:** draw sets 270001 + 100(d−1), d = 1..5 (ADR-0024 layout). **Route A:** 27 stream-permutation seeds 270001 + 100(d−1) + (s−1), set d = parent 1..9, s = 1..3 (270001–270003 … 270801–270803; d = 6..9 confirmed inside this range). One entry runs one route (section 4.7) | 5 sets or 27 seeds | 61 sets |
| | auxiliary | 277001–278999 | — | 0 | 1,999 |
| | calibration | 279001–279199 | Route B sets 279001, 279101; Route A calibration stream seeds 279001, 279101 (same values; one route per entry) | 2 | 0 |
| | rehearsal | 279201–279299 | Route B set 279201; Route A rehearsal stream seed 279201 | 1 | 0 |
| | spare | 279301–279999 | held for Route A only if both routes are ever entered: calibration streams 279301, 279401; rehearsal stream 279501 | 0 | 699 |
| | initialisation | 330401–330499 | Route B registered 330401–330405 (one per draw); Route A registered 330401–330403 (one per seed position, all parents); calibration 330491, 330492; rehearsal 330495; test mode 330498, 330499 (both routes). Held for Route A only if both routes are ever entered: 330411–330413, 330481, 330482, 330485 | 10 (+6 held) | 83 |
| | test | 936001–936999 | — | — | 999 |
| **P10-I-S5 (ADR-0028, conditional; Revision 3)** | registered, engineering part | 280001–286999 | query workloads 280001–280010 (2 patterns × 5 repeats); store contents 280101–280103 (one per store size); arm order 280201–280205 (one per repeat); ANN index build 280301–280303 (one per store size); all as drafted | 21 | 6,978 |
| | auxiliary | 287001–288999 | — | 0 | 1,999 |
| | R1 | 289001–289199 | store contents 289001; workloads 289011, 289012 (two patterns), 289013 (positive control); arm order 289021; ANN build 289031 (values assigned by the registry; the draft states counts only) | 6 | 193 |
| | rehearsal | 289201–289299 | store contents 289201; workloads 289211, 289212; arm order 289221; ANN build 289231 (values assigned by the registry) | 5 | 94 |
| | spare | 289301–289999 | — | 0 | 699 |
| | initialisation | 330501–330599 | **unused** unless the scientific part is entered (not laid out): held 330501–330505, 330591, 330592; test mode 330598, 330599 | 0 (+9 held) | 90 |
| | test | 937001–937999 | — | — | 999 |
| **P10-I-R (ADR-0029)** | bridge draw sets | 290001–296999 | 290001 + 100(d−1), d = 1..5, complete P10-S1-style draws (P10-S1 in-set layout, index seed at base + 60), run through **new adapter code** because `studies/p10s1/core.py:820` whitelists 210001–219999 | 5 sets | 65 sets |
| | spare | 297001–297999 | — | 0 | 999 |
| | I64 index seeds | 298001–298999 | 298001, 298002, 298003 | 3 | 996 |
| | calibration (held; the draft needs none) | 299001–299199 | — | 0 | 199 |
| | rehearsal draw set | 299201–299299 | 299201 | 1 set | 0 |
| | spare | 299301–299999 | — | 0 | 699 |
| | initialisation | 330601–330699 | bridge 330601–330605 (draw d → 330600 + d); rehearsal 330692; test mode 330698, 330699 | 8 | 91 |
| | test | 938001–938999 | — | — | 999 |
| | declared re-uses (not allocations; section 4.6) | P10-S1's five registered draws (210001–210499) with index seeds (base + 60); P10-S1 draw 1 with initialisation 2101 | stage A1 reproduction reads; adapter identity gate | — | — |
| **P10-I spare** | initialisation sub-rows for supplements | 330701–330999 | — | 0 | 299 |

The draft data blocks 240001–249999, 250001–259999, 260001–269999, 270001–279999, 280001–289999 and 300001–309999 were clean under R1 to R3 and are kept. ADR-0029 is new and takes the next free block, 290001–299999. Every initialisation seed the drafts proposed (2401–2405, 2491–2493, 2601–2699, 2701–2799, 3001–3092) is replaced by the row.

### 4.3 Conditions attached to the allocation

1. **No arithmetic derivation from data, permutation, calibration, rehearsal or test seeds** other than in-set offsets below 100 inside the study's own set. In particular the P9 / P9-I rule "initialisation = rehearsal facts seed + offset" is not used; rehearsal, DRY and test modes take the named test-mode initialisation seeds. (Under W1 the adjacent 10,000-blocks reach each other, because block X + 10,000 is the next block; the condition is what keeps them apart.)
2. **ADR-0025** keeps P10-S2's rule that every generator is seeded directly by a listed seed; its initialisation seeds are in the row anyway, so a later change to an initialiser that adds 1000·k stays collision-free.
3. **ADR-0026** must not call P4's or P5's permutation helpers (`src/arborlm/p4_model.py:266-270`, `src/arborlm/p5_model.py:258-262`), which hard-code 40000 + index … 70000 + index; it uses its own P_all, P_used and X seeds above.
4. **ADR-0024 lane L, ADR-0023's new sizes and ADR-0029's bridge cells** cannot run new seeds through P10-S0's or P10-S1's code unedited: those packages whitelist their own namespaces (`studies/p10s0/core.py:541` `check_seed_set`; `studies/p10s1/core.py:820` `SEED_RANGE`, `:991` `check_seed_set`). New seeds go through new adapter code; the old packages see only their own seeds, and only as the declared re-uses of section 4.6.
5. A study's G9 gate checks its planned and recorded seeds against this allocation **with R2 and R3 expanded**, read from code and configs, and re-runs the checker (or a copy extended with the study's named values) before its freeze.

### 4.4 Test ranges

The drafts' 924001–924999 and 926001–926999 pass R1 to R3. They are moved anyway: under W1, P9-II's, P10-S0's and P10-S1's test ranges (910001–921999) plus 1000·k reach 931999, and P10-I-S1's draft range starts at 924001 = 921001 + 3000. Placing every P10-I test range at or above 932001 keeps them clear of every earlier study even under W1 (the only remaining W1 contact is the review diagnostic 941001, whose role is unknown). If the lead prefers the drafts' values, they may be restored; the binding check passes either way.

### 4.5 Rule for a future study

1. **Data:** take a whole free 10,000-block `X0001–X9999` outside 330000–399999 (initialisation zone) and 900000–999999 (test zone) that no earlier study uses; the next free ones are 310001–319999, 320001–329999, then 400001 upward. Lay it out as sets of 100 by role; in-set offsets stay below 100.
2. **Initialisation:** a programme takes one row of 1,000 values at 330001 + 11,000·m (P10-I is m = 0; the next is 341001–341999, derivation reserve 342000–351999; then 352001–352999, and so on) and gives each study a sub-row of 99. A supplement inside P10-I uses 330701–330999. Nothing is ever allocated in a row's derivation reserve.
3. **Tests:** the next free 1,000-range at or above 932001 that is not a P10-I range: 939001–939999, then 952001 upward (942001–951001 holds 941001's R2 images).
4. **Derivations:** only R2 (k ≤ 10) from initialisation seeds, R3 (index < 1,000) from any seed, in-set offsets below 100, and hashing. A study whose code needs k > 10 or an index ≥ 1,000 widens the rule in the checker first.
5. **Check:** add the new allocation to `ALLOC` in a copy of the checker (new file; this one is not edited after it is cited) and require `RESULT: PASS` and an empty `MISSING` list before the freeze.

### 4.6 Declared re-uses (Revision 2)

A declared re-use is a read-only use of seeds a completed study already used, for a check that must reproduce that study's path. It is not an allocation and not a collision: the values belong to the earlier study, the P10-I study observes nothing new on them that enters any class, count or label, and its gate lists them as re-used. The checker's section [7] asserts that every re-used value is already in the inventory (with R2 images where the value is a component seed) and lies in no P10-I allocation.

| Study | Purpose | Values | Why it is not a new observation | Source |
|---|---|---|---|---|
| P10-I-S0 (ADR-0023) | identity gate, part (a): new path bit-identical to P10-S0's path at 4,096 and 16,384 slots for A5-D, A0, A6 (initial model, one forward, one update, one evaluation record) | P10-S0 rehearsal set, base 209101 (69 values: fact-set offsets 0, 20, 60 + 0..19; targets; swaps); initialisation 2092 and its component seeds 3092–7092 | P10-S0's path accepts only its own seed sets; the rehearsal set was never registered data, and the gate compares two code paths on it, not a result. Same pattern as P10-S0's G4 re-using P9-II's rehearsal set 5 | `studies/p10s0/core.py:145` (`REHEARSAL_INIT`), `:424` (`REHEARSAL_BASE`), `:489` (`REHEARSAL_SET`), `:541` (`check_seed_set`); ADR-0023 §3 |
| P10-I-R (ADR-0029) | stage A1 reproduction reads | P10-S1 registered draws 1..5 (bases 210001–210401) with in-set seeds incl. index seed base + 60 (160 values) | the reads reproduce P10-S1's stored checkpoints and records; no model is trained on them | `studies/p10s1/core.py:812-877`; ADR-0029 §5 |
| P10-I-R (ADR-0029) | adapter identity gate (§10): the adapter reproduces P10-S1's F-OQ and T-OQ cells at 8K/4K, draw 1, at their first three snapshots | P10-S1 draw 1 set (210001) and initialisation 2101 with component seeds 3101–7101 | reproduction of a stored checkpoint, compared by hash | `studies/p10s1/core.py:486`, `:812`; ADR-0029 §10 |

### 4.7 ADR-0027's two entry routes (Revision 3)

Routes A and B both name 330401–330403 (and 279001, 279101, 279201, 330491, 330492, 330495, and the values 270001 + 100(d−1) + 0..2, which are Route A's stream seeds and Route B's first data seeds of the same sets). **Sharing is safe on one condition: one entry of S4 runs exactly one route.** ADR-0027 section 3 says "ENTRY = A or B. The route fixes the task and the memory arm of S4", so one entry has one task; no value then seeds two purposes in one study. If the human lead ever entered both routes, the shared values would seed Route A's stream permutations and Route B's fact tables and initialisations with the same generators, so for that case Route A takes the held values instead: registered streams 271001 + 100(p−1) + (s−1) (271001–271803), initialisation 330411–330413, calibration streams 279301, 279401 with 330481, 330482, rehearsal stream 279501 with 330485. They pass the checker now and are allocated to nothing else. Whether "one route per entry" is a fixed rule is ADR-0027's to state (**PENDING LEAD REVIEW**).

## 5. Collisions in the drafts' own proposals

From section [2] of the checker output (R1 to R3; "actual" means the other value is one the code itself uses or derives):

| Draft proposal | Collides with | Example |
|---|---|---|
| ADR-0023 draft 1 initialisation 3001, 3002, 3091, 3092 | P10-S0 initialisation 2001, 2002, 2091, 2092 + 1000 (and the whole chain + 1000·k); 3001/3002 + 4000 = 7001/7002 also equal P8's `7000 + index` and P7's budget seeds; 3001/3002 + 6000 = 9001/9002 = P6 `9000 + pair` | 3001 = 2001 + 1000 |
| ADR-0024 draft 1 initialisation **2401, 2402, 2403** | **P4** addition seeds 401–403 + 2000 (`Memory` values generator), and the chain: 3401–3403 = 401–403 + 3000 (`wq` and DenseAdapter `w1`), 4401–4403, 5401–5403 | 2401 = 401 + 2000. Not reported by the reviews. 2404, 2405 and 2491–2493 are clean |
| ADR-0026 initialisation 2601–2699 (values **2601, 2602**) | **P8** seeds 601, 602 + 2000 (`Memory` values generator via P5's Model), and 3601/3602 = 601/602 + 3000, … | 2601 = 601 + 2000. Not reported by the reviews. 2603–2699 are clean |
| ADR-0027 initialisation 2701–2799 (values 2701, 2702, 2791, 2792) | P9 1701, 1702 + 1000; P9-I calibration 1791, 1792 + 1000; and the chains (+ 2000 … + 8000 for P9-I) | 2701 = 1701 + 1000 |
| ADR-0023 data 300001–309999 | none under R1 to R3. Under W2 only (R3 applied to seeds below 1,000, which no code does): P2 order seeds 301–303 × 1000 + index = 301000–303999 | — |
| Data blocks 240001–289999; tests 924001–924999, 926001–926999, 259001–259999 | none under R1 to R3 | — |
| Between drafts | none | — |

The pattern behind all four: four-digit initialisation seeds of the form `2X0Y` sit in the same range that `s + 1000·k` of earlier four-digit and three-digit seeds covers (P1 to P8 seeds 42–602 reach up to 5,602; P9 to P10-S1 seeds 1701–2193 reach up to 9,802). Any new four-digit initialisation seed has to be checked against all of them; the row in 4.1 avoids the question.

## 6. Checker: command, environment, output

Command (from the worktree root):

```sh
uv run --locked python docs/reviews/p10-i-direction-2026-11-17/seed_registry_check_r3.py           # Revision 3 checks (current)
uv run --locked python docs/reviews/p10-i-direction-2026-11-17/seed_registry_check_r3.py --tables  # also prints the inventory and allocation tables
uv run --locked python docs/reviews/p10-i-direction-2026-11-17/seed_registry_check.py              # Revision 2 checker, kept unchanged
```

Environment: macOS-27.2.1-arm64 (Apple silicon), uv 0.12.15, Python 3.12.14, torch 2.8.0 from the locked environment (torch is needed only by section [6], which imports the studies' own seed functions; without it [6] prints SKIPPED). Wall time 1.06 s (measured with `/usr/bin/time -p`). Checker SHA-256 (Revision 2): `b078100689211a437d59d898e5a7fb04ee03fbcc2a388288e9f5e83dbe759289`. Exit status 0.

Attempt history (failed attempts kept):

- **Attempt 1: FAIL.** Binding check [1] passed (46 allocations, 0 problems), but cross-check [6] found 4 seeds that P9-II's own `seed_namespaces()` declares and my reconstruction lacked: `MISSING: P9-II p9_rehearsal_other: [179941, 179942, 179961, 179962]`. Cause, my error: P9-II reserves the target (+40, +41) and stream (+60, +61) offsets on **every** P9 rehearsal draw 0..9 (`studies/p9ii/core.py:440-444,469-470`), not only on its own draws 3, 4, 5; the rest of those values were already covered by the range 179001–179933 that P10-S1's G9 lists. Fixed by inventory row 36.
- **Attempt 2: PASS**, with noisy informational sections (the literal scan read JSON outputs under `docs/reviews`; the W1 grouping mis-parsed role names containing " and "). Reporting fixed; binding logic unchanged.
- **Attempt 3: PASS** (identical binding result). Then the drafts were found revised at HEAD `fd86a0b` (ADR-0024 split, ADR-0029 added, ADR-0025 asking for initialisation and test seeds). The allocation was updated (53 entries) and the between-draft report was restricted to different ADRs.
- **Attempt 4: PASS** (Revision 1's final run; 53 allocations; checker SHA-256 `6e1e0ea34fd9fef22f9ef13445460468b4c34e88fef2ed9e27dfe919c8edf30f`).
- **Revision 2 run: PASS.** 56 allocations, 0 problems; the draft-3 proposals (240501–240901, 330121–330125, 250916–250917, 252901–252914) show 0 collisions in [2]; section [7] lists 4 declared re-uses, all in the inventory, none inside an allocation. A planted negative test (re-use values 235000 and 240001; an allocation at 2701) made [7] report both faults and [1] report 30 collisions, so the new checks can fail. Its output is reproducible from the unchanged Revision 2 file.
- **Revision 3 run: PASS** (`seed_registry_check_r3.py`, SHA-256 `e462360420321aa284b0e4d47b106806419ab616794a5c632fee70f122c67594`, exit status 0). Output below, verbatim.

```text
SEED REGISTRY CHECK (P10-I) revision 3 — arbor-auditor, standard library only
root: /Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/arborlm-consolidation-experiment-2b31c1
rules: R1 identity; R2 s+1000k, k=1..10, on initialization seeds and on every inventory literal < 100000; R3 s*1000+i, i in [0,999], on every value >= 1000; in-set offsets enumerated per study
inventory: 62 entries, 51101 identity values (with overlaps)
named values checked: 117 initialization, 97 data (revision 3)

[1] binding: P10-I allocations (R1-R3 expanded) against the inventory (R1-R3 expanded) and against each other
    allocations: 56; problems: 0

[2] the drafts' own proposals (as read 2026-11-17) under the same rules, against the inventory only
    (listed: collisions with a seed the code itself uses or derives; 'conservative' counts hits that exist only through
     the catch-all entries or the +1000k applied to small literals that are not initialization seeds)
    ADR-0023 draft 1 init 3001–3002: 14 actual collisions, 85 conservative-only
       ADR-0023 draft 1 init [id] 3001..3002 = P10-S0 / initialization [+1000] (studies/p10s0/core.py:144; studies/p10s0/core.py:145)
       ADR-0023 draft 1 init [+1000] 4001..4002 = P10-S0 / initialization [+2000] (studies/p10s0/core.py:144; studies/p10s0/core.py:145)
       ADR-0023 draft 1 init [+2000] 5001..5002 = P10-S0 / initialization [+3000] (studies/p10s0/core.py:144; studies/p10s0/core.py:145)
       ADR-0023 draft 1 init [+3000] 6001..6002 = P10-S0 / initialization [+4000] (studies/p10s0/core.py:144; studies/p10s0/core.py:145)
       ADR-0023 draft 1 init [+4000] 7001..7002 = P8 / permutation [id] (src/arborlm/p8_core.py:113; src/arborlm/p8_eval.py:285; src/arborlm/p8_core.py:533)
       ADR-0023 draft 1 init [+4000] 7001..7002 = P7-A/P7-B / test (budget) [id] (src/arborlm/p7a_study.py:823; src/arborlm/p7b_budget.py:97)
       ADR-0023 draft 1 init [+4000] 7001..7002 = P10-S0 / initialization [+5000] (studies/p10s0/core.py:144; studies/p10s0/core.py:145)
       ADR-0023 draft 1 init [+5000] 8001..8002 = P7-A/P7-B / test (budget) [id] (src/arborlm/p7a_study.py:823; src/arborlm/p7b_budget.py:97)
       ADR-0023 draft 1 init [+5000] 8001..8002 = P10-S0 / initialization [+6000] (studies/p10s0/core.py:144; studies/p10s0/core.py:145)
       ADR-0023 draft 1 init [+6000] 9001..9002 = P6 / permutation [id] (src/arborlm/p6_common.py:196)
       ADR-0023 draft 1 init [+6000] 9001..9002 = P10-S0 / initialization [+7000] (studies/p10s0/core.py:144; studies/p10s0/core.py:145)
       ADR-0023 draft 1 init [+7000] 10001..10002 = P10-S0 / initialization [+8000] (studies/p10s0/core.py:144; studies/p10s0/core.py:145)
       ADR-0023 draft 1 init [+8000] 11001..11002 = P10-S0 / initialization [+9000] (studies/p10s0/core.py:144; studies/p10s0/core.py:145)
       ADR-0023 draft 1 init [+9000] 12001..12002 = P10-S0 / initialization [+10000] (studies/p10s0/core.py:144; studies/p10s0/core.py:145)
    ADR-0023 draft 1 init 3091–3092: 10 actual collisions, 18 conservative-only
       ADR-0023 draft 1 init [id] 3091..3092 = P10-S0 / initialization [+1000] (studies/p10s0/core.py:144; studies/p10s0/core.py:145)
       ADR-0023 draft 1 init [+1000] 4091..4092 = P10-S0 / initialization [+2000] (studies/p10s0/core.py:144; studies/p10s0/core.py:145)
       ADR-0023 draft 1 init [+2000] 5091..5092 = P10-S0 / initialization [+3000] (studies/p10s0/core.py:144; studies/p10s0/core.py:145)
       ADR-0023 draft 1 init [+3000] 6091..6092 = P10-S0 / initialization [+4000] (studies/p10s0/core.py:144; studies/p10s0/core.py:145)
       ADR-0023 draft 1 init [+4000] 7091..7092 = P10-S0 / initialization [+5000] (studies/p10s0/core.py:144; studies/p10s0/core.py:145)
       ADR-0023 draft 1 init [+5000] 8091..8092 = P10-S0 / initialization [+6000] (studies/p10s0/core.py:144; studies/p10s0/core.py:145)
       ADR-0023 draft 1 init [+6000] 9091..9092 = P10-S0 / initialization [+7000] (studies/p10s0/core.py:144; studies/p10s0/core.py:145)
       ADR-0023 draft 1 init [+7000] 10091..10092 = P10-S0 / initialization [+8000] (studies/p10s0/core.py:144; studies/p10s0/core.py:145)
       ADR-0023 draft 1 init [+8000] 11091..11092 = P10-S0 / initialization [+9000] (studies/p10s0/core.py:144; studies/p10s0/core.py:145)
       ADR-0023 draft 1 init [+9000] 12091..12092 = P10-S0 / initialization [+10000] (studies/p10s0/core.py:144; studies/p10s0/core.py:145)
    ADR-0023 draft 1 data 300001–309999: 0 actual collisions, 0 conservative-only
    ADR-0024 draft 1 init 2401–2405: 9 actual collisions, 9 conservative-only
       ADR-0024 draft 1 init [id] 2401..2403 = P4 / initialization [+2000] (src/arborlm/p4_config.py:21)
       ADR-0024 draft 1 init [+1000] 3401..3403 = P4 / initialization [+3000] (src/arborlm/p4_config.py:21)
       ADR-0024 draft 1 init [+2000] 4401..4403 = P4 / initialization [+4000] (src/arborlm/p4_config.py:21)
       ADR-0024 draft 1 init [+3000] 5401..5403 = P4 / initialization [+5000] (src/arborlm/p4_config.py:21)
       ADR-0024 draft 1 init [+4000] 6401..6403 = P4 / initialization [+6000] (src/arborlm/p4_config.py:21)
       ADR-0024 draft 1 init [+5000] 7401..7403 = P4 / initialization [+7000] (src/arborlm/p4_config.py:21)
       ADR-0024 draft 1 init [+6000] 8401..8403 = P4 / initialization [+8000] (src/arborlm/p4_config.py:21)
       ADR-0024 draft 1 init [+7000] 9401..9403 = P4 / initialization [+9000] (src/arborlm/p4_config.py:21)
       ADR-0024 draft 1 init [+8000] 10401..10403 = P4 / initialization [+10000] (src/arborlm/p4_config.py:21)
    ADR-0024 draft 1 init 2491–2493: 0 actual collisions, 0 conservative-only
    ADR-0024 draft 1 data 240001–249999: 0 actual collisions, 0 conservative-only
    ADR-0024 draft 1 test 924001–924999: 0 actual collisions, 0 conservative-only
    ADR-0025 draft 1 data 250001–259999: 0 actual collisions, 0 conservative-only
    ADR-0025 draft 1 test 259001–259999: 0 actual collisions, 0 conservative-only
    ADR-0026 init 2601–2699: 9 actual collisions, 9 conservative-only
       ADR-0026 init [id] 2601..2602 = P8 / initialization [+2000] (src/arborlm/p8_core.py:88)
       ADR-0026 init [+1000] 3601..3602 = P8 / initialization [+3000] (src/arborlm/p8_core.py:88)
       ADR-0026 init [+2000] 4601..4602 = P8 / initialization [+4000] (src/arborlm/p8_core.py:88)
       ADR-0026 init [+3000] 5601..5602 = P8 / initialization [+5000] (src/arborlm/p8_core.py:88)
       ADR-0026 init [+4000] 6601..6602 = P8 / initialization [+6000] (src/arborlm/p8_core.py:88)
       ADR-0026 init [+5000] 7601..7602 = P8 / initialization [+7000] (src/arborlm/p8_core.py:88)
       ADR-0026 init [+6000] 8601..8602 = P8 / initialization [+8000] (src/arborlm/p8_core.py:88)
       ADR-0026 init [+7000] 9601..9602 = P8 / initialization [+9000] (src/arborlm/p8_core.py:88)
       ADR-0026 init [+8000] 10601..10602 = P8 / initialization [+10000] (src/arborlm/p8_core.py:88)
    ADR-0026 data 260001–269999: 0 actual collisions, 0 conservative-only
    ADR-0026 test 926001–926999: 0 actual collisions, 0 conservative-only
    ADR-0027 init 2701–2799: 20 actual collisions, 30 conservative-only
       ADR-0027 init [id] 2701..2702 = P9 / initialization [+1000] (studies/p9/core.py:149)
       ADR-0027 init [id] 2791..2792 = P9-I / initialization [+1000] (studies/p9i/core.py:94; studies/p9i/core.py:93)
       ADR-0027 init [+1000] 3701..3702 = P9 / initialization [+2000] (studies/p9/core.py:149)
       ADR-0027 init [+1000] 3791..3792 = P9-I / initialization [+2000] (studies/p9i/core.py:94; studies/p9i/core.py:93)
       ADR-0027 init [+2000] 4701..4702 = P9 / initialization [+3000] (studies/p9/core.py:149)
       ADR-0027 init [+2000] 4791..4792 = P9-I / initialization [+3000] (studies/p9i/core.py:94; studies/p9i/core.py:93)
       ADR-0027 init [+3000] 5701..5702 = P9 / initialization [+4000] (studies/p9/core.py:149)
       ADR-0027 init [+3000] 5791..5792 = P9-I / initialization [+4000] (studies/p9i/core.py:94; studies/p9i/core.py:93)
       ADR-0027 init [+4000] 6701..6702 = P9 / initialization [+5000] (studies/p9/core.py:149)
       ADR-0027 init [+4000] 6791..6792 = P9-I / initialization [+5000] (studies/p9i/core.py:94; studies/p9i/core.py:93)
       ADR-0027 init [+5000] 7701..7702 = P9 / initialization [+6000] (studies/p9/core.py:149)
       ADR-0027 init [+5000] 7791..7792 = P9-I / initialization [+6000] (studies/p9i/core.py:94; studies/p9i/core.py:93)
       ADR-0027 init [+6000] 8701..8702 = P9 / initialization [+7000] (studies/p9/core.py:149)
       ADR-0027 init [+6000] 8791..8792 = P9-I / initialization [+7000] (studies/p9i/core.py:94; studies/p9i/core.py:93)
       … 6 more
    ADR-0027 data 270001–279999: 0 actual collisions, 0 conservative-only
    ADR-0028 data 280001–289999: 0 actual collisions, 0 conservative-only
    ADR-0024 draft 3 (block X) data 240501–240901: 0 actual collisions, 0 conservative-only
    ADR-0024 draft 3 (block X) init 330121–330125: 0 actual collisions, 0 conservative-only
    ADR-0025 draft 3 data (disjoint draws) 250916–250917: 0 actual collisions, 0 conservative-only
    ADR-0025 draft 3 data (Part Q rehearsal) 252901–252914: 0 actual collisions, 0 conservative-only
    ADR-0027 draft 3 Route A data (streams d=6..9) 270501–270803: 0 actual collisions, 0 conservative-only
    ADR-0027 draft 3 init 330401–330405: 0 actual collisions, 0 conservative-only
    ADR-0028 draft 3 data (registered) 280001–280303: 0 actual collisions, 0 conservative-only
    between drafts: 0

[3] informational (not binding): worst case, +1000k applied to EVERY value of every role, both sides
    hits: 3502; 1803 inside one study's own block (not listed); the rest grouped by study pair (roles merged):
           8  P10-I-R ADR-0029  <->  Review diagnostics / unknown role
         280  P10-I-S0 ADR-0023  <->  P10-I-R ADR-0029
          10  P10-I-S0 ADR-0023  <->  P10-I-S1 ADR-0024
           9  P10-I-S0 ADR-0023  <->  P10-I-S2 ADR-0025
           8  P10-I-S0 ADR-0023  <->  P10-I-S3 ADR-0026
           7  P10-I-S0 ADR-0023  <->  P10-I-S4 ADR-0027
           6  P10-I-S0 ADR-0023  <->  P10-I-S5 ADR-0028
           2  P10-I-S0 ADR-0023  <->  Review diagnostics / unknown role
           6  P10-I-S1 ADR-0024  <->  P10-I-R ADR-0029
         422  P10-I-S1 ADR-0024  <->  P10-I-S2 ADR-0025
           9  P10-I-S1 ADR-0024  <->  P10-I-S3 ADR-0026
           8  P10-I-S1 ADR-0024  <->  P10-I-S4 ADR-0027
           7  P10-I-S1 ADR-0024  <->  P10-I-S5 ADR-0028
           3  P10-I-S1 ADR-0024  <->  Review diagnostics / unknown role
           7  P10-I-S2 ADR-0025  <->  P10-I-R ADR-0029
          91  P10-I-S2 ADR-0025  <->  P10-I-S3 ADR-0026
           9  P10-I-S2 ADR-0025  <->  P10-I-S4 ADR-0027
           8  P10-I-S2 ADR-0025  <->  P10-I-S5 ADR-0028
           4  P10-I-S2 ADR-0025  <->  Review diagnostics / unknown role
           8  P10-I-S3 ADR-0026  <->  P10-I-R ADR-0029
         250  P10-I-S3 ADR-0026  <->  P10-I-S4 ADR-0027
           9  P10-I-S3 ADR-0026  <->  P10-I-S5 ADR-0028
           5  P10-I-S3 ADR-0026  <->  Review diagnostics / unknown role
           9  P10-I-S4 ADR-0027  <->  P10-I-R ADR-0029
         250  P10-I-S4 ADR-0027  <->  P10-I-S5 ADR-0028
           6  P10-I-S4 ADR-0027  <->  Review diagnostics / unknown role
         251  P10-I-S5 ADR-0028  <->  P10-I-R ADR-0029
           7  P10-I-S5 ADR-0028  <->  Review diagnostics / unknown role

[4] informational (not binding): R3 also applied to values < 1000, both sides
    hits: 4
       P10-I-S0 ADR-0023 / data: registered (10) + reserve (4) draw sets [id] 301000..301999 hits inventory: All code and tests / literal scan [x1000+i] (71 literals in src/arborlm, studies, tests)
       P10-I-S0 ADR-0023 / data: registered (10) + reserve (4) draw sets [id] 301000..302999 hits inventory: P9 / config literal [x1000+i] (configs/p9_diagnostics.toml)
       P10-I-S0 ADR-0023 / data: registered (10) + reserve (4) draw sets [id] 301000..303999 hits inventory: P2 / config literal [x1000+i] (configs/p2_optimization_followup.toml)
       P10-I-S0 ADR-0023 / data: registered (10) + reserve (4) draw sets [id] 301000..303999 hits inventory: P2/P3 / data (order) [x1000+i] (configs/p2_optimization_followup.toml:7)

[5] informational: six-digit literals inside a P10-I allocation, in configs/*.toml, src, studies, tests (*.py),
    docs/decisions/*.md (ADR-0023..0028 excluded) and docs/reviews/**/*.py (P10-I review folders excluded); sizes are not seeds
    hits: 119 occurrences of 14 distinct values
       262144 in P10-I-S3 ADR-0026 / registered streams and permutations: 104 occurrences, first configs/p10s1_capacity.toml:40
       263424 in P10-I-S3 ADR-0026 / registered streams and permutations: 3 occurrences, first tests/test_p10s1_classes.py:243
       290001 in P10-I-R ADR-0029 / data: bridge draw sets (5): 1 occurrences, first docs/decisions/ADR-0029-p10-i-r-routing-diagnosis.md:99
       298001 in P10-I-R ADR-0029 / I64 index seeds (3): 1 occurrences, first docs/decisions/ADR-0029-p10-i-r-routing-diagnosis.md:101
       298002 in P10-I-R ADR-0029 / I64 index seeds (3): 1 occurrences, first docs/decisions/ADR-0029-p10-i-r-routing-diagnosis.md:101
       298003 in P10-I-R ADR-0029 / I64 index seeds (3): 1 occurrences, first docs/decisions/ADR-0029-p10-i-r-routing-diagnosis.md:101
       299201 in P10-I-R ADR-0029 / rehearsal draw set (1): 1 occurrences, first docs/decisions/ADR-0029-p10-i-r-routing-diagnosis.md:102
       330601 in P10-I-R ADR-0029 / init sub-row: 1 occurrences, first docs/decisions/ADR-0029-p10-i-r-routing-diagnosis.md:100
       330605 in P10-I-R ADR-0029 / init sub-row: 1 occurrences, first docs/decisions/ADR-0029-p10-i-r-routing-diagnosis.md:100
       330692 in P10-I-R ADR-0029 / init sub-row: 1 occurrences, first docs/decisions/ADR-0029-p10-i-r-routing-diagnosis.md:102
       330698 in P10-I-R ADR-0029 / init sub-row: 1 occurrences, first docs/decisions/ADR-0029-p10-i-r-routing-diagnosis.md:103
       330699 in P10-I-R ADR-0029 / init sub-row: 1 occurrences, first docs/decisions/ADR-0029-p10-i-r-routing-diagnosis.md:103
       938001 in P10-I-R ADR-0029 / test: 1 occurrences, first docs/decisions/ADR-0029-p10-i-r-routing-diagnosis.md:103
       938999 in P10-I-R ADR-0029 / test: 1 occurrences, first docs/decisions/ADR-0029-p10-i-r-routing-diagnosis.md:103

[6] cross-check: every seed the studies' own functions declare lies inside the reconstruction
     P10-S0 check: 69 seeds, 0 outside the reconstruction
     P10-S0 check_rehearsal_init: 2 seeds, 0 outside the reconstruction
     P10-S0 init: 2 seeds, 0 outside the reconstruction
     P10-S0 registered: 897 seeds, 0 outside the reconstruction
     P10-S0 rehearsal: 69 seeds, 0 outside the reconstruction
     P10-S0 reserve: 138 seeds, 0 outside the reconstruction
     P10-S0 test: 552 seeds, 0 outside the reconstruction
     P10-S1 calibration: 64 seeds, 0 outside the reconstruction
     P10-S1 derived_init: 60 seeds, 0 outside the reconstruction
     P10-S1 init: 12 seeds, 0 outside the reconstruction
     P10-S1 registered: 160 seeds, 0 outside the reconstruction
     P10-S1 rehearsal: 32 seeds, 0 outside the reconstruction
     P10-S1 test: 999 seeds, 0 outside the reconstruction
     P10-S2 allowed_seeds(calibration): 110 seeds, 0 outside the reconstruction
     P10-S2 allowed_seeds(registered-analysis): 1 seeds, 0 outside the reconstruction
     P10-S2 allowed_seeds(registered-data): 11 seeds, 0 outside the reconstruction
     P10-S2 allowed_seeds(registered-run): 44 seeds, 0 outside the reconstruction
     P10-S2 allowed_seeds(rehearsal): 110 seeds, 0 outside the reconstruction
     P10-S2 allowed_seeds(test): 999 seeds, 0 outside the reconstruction
     P10-S2 listed_partition_seeds: 12 seeds, 0 outside the reconstruction
     P9 registered_seed_values: 22 seeds, 0 outside the reconstruction
     P9-I calibration_data: 20 seeds, 0 outside the reconstruction
     P9-I calibration_init: 2 seeds, 0 outside the reconstruction
     P9-I p9_registered: 22 seeds, 0 outside the reconstruction
     P9-I registered_data: 20 seeds, 0 outside the reconstruction
     P9-I registered_init: 2 seeds, 0 outside the reconstruction
     P9-I rehearsal_data: 180 seeds, 0 outside the reconstruction
     P9-I test: 60 seeds, 0 outside the reconstruction
     P9-II calibration_data_3: 24 seeds, 0 outside the reconstruction
     P9-II calibration_data_4: 24 seeds, 0 outside the reconstruction
     P9-II calibration_init: 2 seeds, 0 outside the reconstruction
     P9-II init: 2 seeds, 0 outside the reconstruction
     P9-II p9_registered: 22 seeds, 0 outside the reconstruction
     P9-II p9_rehearsal_other: 168 seeds, 0 outside the reconstruction
     P9-II p9i_registered: 24 seeds, 0 outside the reconstruction
     P9-II registered: 336 seeds, 0 outside the reconstruction
     P9-II rehearsal_data_5: 24 seeds, 0 outside the reconstruction
     P9-II reserve: 48 seeds, 0 outside the reconstruction
     P9-II test: 72 seeds, 0 outside the reconstruction

[7] declared re-uses (read-only use of a completed study's seeds; not allocations, not collisions)
     P10-I-S0 ADR-0023: identity gate part (a): P10-S0 rehearsal data set (base 209101), read-only, bit-identity at 4,096 and 16,384 slots: 69 values, 209101–209142, 209145–209146, 209149–209153, 209161–209180 (69 values); source studies/p10s0/core.py:424 (REHEARSAL_BASE), :489 (REHEARSAL_SET), :541 (check_seed_set); not in inventory: 0; inside a P10-I allocation: 0
     P10-I-S0 ADR-0023: identity gate part (a): P10-S0 rehearsal initialization seed 2092 and its +1000k component seeds: 6 values, 2092, 3092, …, 6092, 7092 (6 values); source studies/p10s0/core.py:145 (REHEARSAL_INIT); studies/p9/model.py:272-279; not in inventory: 0; inside a P10-I allocation: 0
     P10-I-R ADR-0029: stage A1 reproduction reads: P10-S1 registered draws 1..5 incl. index seed (base + 60): 160 values, 210001–210014, 210021–210023, …, 210441, 210451–210461 (160 values); source studies/p10s1/core.py:812-877; not in inventory: 0; inside a P10-I allocation: 0
     P10-I-R ADR-0029: adapter identity gate (section 10): P10-S1 cells F-OQ and T-OQ at 8K/4K, draw 1 (set 210001) with initialization seed 2101 and its component seeds: 38 values, 2101, 3101, …, 210041, 210051–210061 (38 values); source studies/p10s1/core.py:486 (2100 + r), :812 (REGISTERED_BASE), :820 (SEED_RANGE whitelist); not in inventory: 0; inside a P10-I allocation: 0

RESULT: PASS
```

## 7. Unknowns and open points

1. **P9 rehearsal draws are unbounded in code.** `rehearsal_seeds(draw)` (`studies/p9/core.py:842`) and the `--draw` options accept any draw ≥ 0, so values `179001 + 100k + (0..13, 20..22, 30..32)` exist for every k; k = 610 gives 240001, inside P10-I-S1's block, and every P10-I block contains such values. The inventory assumes draws 0..9 and 90; a grep of `results/` found only `rehearsal-0`, `rehearsal-1` and `rehearsal-5`. Not verified against `experiments/` (git-ignored, not read).
2. **941001** is listed by P10-S1's and P10-S2's G9 as a "review diagnostics" seed (`studies/p10s1/core.py:888`); its origin and role were not found in the repository. It is treated as an initialisation seed (R2 applied).
3. **Hash-derived seeds** (62-bit SHA-256 of seed and tags) cannot be enumerated. A chance collision with the ≈ 10⁵ allocated values has probability of the order of 10⁵ / 2⁶² ≈ 2·10⁻¹⁴ per derived seed; not proven absent.
4. **Literal coverage.** P1 to P8 seeds are taken from configs, named constants and the rules cited; a seed computed at run time from a variable the regex scan does not match could be missed. P1 to P8 seeds all lie below 100,000 (P7/P8 panel seeds 91xxx), and every R2 or R3 image of them is far from the P10-I zones; section [5] found no six-digit literal of `src`, `studies`, `tests`, `configs`, ADR-0010…0022 or review scripts inside a P10-I allocation except 262144 and 263424, which are sizes (2¹⁸ and a work count), not seeds.
5. **Review scripts** under `docs/reviews/` were not inventoried seed by seed; only the diagnostics listed by the P10 gates (500001–500004, 941001) are included.
6. **Counts not stated by the drafts:** ADR-0027's Route A calibration parents (fixed in its later revision); ADR-0028's scientific part (not laid out); ADR-0024's lane L seeds (PENDING, decided in its lane L revision); ADR-0025's calibration draws beyond i = 0, 1. Sub-ranges with headroom are reserved; **PENDING LEAD REVIEW**.
7. **Seed whitelists of reused code** (Revision 2: resolved in the drafts). P10-S0's and P10-S1's packages whitelist their own namespaces, so ADR-0023 and ADR-0029 now use new adapter code and touch the old packages only through the declared re-uses of section 4.6. Whether the adapters reproduce the old paths bit for bit is what their identity gates test.
8. **The three overlaps among earlier studies** in section 3 (182001/182002; 190001/190002 and 191001/191002; 7001/7002) were derived from code rules; whether the corresponding arms and draws ran was not checked in the records. **PENDING LEAD REVIEW**.
9. **Test-range choice** (section 4.4) and the choice to keep ADR-0023 at 300001–309999 rather than 230001–239999 (which would order the blocks by study but lies within W1 reach of P10-S2's 220001–229999) are engineering choices; the binding check passes either way.

`Astra review: NOT_PERFORMED`. This is independent engineering evidence by the `arbor-auditor` subagent (Claude Opus 5.5); it is not Astra validation and not human approval.
