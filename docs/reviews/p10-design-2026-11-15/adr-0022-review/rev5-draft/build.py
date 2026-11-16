"""Builds ADR-0022 revision 5 and CHANGES.md from revision 4 (post-E8, with the section 18 records; commit 3cf3576)
by exact, single-occurrence text edits.

Usage: python3 -I build.py <rev4.md> <out_dir>
Reads revision 4 read-only. Writes two files into out_dir. No network, no model, no repository write.
"""
import sys

src, out = sys.argv[1], sys.argv[2]
text = open(src, encoding="utf-8").read()
C = []  # (id, where, finding, reason, mode, old, new)


def rep(cid, where, finding, reason, old, new):
    C.append((cid, where, finding, reason, "replace", old, new))


def ins(cid, where, finding, reason, anchor, new):
    C.append((cid, where, finding, reason, "insert after", anchor, new))


LC = "**[lead's choice]**"
DELEG = "\"we can change it to  p10 can be self approve but p10-I need my review\""
ORACLE_Q = "\"must not claim autonomous learned-memory success from oracle-assisted results\""

# ------------------------------------------------------------------ arithmetic used in the new text (stdlib only)
STORE_U, LORA_U, CELLS = 16, 6, 18


def hours(n, half):
    f = 0.5 if half else 1.0
    lo = n * STORE_U * 5 / 60 * f + n * LORA_U * 8 / 60 * f
    hi = n * STORE_U * 10 / 60 * f + n * LORA_U * 15 / 60 * f
    s_lo = n * CELLS * 1.6 / 60 + n * 0.9 + 0.3
    s_hi = n * CELLS * 5.2 / 60 + n * 3.0 + 0.6
    return (lo + s_lo, hi + s_hi), (s_lo, s_hi)


RUNG = {1: hours(4, False), 2: hours(3, False), 3: hours(4, True), 4: hours(3, True)}


def f1(x):
    return f"{x:.1f}"


def rng(p):
    return f"{f1(p[0])}–{f1(p[1])}"


BASE = {k: rng(v[0]) for k, v in RUNG.items()}
REC = {k: rng(v[1]) for k, v in RUNG.items()}
FULL = {k: rng((v[0][0] + v[1][0], v[0][1] + v[1][1])) for k, v in RUNG.items()}
assert BASE == {1: "14.4–35.5", 2: "10.8–26.8", 3: "10.1–27.2", 4: "7.6–20.5"}, BASE
assert REC[1] == REC[3] == "5.8–18.8" and REC[2] == REC[4] == "4.4–14.3", REC
assert FULL == {1: "20.2–54.3", 2: "15.3–41.1", 3: "15.9–46.0", 4: "12.1–34.8"}, FULL
R_MAX = ((36 - 7.0) / 2, (36 - 3.5) / 2)
assert R_MAX == (14.5, 16.25)
lo = {k: v[0][0] + v[1][0] for k, v in RUNG.items()}
assert lo[1] > R_MAX[1]                      # rung 1 never holds on the projection
assert R_MAX[0] < lo[2] < R_MAX[1] and R_MAX[0] < lo[3] < R_MAX[1]   # rungs 2, 3: only with P near its lower figure
assert lo[4] < R_MAX[0]                      # rung 4: fast part of its range
P_MAX_2, P_MAX_3 = 36 - 2 * lo[2], 36 - 2 * lo[3]
assert f1(P_MAX_2) == "5.4" and f1(P_MAX_3) == "4.2"
# downloads
assert abs(300.8 + 303.7 + 272.4 + 53.1 - 930.0) < 1e-6 and abs(930.0 + 8.1 + 315.3 - 1253.4) < 1e-6
# wheels of the eight named packages, from adr-0022-review/web/pypi_*.json (macOS arm64, Python 3.12)
W = 564262 + 104107 + 897476 + 432206 + 1253645 + 2926478 + 11990925
assert f1((W + 5113918) / 1e6) == "23.3" and f1((W + 14185220) / 1e6) == "32.4"
# seeds: every listed registered seed is inside 220001-228999 and outside calibration, rehearsal and tests
REG = [b + o for b in (220001, 220101, 220201, 220301) for o in range(11)] + list(range(220901, 220906))
assert len(set(REG)) == len(REG) == 49
assert all(220001 <= s <= 228999 and not 221001 <= s <= 221999 and not 222001 <= s <= 222999 and not 229001 <= s <= 229999 for s in REG)
assert all(221001 <= 221001 + 100 * i + o <= 221999 and 222001 <= 222001 + 100 * i + o <= 222999 for i in range(10) for o in range(11))

# ================================================================== header
rep("C01", "header, status line", "task item 7",
    "New status for revision 5.",
    "- **Status: DESIGN REVISION 4 — CONFIRMED BY THE AUDITOR SUBJECT TO C1–C10 AND m1–m7, WHICH THIS REVISION APPLIES. SPEC: PENDING ASTRA REVIEW. Nothing is implemented, downloaded or run.**",
    "- **Status: DESIGN REVISION 5 — pending an independent confirmation; lead's approval PENDING; nothing implemented, downloaded or run. SPEC: PENDING ASTRA REVIEW.**")

ins("C02", "header, after the editorial-corrections line", "task items 1, 7",
    "Says what revision 5 is and where the previous text is.",
    "The text before these corrections is `docs/reviews/p10-design-2026-11-15/revisions/ADR-0022-rev4-before-E8.md`.",
    "\n- **Revision 5** applies the re-check of revision 4 (`adr-0022-review/RECHECK_REV4.md`, Opus 5.5: READY SUBJECT TO text edits; majors J1–J8, minors J9–J14 and others) and does nothing else. No threshold, arm, model, data source, replicate count, rung or cap is changed. Points the re-check left open are settled by the P9 / P9-II convention where one exists, otherwise by the option that is harder for a positive label or counts more time against the cap; each is marked " + LC + " and listed in §20 with the alternative not taken. §21 maps each change to its finding. The text before this revision is commit `3cf3576` on `claude/p10-design`.")

rep("C03", "header, the two capabilities", "re-check §4 (stale sentence); task item 4",
    "The human lead answered reserved item 3; the header still said the decision was pending.",
    "- **Decision that stays with the human lead.** This design uses two translation directions (English→German, English→French) as the two capabilities. They are two capabilities of one kind. **Whether that satisfies \"complementary capabilities\" is the human lead's decision, not the lead's** (§16).",
    "- **The two capabilities.** This design uses two translation directions (English→German, English→French) as the two capabilities. The human lead has accepted them as the two capabilities of this study (§18, item 3). They remain two capabilities of one kind, and §17 limits what a result can mean.\n"
    "- **Oracle qualification.** Every address and every registered route in S2 is supplied by rule. \"Learned memory\" in the title names a store whose keys and values are trained; it does not name learned addressing. The human lead's instruction is that S1 and S2 " + ORACLE_Q + ". §11.3 puts the oracle-assisted line above every printed class, label, annotation and cost line.")

ins("C04", "header, evidence line", "task item 1",
    "The re-check is review evidence like the two earlier reviews.",
    "both Opus 5.5, with the two synthetic probes, are review evidence, not registered results.",
    " The re-check of revision 4 (`adr-0022-review/RECHECK_REV4.md`, Opus 5.5) has the same standing.")

rep("C05", "revision history, row 4", "task item 7",
    "Revision 4 is no longer the current text; its re-check is recorded.",
    "| 4 | 2026-11-15 | confirmed subject to C1–C10 and m1–m7, which this revision applies |",
    "| 4 | 2026-11-15 | applied C1–C10 and m1–m7; re-checked by the auditor: READY SUBJECT TO text edits (J1–J8 major, J9–J14 and others minor; `adr-0022-review/RECHECK_REV4.md`) |")

ins("C06", "revision history, row 5", "task item 7",
    "Adds revision 5 to the history.",
    "\"(n, U)\" on every label; the meaning of \"every replicate\" stated. §19 maps every finding. |",
    "\n| 5 | 2026-11-15 | pending an independent confirmation; lead's approval PENDING | applies the re-check of revision 4: generator seeds listed and seeded directly, with seed gate G9; key initialization stated; the download scope stated once (what is approved, what is open with the human lead); marker strings of the GEN panel within tokens 1–64; router training recipe; disjoint training draws and gold sufficiency; the rung rule's rates and charged scope, and NOT STARTED: BUDGET; RET reference; LoRA and E-table initialization; filter tie-break; window grid; BOS from the reference default; the oracle-assisted line above every printed class and line. No threshold, arm, model, data source, replicate count, rung or cap changed. §21 maps every finding. |")

# ================================================================== §0
rep("C07", "§0 item 6", "J8b; re-check §2 item 3; task item 6",
    "Names the unreachable-budget outcome, and states the consequence of counting the recomputation inside the registered run.",
    "The projection (§13) fits the cap with 2× headroom only at the fast end of an unmeasured throughput estimate. The rehearsal rule decides (§13.3); it can end at three replicates, at shortened training, or in \"not started\".",
    "The projection (§13) fits the cap with 2× headroom only at the fast end of an unmeasured throughput estimate. With the independent recomputation counted inside the registered run (revision 5, §13.3), four full-length replicates do not fit anywhere on the projection. The rehearsal rule decides (§13.3); it can end at three replicates, at shortened training, or in **NOT STARTED: BUDGET**.")

# ================================================================== §3
ins("C08", "§3, key initialization", "J2 (E-J2, verbatim) and J1",
    "The key distribution was never stated; appended rows must not repeat the stage-1 draw.",
    "*(lead's choice)*; the report states that the append cost depends on that initialization.",
    " Keys are initialized from a normal distribution with standard deviation 0.02 *(lead's choice; as P9's `_matrix`)*. Appended keys and values are drawn from the same distributions with the stage-2 seed (§9), never with the stage-1 seed. " + LC + " The alternative, keys of unit scale, would make the keys move far less per update under the cosine score; the P9 convention is kept.")

ins("C09", "§3, reference test", "J1",
    "P9's memory class seeds its own generators at seed + 1000·k; the reference test must not bring that derivation into S2.",
    "- **Reference test.** On shared inputs the selection and weights equal those of the P9 flat memory forward, imported read-only.",
    " The test passes S2's own tensors to the P9 forward. S2 code initializes no P9 module from a seed, so P9's `seed + 1000·k` derivation is not exercised (§9, gate G9).")

# ================================================================== §4.2
rep("C10", "§4.2, fallback hash", "re-check §4 (fallback SHA-256)",
    "The hash is in the reviewer's saved Hub tree in the repository (`adr-0022-review/web/opus_en-es_tree.json`, LFS oid), so it is stated.",
    "(Apache-2.0; `pytorch_model.bin` 312,087,523 B; 77,484,009 parameters)",
    "(Apache-2.0; `pytorch_model.bin` 312,087,523 B, SHA-256 `befce0f620e8e63f83bbb7f0818eb51d541cba28057a7cc14b00466d85c4994c` from the reviewer's saved Hub tree, `adr-0022-review/web/opus_en-es_tree.json`, to be checked at download; 77,484,009 parameters)")

rep("C11", "§4.2, when the fallback is fetched", "J3; task item 3 (supersedes E-J3's \"same session\")",
    "One statement of the download scope: fallback teacher and fallback data only if the fallback rule is invoked.",
    "The fallback's files are fetched only if it is invoked and approved (§14.1).",
    "The fallback teacher's files and the fallback's Tatoeba files (Spanish; rows 5 and 6 of §14.1) are fetched only if the rule above invokes the fallback. The human lead's approval covers them for that case only (§18).")

# ================================================================== §5.2
ins("C12", "§5.2, sufficiency rule", "J7 (E-J7, verbatim, with the split rule the re-check left pending)",
    "No rule made T_A^r and T_B^r disjoint when the pools overlap; the gold draw was not in the sufficiency rule.",
    "or an accepted pool 8,000, the study stops with TRANSFER-INCONCLUSIVE: DATA-INSUFFICIENT.",
    " English sources in both accepted pools are split, by the training-draw seed of each replicate, into two halves assigned to A and B before drawing. Sufficiency requires, for each capability, its exclusive accepted sources plus its half ≥ 8,000 × 1.25 *(lead's choice)*, and 8,000 gold pairs per capability outside Q, D_cal and D_con; otherwise DATA-INSUFFICIENT. " + LC + " The half is the smaller one when the shared count is odd; the gold pairs are in-vocabulary pairs of 3 to 10 words. All replicates draw from one accepted pool per capability, so their training draws overlap. The share of training items common to each pair of replicates is reported, and §9's reading of \"every replicate\" is given with that share.")

# ================================================================== §5.3
ins("C13", "§5.3, generation sample", "J1",
    "Names the seed of the source sample.",
    "At most 60,000 sources per capability, a seeded sample *(lead's choice)*",
    " (seed 220903, §9)")

ins("C14", "§5.3, filter tie-break", "J12",
    "No rule chose between settings with the same accepted share.",
    "against the best reference — is ≥ **0.90**.",
    " Among settings with the same accepted share, the one with the larger τ is taken, then the narrower length-ratio range " + LC + ".")

rep("C15", "§5.3, verification", "task item 4 (recorded answer on item 4)",
    "The acceptance is the human lead's, recorded in §18, not a ruling of the lead.",
    "is met in this sense and no other; the lead has ruled this acceptable, and it is named in the label line (§11.3).",
    "is met in this sense and no other; the human lead has accepted the filter as the verification of the teachers' outputs (§18, item 4), and it is named in the label line (§11.3).")

# ================================================================== §5.4
ins("C16", "§5.4, address", "J1",
    "Says which seed the oracle codes use and that the hash seeds no generator.",
    "the code u(t, w) is a fixed random unit vector in R^16 from a seeded hash of the pair",
    " (seed +10 of the replicate, §9; the hash takes that listed seed and the pair as inputs, as P9's `unit_code` does, and seeds no generator)")

ins("C17", "§5.4, router lane", "J6 (E-J6, verbatim, then the points it left open)",
    "The router decides a label gate (GEN) and had no training recipe.",
    "the prompts differ in a marker word, and a pass says nothing about fine-grained addressing.",
    " Router training: AdamW, learning rate 0.001, 500 updates of batch 64 *(lead's choice)*, on the stored prompts of the current stage's training streams only (never D_cal, D_con or an evaluation panel) and on WikiText-2 *train* prefixes of exactly 64 tokens in equal number; the projection is initialized from seed +3. The decision position in training matches GEN's (the 64th token of a \"none\" prefix; the last prompt token of a task prompt). " + LC + " In detail, all " + LC + ": \"the current stage's training streams\" are the prompts of T^r of every task the router of that snapshot must know — one stream for an ST1 router, T_A^r and T_B^r for a stage-2 or joint router; prompts only, and no teacher is run. Every batch holds the same number of examples of each class (each task, and \"none\") as nearly as 64 allows, the remainder going to \"none\". The \"none\" prefixes are consecutive non-overlapping 64-token pieces of the tokenized WikiText-2 train file, 8,000 of them sampled with seed +3. The hidden state is the output of block L, where the store would be read. The loss is cross-entropy over the cosine scores divided by the read temperature 0.2. The projection and then the router keys are drawn from N(0, 0.02) by one generator seeded +3; every router is trained from that initialization and is not continued from an earlier stage's router. A router depends on the replicate and on the set of tasks, not on the arm.")

# ================================================================== §6.4
rep("C18", "§6.4, \"before\"", "J10",
    "§6.4's \"before\" (parent snapshot) and §11.1's \"after Stage 1\" differed for M-ii.",
    "\"before\" is the parent snapshot's score.",
    "\"before\" is the parent snapshot's score, except in the RET gate and the retention negative zone, where it is V1 for every stage-2 arm (§11.1).")

rep("C19", "§6.4, marker-like windows", "J5 (E-J5, verbatim)",
    "A marker string after token 64 is invisible to the router, so such a window is not a hard negative.",
    "\"translation\" or a line ending in \":\"** (selected by rule with the partition seed)",
    "\"translation\" or a line ending in \":\", with at least one such string within tokens 1–64 of the window (the part the router sees)** (selected by rule with the GEN-window seed 220905, §9)")

ins("C20", "§6.4, window grid", "J14, J5",
    "How windows are cut from the validation stream was unstated.",
    "This data is used for nothing else.",
    " **Window grid " + LC + ".** The validation file is tokenized once as a whole in the data-generation step and cut from its first token into consecutive, non-overlapping windows of 256 tokens; a trailing remainder is dropped. A window is in the marker-like stratum if one of the strings lies wholly within the text of its tokens 1–64, and in the ordinary stratum if it contains none of the strings anywhere. A window whose only such strings lie after token 64 is in neither stratum and is not used. 100 windows of each stratum are sampled with the GEN-window seed. If either stratum has fewer than 100 windows on this grid, neither the grid nor the rule is changed and the work returns to the lead before the freeze.")

# ================================================================== §7
ins("C21", "§7, LoRA form", "J11",
    "LoRA scaling and initialization were unspecified.",
    "Placement is fixed, not tuned; calibration tunes only its learning rate.",
    " LoRA form " + LC + ": the update is (α/r)·B·A with α = r, a scale of 1; A is drawn uniform on ±1/√(fan-in), the conventional initialization (as ADR-0021 does for its dense control), from seed +8; B is zero, so an untrained adapter changes nothing; no dropout.")

rep("C22", "§7, E-table row", "J11",
    "E-table initialization and gate were unspecified; it starts as the store does.",
    "added at layer L at the same positions as the store's reads; no keys, no top-k |",
    "added at layer L at the same positions as the store's reads; no keys, no top-k; vectors drawn from N(0, 0.02) with seed +9 and multiplied by one linear scalar gate with initial value 0, as the store's values are " + LC + " |")

rep("C23", "§7, ablation subsample", "J1",
    "The subsample has its own listed seed instead of sharing the partition seed.",
    "drawn once with the partition seed and the same for every cell and replicate",
    "drawn once with the ablation-subsample seed 220904 (§9) and the same for every cell and replicate")

# ================================================================== §9
rep("C24", "§9, seeds", "J1 (E-J1, verbatim except the named streams); re-check §3 minor (S1 ranges); task item 2",
    "Generator seeds were not defined; under P9's seed + 1000·k every S2 seed would land in S2's own calibration or rehearsal range. The re-check's hash of (220901, stream name) would leave the listed sets, so the streams get listed seeds.",
    "- Seeds: replicate bases 220001, 220101, 220201, 220301 (base + 0 initialization, + 1 training draw, + 2 batch order, + 3 router, + 4 permutation controls, + 5 gold draw); partition seed 220901; calibration 221001–221999; rehearsal 222001–222999; tests 229001–229999. The implementation asserts the ranges are disjoint from each other and from every seed of P1–P9-II, S0 (200001–209999, 2001–2002, 2091–2092, 920001–920999) and S1, and writes the hash of every panel and stream to the data manifest.",
    "- Seeds: replicate bases 220001, 220101, 220201, 220301, each with these offsets:\n"
    "  - +0 stage-1 store (keys, then values, from one generator in that order);\n"
    "  - +1 training draw;\n"
    "  - +2 batch order;\n"
    "  - +3 router;\n"
    "  - +4 permutation controls;\n"
    "  - +5 gold draw;\n"
    "  - +6 stage-2 appended rows;\n"
    "  - +7 M-joint store;\n"
    "  - +8 LoRA initialization;\n"
    "  - +9 E-table initialization;\n"
    "  - +10 oracle-code hash " + LC + " (per replicate, as every data draw of P9-II and of S1 carries its own code seed; the alternative is one fixed code seed for all replicates).\n\n"
    "  Within a replicate, the M-seq and M-ii arms start from the snapshots they continue. Partition seed 220901. The other partition-side streams each have a listed seed " + LC + ": 220902 the Q split, 220903 the 60,000-source sample, 220904 the ablation subsample, 220905 the GEN window selection. (The re-check's text took these streams by a hash of (220901, stream name); a hashed seed would leave the listed sets.) Calibration draws use 221001 + 100·i and rehearsal draws 222001 + 100·i with the same offsets, i = 0…9; tests use 229001–229999. Every generator is seeded directly by a listed seed: **no \"+1000·k\" derivation is used**, and no seed is obtained by hashing or by arithmetic on another seed beyond the offsets listed here. One seed serves the uses that §9 pairs, in a fixed order " + LC + ": +0 initializes ST1 of both orders and MA-gold of both capabilities; +6 the appended rows of both orders (keys, then values); +8 LoRA-1 of both orders and, with its own shapes, L-joint; +9 E-table of both capabilities; +1 and +5 draw capability A, then B.\n\n"
    "  The implementation asserts that every seed actually passed to a generator lies in the listed sets and is disjoint from:\n"
    "  - P1–P9-II (as listed in ADR-0021 §6.3);\n"
    "  - S0 (200001–209999, 2001–2002, 2091–2092, 920001–920999);\n"
    "  - S1 (210001–219999, 2101–2105, 2111, 2112, 2121, 2122, 2191–2192, 921001–921999).\n\n"
    "  Every listed registered seed lies in S2's namespace 220001–228999 and outside S2's calibration (221001–221999), rehearsal (222001–222999) and test (229001–229999) ranges; gate G9 (§12.3) asserts it on the seeds actually used. The implementation writes the hash of every panel and stream to the data manifest.")

ins("C25", "§9, class and label lines", "re-check §5 (E-5); task item 5",
    "\"(n, U)\" was required on class lines but the oracle-assisted line was not.",
    "- Every class and label line prints \"(n replicates, U = …)\"",
    ", under the oracle-assisted line of §11.3")

# ================================================================== §11
rep("C26", "§11.1, RET", "J10 (E-J10, verbatim)",
    "States the reference snapshot of RET for every stage-2 arm.",
    "| RET | s_first after Stage 2 ≥ s_first after Stage 1 − 0.03, and G_first after ≥ 0.90 × G_first before |",
    "| RET | s_first after Stage 2 ≥ s_first after Stage 1 − 0.03, and G_first after ≥ 0.90 × G_first before. \"after Stage 1\" and \"before\" mean V1 (the ST1 snapshot) for every stage-2 arm, including M-ii " + LC + " (the alternative is the parent snapshot, which for M-ii is M-append-frozen's) |")

ins("C27", "§11.2, class lines", "re-check §5 (E-5); task item 5",
    "A mechanism-class line could be printed without the oracle-assisted line.",
    "M-i-separate and L-sep are printed **BY CONSTRUCTION** and receive no class.",
    " Every class line is printed under the oracle-assisted line of §11.3.")

rep("C28", "§11.3, row 1", "J1; task item 2",
    "The new seed gate G9 is an engineering gate like the others.",
    "a defect found by gates G1, G4–G8;",
    "a defect found by gates G1, G4–G9;")

ins("C29", "§11.3, after the fixed line", "re-check §5 (E-5, verbatim, first bullet); task item 5",
    "Positive-sounding class, router, composition and cost lines could be printed without the fixed line.",
    "teacher-only training material verified by measured-precision filter; not autonomous learned memory.\"**",
    "\n- The same line heads every mechanism-class line, every annotation and every table of the outcome report that prints a class or label, and every cost line.\n"
    "- **No positive wording without it.** The human lead's instruction is that S1 and S2 " + ORACLE_Q + ". The words ACQUIRES-AND-RETAINS, TRANSFER-POSITIVE, QUALIFIED, COMPOSES, TRAINING COST COMPARABLE and FEWER VALUE ROWS ACTIVE, and every other class, mechanism, router, composition or cost line, are therefore printed only directly under that line: in the outcome report, in every table and figure caption, in the machine-readable outcome record (as a field of the same record), and in any summary a script writes to the terminal or to a log. The analysis refuses to write an output in which such a line lacks it, and the report test on synthetic records (§13.3, rehearsal content) checks every such line.")

ins("C30", "§11.4, annotations", "re-check §5 (E-5); task item 5",
    "ROUTER QUALIFIED and COMPOSES could appear in a table of their own without the line.",
    "| Cost lines | always printed (§11.5) |",
    "\n\nEvery annotation, the ROUTER and COMPOSES lines included, is printed under the oracle-assisted line of §11.3, also when it appears in a table of its own.")

ins("C31", "§11.5, cost lines", "re-check §5 (E-5); task item 5",
    "Cost lines are positive-sounding and carried no qualification.",
    "None is an efficiency result. Logical counts are never reported as measured efficiency.",
    " Each cost line is printed under the oracle-assisted line of §11.3.")

# ================================================================== §12.3
rep("C32", "§12.3, G5(c)", "J13 (E-J13, verbatim)",
    "0 · inf is NaN; the isolation test holds for finite values.",
    "replaced by arbitrary values equals r with them at zero",
    "replaced by arbitrary finite values equals r with them at zero")

ins("C33", "§12.3, G5 key initialization", "J2",
    "Points G5's sentence at the stated distribution and seed.",
    "Appended keys are initialized from the same distribution as first-stage keys *(lead's choice)*, and the report states that the append cost depends on that initialization.",
    " The distribution is normal with standard deviation 0.02, drawn with the stage-2 seed (§3, §9).")

ins("C34", "§12.3, new gate G9", "J1; task item 2",
    "A gate must assert the namespace on the seeds actually used, not on declared ranges.",
    "including the stored injection-point logits and the stored greedy sequences of §14.2 step 4.",
    "\n- **G9** seeds (§9). Every generator in `studies/p10s2/` is seeded through one function, which records the seed and its purpose and refuses a seed outside the set allowed for the running stage. The gate asserts, on the seeds planned for the registry and again on the seeds actually recorded: every seed of the registered run is one of the listed registered seeds (a replicate base + 0…10, or 220901–220905), lies in 220001–228999 and lies outside 221001–221999, 222001–222999 and 229001–229999; every calibration seed lies in 221001–221999, every rehearsal seed in 222001–222999 and every test seed in 229001–229999; no recorded seed lies in a range of P1–P9-II, S0 or S1 listed in §9. A source check asserts that no generator is seeded anywhere else and that the global default generator is not used. The recorded seed list is written to the run record. A seed outside its set stops the run.")

# ================================================================== §13
ins("C35", "§13.2, charging rule", "J8b",
    "Whether the second gates stage and the recomputation are charged was not stated.",
    "The data-generation step, calibration, pilot, rehearsal and the registered run are all charged.",
    " So are the second gates stage on registered seeds and the independent recomputation of §16 step 10 (§13.3).")

ins("C36", "§13.3, projection table", "J8b",
    "The table had no row for the recomputation, which is now inside R.",
    "| **Registered run** | | | | **14.4–35.5 h** |",
    "\n| Independent recomputation of every score (§16 step 10); not in the row above; projected as one repetition of the three scoring rows, an upper estimate | CPU | — | — | " + REC[1] + " h |")

ins("C37", "§13.3, after the rung list", "J8a, J8b, re-check §2 item 3 (E-J8, adapted); task items 2 and 6",
    "Fixes which rates the rule uses after a re-selection at U = 1,000, what R contains, and the name of the outcome \"none\".",
    "5. none: the run is not started and the lead returns to the human lead.",
    "\n\n**Rates and scope of the rule (revision 5).** R(n, U) contains, for n replicates: training; every scoring; the second gates stage on registered seeds; the timing benchmark; and the independent recomputation of every score of §16 step 10, which is charged like any other S2 process " + LC + " (inside R and inside the 36 hours, so the headroom doubles it; the alternative is to charge it outside R). The recomputation is projected from the rehearsal's measured scoring rates as one repetition of every scoring. For U = 2,000 the training rates are those of the calibrated setting, rehearsed at full length. For U = 1,000 the setting may be re-selected (§12.1), and the read layer may change with it. R(n, 1,000) therefore uses, for every store-type cell, the slower of the rates measured at L = 4 and at L = 12 " + LC + " (the slower rate counts more time against the cap; the re-check's text used the rates of the re-selected setting). The read layer that was not rehearsed at full length is measured on 200 rehearsal updates of each store-type cell type before the rule is applied, and that time is part of P. The outcome \"none\" is recorded as **NOT STARTED: BUDGET** with the rehearsal record. A re-design after it is a new decision of the human lead (§16).")

rep("C38", "§13.3, projection sentence", "re-check §2 (E-m1: stale parenthetical, 7.6); J8b",
    "The parenthetical invited adding a change twice; rung 4 computes to 7.6. With the recomputation inside R the reading of the projection changes, and the text must say so.",
    "On the projection above the registered run is 14.4–35.5 h at rung 1, 10.8–26.8 h at rung 2, 10.1–27.2 h at rung 3 and 7.7–20.5 h at rung 4 (removing M-seq-shared and adding L-joint changes each by about +0.1 to +0.3 h per replicate). A rung holds only if its registered run measures at about 15 hours or less, so rung 1 holds only at the fast end. **It is plausible that the rule ends at rung 2 or below, or at \"not started\".**",
    "On the table above, training and first scoring come to " + BASE[1] + " h at rung 1, " + BASE[2] + " h at rung 2, " + BASE[3] + " h at rung 3 and " + BASE[4] + " h at rung 4. The recomputation, projected as one repetition of the three scoring rows, adds " + REC[1] + " h for four replicates and " + REC[2] + " h for three (an upper estimate, because the timing benchmark is not repeated). R is then " + FULL[1] + " h at rung 1, " + FULL[2] + " h at rung 2, " + FULL[3] + " h at rung 3 and " + FULL[4] + " h at rung 4; the second gates stage is not projected. A rung holds only if its R measures at about 15 hours or less (14.5 h at P = 7.0, 16.25 h at P = 3.5). **On this projection rung 1 does not hold at all; rung 2 holds only at its fastest end and with P below about " + f1(P_MAX_2) + " h, rung 3 only at its fastest end and with P below about " + f1(P_MAX_3) + " h; rung 4 holds in the fast part of its range. It is plausible that the rule ends at rung 4 or at NOT STARTED: BUDGET.** These are projections, not measurements; the rehearsal decides.")

ins("C39", "§13.3, rehearsal content", "J8a",
    "The rates of the read layer not selected must be measured for the rule.",
    "one store cell, one M-ii cell and one LoRA cell for the full U;",
    " 200 updates of each store-type cell type at the read layer that calibration did not select (for the rule's rates);")

# ================================================================== §14.1
rep("C40", "§14.1, opening paragraph", "J3, J4; re-check §4 (stale \"no answer yet\"); task items 3 and 4",
    "One statement of what is approved and what is open.",
    "The lead has asked the human lead about the student and the data and has no answer yet. The human lead's words cover \"two small teachers\"; everything else in this table is outside those words.",
    "**Approved by the human lead and recorded (§18):** rows 1–4 — the two teachers, the student and the Tatoeba exports — and, only if the fallback rule of §4.2 is invoked, rows 5 and 6, the fallback teacher and the fallback (Spanish) data. **Not approved, open with the human lead:** the package wheels for the one-off data-generation step (§14.2); the two symmetry-check link files (6.2 MB, below); any package outside the lock. Nothing in the open list is fetched before a recorded answer of the human lead, given with the sizes in front of them. Implementation and tests on synthetic stand-ins need none of it. No download has been made.")

rep("C41", "§14.1, row 6", "J3; task item 3",
    "The fallback data are fetched only if the fallback is invoked.",
    "| 6 | Fallback data — fetched in the same session as row 4 so that all Tatoeba files come from one weekly export; opened only if the fallback is invoked |",
    "| 6 | Fallback data, only if invoked |")

rep("C42", "§14.1, total row", "J3, J4; task item 3",
    "The totals follow the scope above and name what is outside them.",
    "**930 MB primary; 938 MB with the fallback data fetched in the same session; 1,253 MB if the fallback teacher is invoked**",
    "**930 MB approved and fetched (rows 1–4); 8.1 MB + 315.3 MB more only if the fallback is invoked (1,253 MB in all). Not in these figures and not approved: 6.2 MB of symmetry-check link files; the package wheels (§14.2)**")

rep("C43", "§14.1, symmetry-check link files", "J3, J4; task item 3",
    "The 6.2 MB were in no figure shown to the human lead and cannot be \"part of row 4's approval\".",
    "if those two files are fetched for the check they add 6.2 MB and are part of row 4's approval.",
    "those two files add 6.2 MB. **They were in no figure shown to the human lead and are not approved.** The symmetry check against them is made only if the human lead approves them; they are then fetched in the same session as row 4. Without them the check is not made, and the data manifest and the report say that the symmetry of the link files was not checked " + LC + ".")

rep("C44", "§14.1, one session", "J3; task item 3",
    "\"All Tatoeba files, the fallback's included, in one session\" contradicted §4.2 and §18.",
    "- **One session.** All Tatoeba files, the fallback's included, are fetched in one session, because a later fetch would come from a different weekly export.",
    "- **One session.** The five files of row 4 (and the two link files, if approved) are fetched in one session, because a later fetch would come from a different weekly export. The fallback's Tatoeba files are not fetched with them. If the fallback is invoked, they come from a later weekly export: link rows whose English sentence id is absent from the frozen English file are dropped and counted, the dates of both sessions are recorded, and the report states the mix " + LC + ".")

# ================================================================== §14.2
rep("C45", "§14.2 step 4, BOS", "re-check §1 C8 (E-m3, verbatim)",
    "BOS is decided by a rule instead of by the lead's expectation.",
    "BOS is not prepended in any input *(lead's choice; the same convention in the equivalence logits and every registered input)*",
    "BOS follows the reference tokenizer's default for this model, read from the pinned `tokenizer.json`/`tokenizer_config.json` and recorded in the data-generation step; the draft expects \"not prepended\" (the same convention in the equivalence logits and every registered input)")

rep("C46", "§14.2, sacrebleu row", "re-check §4 (stale sentence)",
    "`CONFIRM.md` §6 checked existence, licence and advisories.",
    "analysis-only cross-check; exists on PyPI, Apache-2.0; not checked by the reviewer",
    "analysis-only cross-check; exists on PyPI, Apache-2.0, no advisories (`CONFIRM.md` §6); brings portalocker, regex, tabulate, colorama, lxml and numpy")

rep("C47", "§14.2, package wheels", "J4; re-check §4 (stale sentence); task items 3 and 4",
    "The wheels are not approved; the sentence said only that the question was left to the human lead.",
    "- Package wheels are themselves downloads. Whether they may be fetched is left to the human lead (§16); none is fetched before the answer.",
    "- **Package wheels are themselves downloads, and they are not approved.** The figure shown to the human lead (938 MB) did not include them (§18, the lead's correction). They are open with the human lead, together with the use of packages outside the lock that they imply. From the reviewer's saved index records (`adr-0022-review/web/pypi_*.json`), the wheels of the eight packages named above for macOS arm64 and Python 3.12 total about 23 MB, or about 32 MB if numpy's larger wheel is the one selected. The transitive dependencies are not in those records and their sizes are not established. No wheel is fetched, and the resolution that writes `requirements-datagen.txt` (it contacts the package index) is not run, before a recorded answer of the human lead. The data-generation step cannot start before that answer. Implementation and tests on synthetic stand-ins do not need it.")

# ================================================================== §15
ins("C48", "§15, standing of the departures", "J9; re-check §4 (§15 item 3); task item 4",
    "Departures 1, 4, 5 and 7 were neither reserved for the human lead nor accepted anywhere.",
    "7. Data without a revision identifier: frozen by recorded hash, not by pin.",
    "\n\n**Standing of each item at revision 5.** Item 2 rests on the human lead's answer recorded in §18 (training on MPS with every score recomputed on CPU). Item 3 stands as revision 4 stated it; the re-check could not verify that the words quoted in §18 refer to the 36-hour figure, and the lead confirms their context in the approval record. Item 6 is open with the human lead (§14.2, §16). Items 1, 4, 5 and 7 are neither reserved for the human lead in §16 nor yet accepted: their acceptance is for the lead's approval record in §18, under the delegation " + DELEG + ". This revision does not record that acceptance.")

# ================================================================== §16
rep("C49", "§16, order of work", "J3, J4; task item 3",
    "The order of work must show that the data-generation step waits for the open answers.",
    "**Order.** (1) The human lead's answers on the five reserved items below. (2) Lead's approval, recorded in §18. (3) Implementation review as the work proceeds. (4) Implementation with tests on synthetic stand-ins, before any download. (5) Downloads; data-generation step.",
    "**Order.** (1) The human lead's answers on the reserved items below: recorded in §18, except the open ones. (2) Lead's approval, recorded in §18. (3) Implementation review as the work proceeds. (4) Implementation with tests on synthetic stand-ins, before any download. (5) Downloads of the approved files (§14.1); then the data-generation step, which cannot start before the human lead has answered on the package wheels.")

rep("C50", "§16, reserved items", "J3, J4; re-check §4; task items 3 and 4",
    "The list now shows which items are answered and which are open, in the words of §14.1 and §18.",
    "The five items the auditor left for the human lead; the lead does not decide them:\n\n"
    "1. The downloads of the student (272.4 MB), the Tatoeba data (53.1 MB), and the fallback teacher and data (315.3 MB + 8.1 MB) (§14.1).\n"
    "2. Whether the package wheels for the data-generation step count as downloads (§14.2).\n"
    "3. Whether two translation directions are \"complementary capabilities\".\n"
    "4. Whether a filter of measured precision counts as \"suitable verification\" (§5.3).\n"
    "5. Acceptance of training on MPS and of packages outside the lock (§15 items 2 and 6).",
    "The five items the auditor left for the human lead, with their state at revision 5 (§18 holds the words), and a sixth from the re-check. The lead does not decide them:\n\n"
    "1. The downloads of the two teachers (300.8 MB + 303.7 MB), the student (272.4 MB) and the Tatoeba data (53.1 MB), and, only if the fallback rule is invoked, the fallback teacher and data (315.3 MB + 8.1 MB) (§14.1). **Answered: approved.**\n"
    "2. The package wheels for the data-generation step (§14.2; about 23 to 32 MB for the eight named packages, transitive dependencies not established). **Open: not approved.**\n"
    "3. Whether two translation directions are \"complementary capabilities\". **Answered: yes.**\n"
    "4. Whether a filter of measured precision counts as \"suitable verification\" (§5.3). **Answered: yes.**\n"
    "5. Acceptance of training on MPS and of packages outside the lock (§15 items 2 and 6). **Training on MPS with scores recomputed on CPU: answered, yes. Packages outside the lock: open.**\n"
    "6. The two symmetry-check link files (6.2 MB, §14.1). **Open: not approved.**\n\n"
    "Nothing in an open item is fetched or installed before a recorded answer.")

# ================================================================== §18
rep("C51", "§18, end of the approval record", "J3, J4, J9; task items 3 and 4",
    "States the download scope once, without rewriting the earlier records, which the lead's correction keeps as written; places the acceptance of §15 departures with the lead's approval record; updates the pending line.",
    "Lead's approval: PENDING revision 5, which answers the re-check (majors J1–J8), and its confirmation.",
    "**Download scope as revision 5 states it** (one statement for §4.2, §14.1, §14.2 and §16; it adds no approval and removes none):\n\n"
    "- Approved by the human lead and recorded above: the two teachers, the student, the Tatoeba data; the fallback teacher and the fallback (Spanish) data only if the fallback rule of §4.2 is invoked.\n"
    "- Not approved, open with the human lead: the package wheels for the one-off data-generation step (about 23 to 32 MB for the eight named packages; transitive dependencies not established); the 6.2 MB of symmetry-check link files; any package outside the lock.\n"
    "- Nothing in the open list is fetched before a recorded answer. Implementation and tests on synthetic stand-ins need none of it.\n"
    "- The re-check's paste-ready edits to the records above (E-J3 for item 1, E-J4 for item 2 and for the last bullet) are not applied to those records: the lead's correction keeps them as written and supersedes them. E-J3's \"fetched in the same session\" is not adopted (§14.1).\n\n"
    "**§15 departures 1, 4, 5 and 7 (J9).** Their acceptance is for the lead's approval record, under the delegation " + DELEG + ". It is not given in this revision.\n\n"
    "Lead's approval: PENDING. Revision 5 answers the re-check (majors J1–J8, minors J9–J14 and others; §21) and awaits an independent confirmation.")

# ================================================================== §19
ins("C52", "§19, not applied verbatim, item 1", "re-check §1 C8 (E-m3)",
    "The BOS choice is replaced by the re-check's rule.",
    "because the student was trained with whichever convention its authors used.",
    " *Revision 5: replaced by the re-check's rule; BOS follows the reference tokenizer's default (§14.2).*")

ins("C53", "§19, not applied verbatim, item 5", "J3, J4",
    "The two link files are not covered by any approval.",
    "which the download table did not list before; they are now named under row 4.",
    " *Revision 5: these two files are not approved and are open with the human lead (§14.1, §18).*")

# ================================================================== §20
rep("C54", "§20, table row BOS and keys", "J2; E-m3",
    "Keeps the list of choices in step with §3 and §14.2.",
    "| BOS convention; appended-key initialization | not prepended; same distribution as first-stage keys | §14.2, §3 |",
    "| BOS convention; key initialization | the reference tokenizer's default (expected: not prepended); normal, standard deviation 0.02, appended rows drawn with the stage-2 seed | §14.2, §3 |")

rep("C55", "§20, table row seeds", "J1",
    "Keeps the list of choices in step with §9.",
    "| Seeds | replicate bases 220001, 220101, 220201, 220301; partition 220901 | §9 |",
    "| Seeds | replicate bases 220001, 220101, 220201, 220301 with offsets +0…+10; partition-side streams 220901–220905; every generator seeded directly | §9 |\n\n"
    "**Choices made in revision 5 where the re-check left a point open** (each marked " + LC + " in the text; rule used: the P9 / P9-II convention where one exists, otherwise the option that is harder for a positive label or counts more time against the cap):\n\n"
    "| Point | Choice | Alternative not taken | Section |\n"
    "|---|---|---|---|\n"
    "| J1 seed derivation | every generator seeded directly by a listed seed; offsets +0…+10 per replicate | P9's `seed + 1000·k`, which lands in S2's own calibration and rehearsal ranges with the present bases | §9, G9 |\n"
    "| J1 partition-side streams | listed seeds 220902–220905 | a hash of (220901, stream name), which leaves the listed sets | §9 |\n"
    "| J1 oracle-code seed | per replicate (+10) | one fixed code seed for all replicates | §5.4, §9 |\n"
    "| J1 appended rows | own seed +6, keys then values | reuse of the stage-1 seed (duplicates the first-stage keys) | §3, §9 |\n"
    "| J1 seeds shared between cells | +0 for ST1 of both orders and MA-gold; +8 for LoRA-1 and L-joint; +9 for E-table of both capabilities | a separate seed per cell | §9 |\n"
    "| J2 key initialization | normal, standard deviation 0.02, as P9's `_matrix` | unit-scale keys | §3 |\n"
    "| J5 marker placement | at least one marker-like string within tokens 1–64 of every window of that stratum; windows with such strings only later are not used | keep such windows and report their share | §6.4 |\n"
    "| J6 router recipe | AdamW, 0.001, 500 updates of batch 64; prompts of every task the router must know; balanced classes; 8,000 \"none\" prefixes of 64 tokens; hidden state at block L; cross-entropy over cosine scores at temperature 0.2; trained from seed +3 for every snapshot | the second stream only at stage 2; the final layer's hidden state; continuing the earlier router | §5.4 |\n"
    "| J7 disjoint draws | shared accepted sources split in halves by each replicate's training-draw seed; pool ≥ 8,000 × 1.25 per capability; 8,000 gold pairs per capability; overlap between replicates reported | draws disjoint across replicates (pool ≥ n × 8,000), harder to satisfy; one split fixed by the partition seed | §5.2 |\n"
    "| J8a rates after re-selection | the slower of the rates at L = 4 and L = 12 | the rates of the re-selected setting | §13.3 |\n"
    "| J8b scope of R | second gates stage and independent recomputation inside R and inside the 36 hours | recomputation charged outside R, or outside the cap | §13.2, §13.3 |\n"
    "| J10 RET reference | V1 for every stage-2 arm | the parent snapshot (M-append-frozen's for M-ii) | §6.4, §11.1 |\n"
    "| J11 LoRA form | α = r; A uniform on ±1/√(fan-in), B zero; no dropout | α = 2r; A normal with standard deviation 0.02 | §7 |\n"
    "| J11 E-table | N(0, 0.02) with a linear scalar gate at 0, as the store | zero vectors without a gate | §7 |\n"
    "| J12 filter tie-break | larger τ, then the narrower length-ratio range | first in grid order | §5.3 |\n"
    "| J14 window grid | consecutive non-overlapping 256-token windows from the first token; fewer than 100 in a stratum returns to the lead | overlapping windows; filling a short stratum from the other | §6.4 |\n"
    "| Seed gate | G9, with a failure counted under ENGINEERING-FAILURE like G4–G8 | an assertion outside the gate list | §11.3, §12.3 |\n"
    "| Link files not approved | the symmetry check is not made and the report says so | not starting the data-generation step without it | §14.1 |\n"
    "| Fallback data from a later export | link rows to English ids absent from the frozen file dropped and counted | fetching the 8.1 MB with row 4, as revision 4's table said | §14.1 |")

# ================================================================== closing lists
rep("C56", "open questions, item 4", "re-check §1 C8 (E-m3)",
    "The BOS question is settled by rule.",
    "4. BOS: \"not prepended\" is written as the lead's choice; confirm against the reference tokenizer's default before the freeze.",
    "4. BOS: settled by rule in revision 5 (the reference tokenizer's default, recorded in the data-generation step).")

ins("C57", "open questions, added", "task item 2",
    "Points the lead at the choices this revision made by rule.",
    "6. Should the equivalence tolerance (1e-3) be replaced by a measured run-to-run difference of the reference, as the auditor prefers?",
    "\n7. The choices of revision 5 listed at the end of §20, each with its alternative. The heaviest in consequence: the recomputation inside R (on the projection it removes rung 1 and leaves rungs 2 and 3 only at the fastest end); training draws that overlap between replicates; the oracle-code seed per replicate.")

rep("C58", "things to verify, first bullet", "re-check §4 (stale); task item 3",
    "Five items are no longer open; three points are.",
    "- The human lead's answers on the five reserved items of §16.",
    "- The human lead's answers still open: the package wheels, the two symmetry-check link files, packages outside the lock (§16).\n"
    "- The source of the human lead's sentence on oracle-assisted results quoted in the header and §11.3; it is not in the repository's records.\n"
    "- The context of the words quoted in §18 for the 36-hour cap (§15 item 3).")

rep("C59", "things to verify, package set", "re-check §4 (stale sacrebleu sentence)",
    "The reviewer did check sacrebleu; the resolution waits for the answer on the wheels.",
    "- That the package set of §14.2 resolves with torch 2.8.0 on Python 3.12; `sacrebleu` 2.5.1 was not checked by the reviewer.",
    "- That the package set of §14.2 resolves with torch 2.8.0 on Python 3.12. Not run: the resolution contacts the package index and waits for the human lead's answer on the wheels.")

# ================================================================== §21 (inserted before "Open questions for the lead")
MAP = [
    ("J1 (major) generator seeds", "Offsets +0…+10 per replicate; listed stream seeds 220902–220905; direct seeding, no +1000·k; S1's ranges listed; gate G9 on the seeds actually used; G9 in ENGINEERING-FAILURE", "§3, §5.3, §5.4, §7, §9, §11.3, §12.3"),
    ("J2 (major) key initialization", "Normal, standard deviation 0.02; appended rows from the stage-2 seed", "§3, §12.3"),
    ("J3 (major) download scope", "One statement: rows 1–4 approved; fallback teacher and data only if invoked; link files and wheels open. E-J3's \"same session\" for the fallback data not adopted", "§4.2, §14.1, §16, §18"),
    ("J4 (major) wheels not in the figure", "Wheels and packages outside the lock stated as not approved and open; sizes from the saved index records where they exist", "§14.1, §14.2, §16, §18"),
    ("J5 (major) marker placement", "At least one marker-like string within tokens 1–64", "§6.4"),
    ("J6 (major) router recipe", "E-J6, with data, balance, layer, loss and initialization stated", "§5.4"),
    ("J7 (major) disjoint draws, gold", "E-J7; overlap between replicates reported", "§5.2"),
    ("J8 (major) rung rule", "Slower of the two read layers' rates at U = 1,000; second gates stage and recomputation inside R; projection restated; NOT STARTED: BUDGET", "§0, §13.2, §13.3"),
    ("J9 departures 1, 4, 5, 7", "Acceptance placed with the lead's approval record; not given here", "§15, §18"),
    ("J10 RET reference", "V1 for every stage-2 arm", "§6.4, §11.1"),
    ("J11 LoRA scaling, E-table", "α = r, conventional initialization; E-table as the store", "§7"),
    ("J12 filter tie-break", "Larger τ, then the narrower range", "§5.3"),
    ("J13 finite values", "\"arbitrary finite values\"", "§12.3"),
    ("J14 window grid", "Consecutive non-overlapping windows; strata defined", "§6.4"),
    ("Re-check §2: stale parenthetical, 7.6, unnamed outcome", "Parenthetical deleted; 7.6–20.5 h; NOT STARTED: BUDGET", "§0, §13.3"),
    ("Re-check §3 minor: S1 ranges", "Listed", "§9"),
    ("Re-check §4: fallback SHA-256", "Added from the reviewer's saved Hub tree", "§4.2"),
    ("Re-check §4: stale sentences", "Header; §14.1 opening; §14.2 wheels and sacrebleu; §5.3; closing lists", "header, §5.3, §14.1, §14.2, closing lists"),
    ("Re-check §1 C8: BOS (E-m3)", "The reference tokenizer's default, recorded", "§14.2, §19, §20"),
    ("Re-check §5: oracle line (E-5)", "The line heads every class, annotation, router, composition and cost line; no positive wording without it", "header, §9, §11.2–§11.5"),
]
sec21 = ("## 21. Map of the re-check of revision 4 (`RECHECK_REV4.md`) to revision 5\n\n"
         "| Finding | Change | Where |\n|---|---|---|\n"
         + "".join(f"| {a} | {b} | {c} |\n" for a, b, c in MAP)
         + "\n**Not applied verbatim (listed, not resolved silently):**\n\n"
         "1. **E-J1, named streams.** The re-check took them by a hash of (220901, stream name). Revision 5 gives each a listed seed, because the lead's instruction for this revision is that every seed actually used stays inside 220001–228999 and outside the calibration, rehearsal and test ranges.\n"
         "2. **E-J3.** The re-check's text fetched the fallback's Tatoeba files in the same session as row 4. Revision 5 follows the lead's correction in §18: fallback teacher and fallback data only if the fallback rule is invoked.\n"
         "3. **E-J3 and E-J4, edits to the §18 records.** Not made. The earlier records are kept as written; the lead's correction supersedes them and the statement at the end of §18 gives the scope.\n"
         "4. **E-J8, rates.** The re-check's text used the rates of the re-selected setting. Revision 5 uses the slower of the two read layers' rates.\n"
         "5. **E-J9.** The re-check's sentence records the lead's acceptance. Revision 5 does not record it; it is left to the lead's approval record.\n"
         "6. **Additions beyond the re-check's text**, each marked " + LC + ": the details of the router recipe, the window grid, the LoRA and E-table forms, the filter tie-break, gate G9, the handling of a later fallback export, and the consequence for the projection of counting the recomputation inside R.\n\n")
C.append(("C60", "new §21", "task item 7", "Maps each change to its finding.", "insert before", "## Open questions for the lead\n", sec21))

# ------------------------------------------------------------------ the lead's rulings on the first draft
exec(compile(open(__file__.replace('build.py', 'rulings.py'), encoding='utf-8').read(), 'rulings.py', 'exec'))

# ------------------------------------------------------------------ apply
for cid, where, finding, reason, mode, old, new in C:
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"{cid}: anchor occurs {n} times: {old[:90]!r}")
    if mode == "replace":
        text = text.replace(old, new)
    elif mode == "insert after":
        text = text.replace(old, old + new)
    else:
        text = text.replace(old, new + old)

for stale in ("has no answer yet", "+0.1 to +0.3 h per replicate", "7.7–20.5", "part of row 4's approval",
              "not checked by the reviewer", "is the human lead's decision, not the lead's", "DESIGN REVISION 4 —"):
    assert stale not in text, stale
assert "Astra review: NOT_PERFORMED" in text and text.count("NOT STARTED: BUDGET") >= 4
assert DELEG in text and "\"yes s0 should include the penalty and i approve s2 download\"" in text
assert "\"s2.1 yes s2.2 yes, s2.3 yes\"" in text
assert ORACLE_V in text and ORACLE_Q not in text and WHEELS_V in text and WHEELS_Q in text
assert "does not hold at all" not in text and "3cf3576" not in text and "transitive dependencies not established" not in text

open(f"{out}/ADR-0022-p10-s2-two-teacher-transfer.md", "w", encoding="utf-8").write(text)

# ------------------------------------------------------------------ CHANGES.md
OPEN = open(f"{out}/open_for_the_lead_v2.md", encoding="utf-8").read()
h = ["# ADR-0022 revision 5 — changes from revision 4 (commit 3cf3576 on claude/p10-design)\n\n",
     "Draft by the lead subagent (Claude Fable 5.2, `claude-fable-5-2`). Text only: nothing implemented, downloaded, run or committed. ",
     "Not an approval; not a confirmation. Astra review: NOT_PERFORMED.\n\n",
     f"Built by `build.py` with the lead's rulings on the first draft applied by `rulings.py`: {len(C)} exact single-occurrence edits. No threshold, arm, model, data source, replicate count, rung or cap is changed.\n\n",
     "## Changes\n\n"]
for cid, where, finding, reason, mode, old, new in C:
    h.append(f"### {cid} — {where}\n\n- **Finding answered:** {finding}\n- **Reason:** {reason}\n- **Mode:** {mode}\n\n")
    if mode == "replace":
        h.append("Old:\n\n```text\n" + old + "\n```\n\nNew:\n\n```text\n" + new + "\n```\n\n")
    else:
        h.append("Anchor (unchanged):\n\n```text\n" + old.strip("\n") + "\n```\n\nInserted:\n\n```text\n" + new.strip("\n") + "\n```\n\n")
h.append(OPEN)
open(f"{out}/CHANGES.md", "w", encoding="utf-8").write("".join(h))
print(f"{len(C)} edits applied; {len(text)} characters")
