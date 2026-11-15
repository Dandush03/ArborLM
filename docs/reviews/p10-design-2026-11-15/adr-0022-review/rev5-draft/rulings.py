# The lead's rulings on the first draft of revision 5, applied as overrides of the edit list of build.py.
# Executed by build.py (same namespace) after the edit list is built and before it is applied.
# Rulings: 1 recomputation not charged, second gates stage inside R; 2 oracle sentence verbatim; 3 context of the
# 36-hour sentence; 4 package wheels approved, link files still not; 6 P9 reference test; 7 fallback partitions;
# 9 where the revision 4 text is kept. Rulings 5 and 8 keep the draft.


def over(cid, new=None, reason=None, finding=None, edit=None):
    for i, c in enumerate(C):
        if c[0] == cid:
            c = list(c)
            if edit is not None:
                for a, b in edit:
                    assert c[6].count(a) == 1, (cid, a[:60])
                    c[6] = c[6].replace(a, b)
            if new is not None:
                c[6] = new
            if reason is not None:
                c[3] = reason
            if finding is not None:
                c[2] = finding
            C[i] = tuple(c)
            return
    raise SystemExit(f"no edit {cid}")


def f2(x):
    return f"{x:.2f}"


ORACLE_V = "\"S1 and S2 must not claim autonomous learned-memory success from oracle-assisted results.\""
WHEELS_V = "\"yes I do, yes we can raise to 16 and I approve the package\""
WHEELS_Q = "\"Approve the package wheels and the 6.2 MB of link files for S2? These were not in the 938 MB figure.\""

# second gates stage: G2 and G4 each score E_A and E_B twice (four scorings at the table's 1.6-5.2 min), plus at most
# 0.05 h for the repeated 20-update runs, the general panel and the hash checks. Independent of n and U. Unmeasured.
GATES = (4 * 1.6 / 60, 4 * 5.2 / 60 + 0.05)
assert (f2(GATES[0]), f2(GATES[1])) == ("0.11", "0.40")
DESIGN = {1: "4 × 2,000", 2: "3 × 2,000", 3: "4 × 1,000", 4: "3 × 1,000"}
TS = {k: v[0] for k, v in RUNG.items()}
assert [(f2(TS[k][0]), f2(TS[k][1])) for k in (1, 2, 3, 4)] == [("14.35", "35.51"), ("10.84", "26.78"), ("10.09", "27.17"), ("7.64", "20.53")]
RG = {k: (TS[k][0] + GATES[0], TS[k][1] + GATES[1]) for k in TS}
assert RG[1][0] < R_MAX[0] < R_MAX[1] < RG[1][1]            # rung 1 holds only at the fast end
ROWS = "".join(f"| {k} | {DESIGN[k]} | {f2(TS[k][0])}–{f2(TS[k][1])} | {f2(GATES[0])}–{f2(GATES[1])} | **{f2(RG[k][0])}–{f2(RG[k][1])}** |\n" for k in (1, 2, 3, 4))
RUNG_TABLE = ("| Rung | Design | Training and scoring (h) | Second gates stage (h) | R (h) |\n|---|---|---|---|---|\n" + ROWS)
print(RUNG_TABLE)

# ---------------------------------------------------------------- ruling 9: header
over("C02", edit=[("The text before this revision is commit `3cf3576` on `claude/p10-design`.",
                   "The revision 4 text is kept at `docs/reviews/p10-design-2026-11-15/revisions/ADR-0022-rev4.md`.")])

# ---------------------------------------------------------------- ruling 2: the oracle sentence, verbatim
over("C03", edit=[("The human lead's instruction is that S1 and S2 " + ORACLE_Q + ".",
                   "The human lead's instruction, verbatim: " + ORACLE_V)])
over("C29", edit=[("The human lead's instruction is that S1 and S2 " + ORACLE_Q + ".",
                   "The human lead's instruction, verbatim: " + ORACLE_V)])

# ---------------------------------------------------------------- ruling 1: §0, §13
over("C07", finding="re-check §2 item 3; task item 6",
     reason="Names the unreachable-budget outcome. The reading of the projection is revision 4's, because the recomputation is not charged (lead's ruling 1).",
     new="The projection (§13) fits the cap with 2× headroom only at the fast end of an unmeasured throughput estimate. The rehearsal rule decides (§13.3); it can end at three replicates, at shortened training, or in **NOT STARTED: BUDGET**.")

over("C35", reason="States what is charged: the second gates stage is; the recomputation is not (lead's ruling 1).",
     new=" So is the second gates stage on registered seeds. The independent recomputation of §16 step 10 is not charged (§13.3).")

over("C36", reason="The table had no row for the second gates stage, which is inside R, nor for the recomputation, which is stated for information.",
     new="\n| Second gates stage on registered seeds (inside R; not in the row above): four scorings of E_A and E_B at the rate above, plus at most 0.05 h for the repeated updates, the general panel and the hash checks | both | — | — | " + f1(GATES[0]) + "–" + f1(GATES[1]) + " h |"
         "\n| Independent recomputation of every score (§16 step 10): an audit step after the registered run, **not charged** (§13.3); for information, one repetition of the three scoring rows, an upper estimate | CPU | — | — | " + REC[1] + " h |")

over("C37", finding="J8a, J8b, re-check §2 item 3 (E-J8, adapted); lead's ruling 1",
     new="\n\n**Rates and scope of the rule (revision 5).** R(n, U) contains, for n replicates: training; every scoring of the registered run; the timing benchmark; and the second gates stage on registered seeds. **The independent recomputation of every score (§16 step 10) is not in R and is not charged to the 36 hours** " + LC + ". It is an audit step performed after the registered run by a separate auditor context, and the project's convention is that such a recomputation is not charged to the study's budget: the Opus recomputations of P9-I and P9-II were not charged to those studies. (The alternative not taken is the recomputation inside R.) For information, it is projected at " + REC[1] + " h for four replicates and " + REC[2] + " h for three, as one repetition of the three scoring rows, an upper estimate. It must respect the per-process memory limits of this section (8 GiB per worker, 24 GiB aggregate), and no result is reported before it completes. For U = 2,000 the training rates are those of the calibrated setting, rehearsed at full length. For U = 1,000 the setting may be re-selected (§12.1), and the read layer may change with it. R(n, 1,000) therefore uses, for every store-type cell, the slower of the rates measured at L = 4 and at L = 12 " + LC + " (the slower rate counts more time against the cap; the re-check's text used the rates of the re-selected setting). The read layer that was not rehearsed at full length is measured on 200 rehearsal updates of each store-type cell type before the rule is applied, and that time is part of P. The second gates stage enters R at the time the rehearsal's gates stage measured. The outcome \"none\" is recorded as **NOT STARTED: BUDGET** with the rehearsal record. A re-design after it is a new decision of the human lead (§16).")

over("C38", finding="re-check §2 (E-m1: stale parenthetical, 7.6); J8b; lead's ruling 1",
     reason="The parenthetical invited adding a change twice; rung 4 computes to 7.64. The second gates stage is inside R and is shown.",
     new="On the table above, training and scoring come to the figures below (the re-check's recomputation; revision 4 printed 7.7 for 7.64). The second gates stage is projected at " + f2(GATES[0]) + "–" + f2(GATES[1]) + " h at every rung: it does not depend on n or U. That figure is unmeasured like the others, and the rehearsal's gates stage replaces it.\n\n"
         + RUNG_TABLE +
         "\nA rung holds only if its R measures at about 15 hours or less (14.5 h at P = 7.0, 16.25 h at P = 3.5), so rung 1 holds only at the fast end. **It is plausible that the rule ends at rung 2 or below, or at NOT STARTED: BUDGET.**")

# ---------------------------------------------------------------- ruling 6: P9 reference test
over("C09", finding="J1; lead's ruling 6",
     new=" The test passes S2's own tensors explicitly to the P9 forward. S2 does not construct P9's `ScalableMemory` from a seed, so P9's `seed + 1000·k` derivation is not exercised (§9, gate G9). If the P9 forward cannot be given the tensors without editing P9, the reference test is dropped and the report says so " + LC + ".")

# ---------------------------------------------------------------- ruling 7: fallback partitions
over("C11", finding="J3; task item 3 (supersedes E-J3's \"same session\"); lead's ruling 7",
     edit=[("The human lead's approval covers them for that case only (§18).",
            "The human lead's approval covers them for that case only (§18). If the fallback is invoked, the invocation first returns to the human lead (the fallback is a reserved decision); partitions and panels are then rebuilt by the same rules and seeds with the fallback language in place of the failed one, before any training.")])

# ---------------------------------------------------------------- ruling 4: wheels approved, link files not
over("C40", new="**Approved by the human lead and recorded (§18):** rows 1–4 — the two teachers, the student and the Tatoeba exports; only if the fallback rule of §4.2 is invoked, rows 5 and 6, the fallback teacher and the fallback (Spanish) data; and the package wheels for the one-off data-generation step (§14.2). **Not approved, open with the human lead:** the two symmetry-check link files (6.2 MB, below), about which the lead has asked again; any package outside the lock other than those wheels. Nothing in the open list is fetched before a recorded answer of the human lead, given with the sizes in front of them. Implementation and tests on synthetic stand-ins need none of it. No download has been made.")

over("C42", new="**930 MB approved and fetched (rows 1–4); 8.1 MB + 315.3 MB more only if the fallback is invoked (1,253 MB in all). Not in these figures: the package wheels (approved, §14.2; about 23 to 32 MB for the eight named packages, their dependencies recorded at fetch time); 6.2 MB of symmetry-check link files (not approved)**")

over("C43", edit=[("**They were in no figure shown to the human lead and are not approved.**",
                   "**They were in no figure shown to the human lead and are not approved.** The human lead's answer on the package wheels did not name them, and the lead has asked again (§18).")])

over("C47", finding="J4; re-check §4 (stale sentence); lead's ruling 4",
     reason="The human lead has approved the wheels; the sentence said the question was left open.",
     new="- **Package wheels are themselves downloads. The human lead has approved them (§18):** the eight packages named above and the dependencies the resolver requires for them, pinned with exact versions and hashes in the requirements file of the freeze, installed with `uv run --locked --with`; `uv.lock` and `pyproject.toml` do not change. The 938 MB figure did not include them. From the reviewer's saved index records (`adr-0022-review/web/pypi_*.json`), the wheels of the eight named packages for macOS arm64 and Python 3.12 total about 23 MB, or about 32 MB if numpy's larger wheel is the one selected. The transitive dependencies are not in those records; their names, versions, hashes and sizes are recorded at fetch time. Nothing else is installed outside the lock without a further answer. By §16 the wheels are fetched with the downloads, after implementation on synthetic stand-ins.")

over("C48", finding="J9; re-check §4 (§15 item 3); lead's rulings 3, 4 and 8",
     new="\n\n**Standing of each item at revision 5.** Item 2 rests on the human lead's answer recorded in §18 (training on MPS with every score recomputed on CPU). Item 3 rests on the human lead's sentence \"im confortable with does number …\" quoted in §18, which answered the lead's message listing S0 16 h, S1 12 h, S2 36 h, total 64 h (§18). Item 6 rests on the human lead's approval of the package wheels (§18) and reaches no other package. Items 1, 4, 5 and 7 are neither reserved for the human lead in §16 nor yet accepted: their acceptance is for the lead's approval record in §18, under the delegation " + DELEG + ". This revision does not record that acceptance.")

over("C49", new="**Order.** (1) The human lead's answers on the reserved items below: recorded in §18, except the link files. (2) Lead's approval, recorded in §18. (3) Implementation review as the work proceeds. (4) Implementation with tests on synthetic stand-ins, before any download. (5) Downloads of the approved files (§14.1) and of the approved wheels (§14.2); data-generation step.")

over("C50", edit=[
    ("2. The package wheels for the data-generation step (§14.2; about 23 to 32 MB for the eight named packages, transitive dependencies not established). **Open: not approved.**",
     "2. The package wheels for the data-generation step (§14.2; about 23 to 32 MB for the eight named packages, their dependencies recorded at fetch time). **Answered: approved.**"),
    ("**Training on MPS with scores recomputed on CPU: answered, yes. Packages outside the lock: open.**",
     "**Training on MPS with scores recomputed on CPU: answered, yes. Packages outside the lock: approved for the data-generation wheels of item 2 and for nothing else.**"),
    ("6. The two symmetry-check link files (6.2 MB, §14.1). **Open: not approved.**",
     "6. The two symmetry-check link files (6.2 MB, §14.1). **Open: not approved.** The answer on item 2 did not name them; the lead has asked again."),
])

over("C51", finding="J3, J4, J9; task items 3 and 4; lead's rulings 3, 4 and 8",
     reason="Records the human lead's answer on the wheels and the context of the 36-hour sentence; states the download scope once, without rewriting the earlier records; places the acceptance of §15 departures with the lead's approval record; updates the pending line.",
     new="**Human lead's answer on the package wheels — 2026-11-15 (UTC), verbatim:**\n\n"
         "> " + WHEELS_V + "\n\n"
         "The third clause answered the lead's question: " + WHEELS_Q + " (The first two clauses answer other questions.)\n\n"
         "Recorded by the lead:\n\n"
         "- **The package wheels for the one-off data-generation step are approved:** the eight packages named in §14.2 and the dependencies the resolver requires for them, pinned in the requirements file of the freeze, installed with `uv run --locked --with`; `uv.lock` and `pyproject.toml` do not change. The eight named packages come to about 23 to 32 MB; the transitive dependencies are recorded at fetch time.\n"
         "- **The two symmetry-check link files (6.2 MB) were not named in the answer and stay not approved.** The lead has asked again. Until an answer names them they are not fetched and the symmetry check is not made (§14.1).\n"
         "- **Context of the second quotation at the head of this section** (\"im confortable with does number …\"): it answered the lead's message listing S0 16 h, S1 12 h, S2 36 h, total 64 h. The human lead has since raised S1's cap to 16 h; S2's 36 h is unchanged. §15 item 3 rests on it.\n\n"
         "**Download scope as revision 5 states it** (one statement for §4.2, §14.1, §14.2 and §16; it adds no approval and removes none):\n\n"
         "- Approved by the human lead and recorded above: the two teachers, the student, the Tatoeba data; the fallback teacher and the fallback (Spanish) data only if the fallback rule of §4.2 is invoked; the package wheels for the one-off data-generation step.\n"
         "- Not approved, open with the human lead: the 6.2 MB of symmetry-check link files; any package outside the lock other than those wheels.\n"
         "- Nothing in the open list is fetched before a recorded answer. Implementation and tests on synthetic stand-ins need none of it.\n"
         "- The re-check's paste-ready edits to the earlier records (E-J3 for item 1, E-J4 for item 2 and for the last bullet) are not applied to those records: the lead's correction keeps them as written and supersedes them. E-J3's \"fetched in the same session\" is not adopted (§14.1).\n\n"
         "**§15 departures 1, 4, 5 and 7 (J9).** Their acceptance is for the lead's approval record, under the delegation " + DELEG + ". It is not given in this revision.\n\n"
         "Lead's approval: PENDING. Revision 5 answers the re-check (majors J1–J8, minors J9–J14 and others; §21) and awaits an independent confirmation.")

# ---------------------------------------------------------------- §20, §21, closing lists
over("C55", edit=[
    ("| J8b scope of R | second gates stage and independent recomputation inside R and inside the 36 hours | recomputation charged outside R, or outside the cap | §13.2, §13.3 |",
     "| J8b scope of R | second gates stage inside R and the 36 hours; the independent recomputation not charged (the P9-I / P9-II convention), within the memory limits, and no result reported before it completes | the recomputation inside R | §13.2, §13.3 |\n"
     "| P9 reference test | tensors passed explicitly to the P9 forward; `ScalableMemory` never constructed from a seed; the test is dropped, and the report says so, if that needs an edit of P9 | constructing the P9 module with a seed | §3 |"),
])

over("C57", new="\n7. The choices of revision 5 listed at the end of §20, each with its alternative. The heaviest in consequence: training draws that overlap between replicates; the oracle-code seed per replicate; the recomputation outside the charged hours.")

over("C58", reason="The reserved items are answered except the link files.",
     new="- The human lead's answer still open: the two symmetry-check link files (§16); the lead has asked again.")

over("C59", reason="The reviewer did check sacrebleu; the resolution is run when the wheels are fetched.",
     new="- That the package set of §14.2 resolves with torch 2.8.0 on Python 3.12. Not run; it is run when the approved wheels are fetched (§16 step 5).")

over("C60", edit=[
    ("| J4 (major) wheels not in the figure | Wheels and packages outside the lock stated as not approved and open; sizes from the saved index records where they exist |",
     "| J4 (major) wheels not in the figure | The figure's content stated; the human lead's later approval of the wheels recorded; the link files stay open; sizes from the saved index records where they exist |"),
    ("| J8 (major) rung rule | Slower of the two read layers' rates at U = 1,000; second gates stage and recomputation inside R; projection restated; NOT STARTED: BUDGET |",
     "| J8 (major) rung rule | Slower of the two read layers' rates at U = 1,000; second gates stage inside R and shown in the rung table; recomputation not charged, by the P9-I / P9-II convention; NOT STARTED: BUDGET |"),
    ("4. **E-J8, rates.** The re-check's text used the rates of the re-selected setting. Revision 5 uses the slower of the two read layers' rates.",
     "4. **E-J8.** The re-check's text used the rates of the re-selected setting; revision 5 uses the slower of the two read layers' rates. The re-check's text also charged the independent recomputation inside R; by the lead's ruling it is not charged, following the P9-I / P9-II convention (§13.3)."),
    ("the handling of a later fallback export, and the consequence for the projection of counting the recomputation inside R.",
     "the handling of a later fallback export, the rule for the P9 reference test, the rebuilding of partitions for a fallback language, and the projection of the second gates stage."),
])
