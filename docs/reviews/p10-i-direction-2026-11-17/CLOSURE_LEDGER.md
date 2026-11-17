# P10-I — closure ledger for P1 to P10 (drafted 2026-11-17 UTC)

**Status: DRAFT — NOT APPROVED. Nothing under this ADR is implemented, calibrated, frozen or run.**

This file is a ledger, not a specification and not an ADR. It is the ledger asked for in `DIRECTION.md` section 6. It maps each open issue of the programme to one disposition. It revises no result, threshold, seed or outcome, reopens no study, and authorizes nothing. Every disposition is a proposal of the lead (Claude Fable 5.2) for the human lead to approve. ADR-0023 to ADR-0029 are proposed numbers; none of those ADRs is approved. ArborLM is unproven research; no row below is a success claim. `Astra review: NOT_PERFORMED`. Claude review is not Astra review.

## 1. How to read it

| Disposition | Meaning |
|---|---|
| CLOSED AS RECORDED | The registered status stands and no P10-I study takes the item. It does not mean the question is answered. Rows marked "unresolved" stay visible as unresolved. |
| SUPERSEDED BY \<study\> | A later study that has already run asked the item's question in another registered form. The original status stands. |
| CARRIED INTO \<P10-I study\> | The unanswered part is proposed for that study's specification. The original status stands. "Candidate" means `DIRECTION.md` does not bind the study to it; the drafter of that ADR accepts or declines it in writing. |
| RESERVED FOR THE HUMAN LEAD | No study can settle it. No ruling is proposed here. |

Proposed studies: P10-I-S0 (ADR-0023, addressing and overload), S1 (ADR-0024, capacity scaling), R (ADR-0029, frozen-checkpoint routing diagnosis; split out of ADR-0024 on the reviewer's and the lead's recommendation; the human lead ruled "Keep ADR-0029" on 2026-11-17), S2 (ADR-0025, sequential teacher transfer), S3 (ADR-0026, longer training), S4 (ADR-0027, quality against cost, conditional), S5 (ADR-0028, physical SSD, conditional).

Labels in the second column are copied from the record named in the third. Paths are relative to the repository root.

## 2. P1 to P7 (ADR-0005 to ADR-0014)

| Item | Original registered status (verbatim label) | Record (path) | Disposition | Named study | Note |
|---|---|---|---|---|---|
| P1, P2, P3-LT memory dependence under joint training | "promotion threshold missed"; "memory effects below registered sensitivity"; "Both memory-dependence flags failed their mean thresholds" | `docs/RESEARCH_LOG.md` (P1, P2, P3-LT entries); `results/p3-lt-2026-11-12/` | CLOSED AS RECORDED | — | Joint training. P10-I-S3 studies the frozen-backbone memory and does not re-read these. |
| P4: dense adapter against memory | "dense had lower loss in all 27 matched comparisons"; "Dense tolerance, the secondary advantage flag, and the composite criterion failed" | `results/p4-2026-11-12/`; ADR-0009 | CARRIED INTO | P10-I-S3 | `DIRECTION.md` section 4. S3's 512-update point is a new measurement; P4 is not revised. |
| P4: capacity and slot association | "meeting the registered capacity and slot-association criteria" (C and P positive in 27 of 27) | `results/p4-2026-11-12/` | CLOSED AS RECORDED | — | Bounded finding at 512 updates and 198,401 trainable parameters. |
| P5: dense-reference criteria | "All dense-reference criteria and the full learned-hierarchy criterion failed" | `results/p5-2026-11-13/README.md`; ADR-0010 | CARRIED INTO | P10-I-S3 | Competitiveness against the dense adapter only. The composite stays FAILED. |
| P5: learned routing and latency | "**R failed**"; "both L criteria failed" | `results/p5-2026-11-13/README.md` | CLOSED AS RECORDED | — | The P5 review notes the router's limited gradient path (`docs/reviews/p5-claude-review-2026-11-13/README.md`). Routing on P10 checkpoints is a new question in P10-I-R (ADR-0029). |
| P6-E timing | SP, PAR and PR "**INCONCLUSIVE**" | `docs/reviews/p6-results-2026-11-13/README.md`; ADR-0011 | CLOSED AS RECORDED | — | Not re-timed. No efficiency claim follows. |
| P6-Q routing fidelity | "all four flags FAIL for both tree kinds" | same | CLOSED AS RECORDED | — | Applies to the P5 checkpoints only. |
| P7-A | "CONCENTRATION-ONLY for both tree kinds" | `docs/reviews/p7a-results-2026-11-13/README.md`; ADR-0013 | CLOSED AS RECORDED | — | Simulation of page misses, not a storage measurement. |
| P7-B outcome | "WITHIN 10% OF FLAT CO-ACCESS, REPLICATED"; "The hierarchy-specific locality hypothesis failed" | `docs/reviews/p7b-results-2026-11-13/README.md`; ADR-0014 | CLOSED AS RECORDED | — | |
| P7-B question "Redesign or stop" | "do not scale the existing hierarchy on storage-locality grounds" (choice left to the human lead) | same, section 9 | SUPERSEDED BY | P8 (ADR-0015) | The overnight direction authorized P8, which tested H3 directly. The recommendation itself stands. |
| H4 (SSD viability), handoff hypothesis | "H4 and H5 remain untested" | ADR-0015 section 17; `docs/RESEARCH_HANDOFF.md` | CARRIED INTO | P10-I-S5 | Conditional study; entry is the human lead's decision. |
| H5 (scaling), handoff hypothesis | same | same | CARRIED INTO | P10-I-S1 | P10-S1 gave no positive line (section 6). |

## 3. P8 and its supplement (ADR-0015, ADR-0016)

| Item | Original registered status (verbatim label) | Record (path) | Disposition | Named study | Note |
|---|---|---|---|---|---|
| P8 study status | "STUDY INCOMPLETE (55 of 60 cells simulated); NO CASE LOCALITY-POSITIVE"; decision `none` | ADR-0015 status line and section 17; `results/p8-2026-11-14/SUMMARY.md` | CLOSED AS RECORDED | — | P8 remains INCOMPLETE. The supplement does not complete it. |
| C04, C05 | "INCOMPLETE" | ADR-0015 section 17 | CLOSED AS RECORDED | — | Supplementary classes (QUALITY-FAILED on both panels) stay in the separate supplementary record. |
| C06 to C10 classes | COLLAPSED; CONCENTRATION-ONLY; QUALITY-FAILED; "NOT REPLICATED ACROSS PANELS"; QUALITY-FAILED | ADR-0015 section 17; `docs/reviews/p8-results-2026-11-14/HUMAN_DECISION.md` | CLOSED AS RECORDED | — | Accepted by the human lead ("yeah") with the stop-rule deviation disclosed. |
| H3 (locality objective) | "H3 was tested at one dose and not supported" | ADR-0015 section 17 | CLOSED AS RECORDED | — | Unresolved beyond one dose. No P10-I study tests a locality objective. |
| Supplement (five collapsed cells) | "EXECUTED ONCE … COMPLETE (5/5 cells) … The registered P8 study remains INCOMPLETE with decision `none`" | ADR-0016 status line; `results/p8-supplement-2026-11-14/` | CLOSED AS RECORDED | — | "the supplement tested nothing new" (`docs/RESEARCH_LOG.md`). |
| Three errors in the P8 review | Errata; "no P8 number or class changes" | `docs/reviews/adr-0017-design-2026-11-14/ERRATA_P8_REVIEW.md` | CLOSED AS RECORDED | — | |
| Review question 3: locality on a memory held at high utilization | Open question | `docs/reviews/p8-results-2026-11-14/README.md` section 9 | SUPERSEDED BY | P9 Lane C (ADR-0017) | Lane C took it up and is calibration blocked (section 4). |
| ADR-0015 status line | "PENDING HUMAN REVIEW" | ADR-0015 status line; `docs/reviews/p9i-consolidation-2026-11-15/CONSOLIDATION_RECEIPT.md` section 6 item 1 | RESERVED FOR THE HUMAN LEAD | — | The merge approval did not close the review. |
| P8 freeze `80f46ae` | Exists only on a local backup branch; mapped to `378aeac` | `CONSOLIDATION_RECEIPT.md` section 6 item 2; `docs/reviews/p8-results-2026-11-14/COMMIT_MAP.md` | RESERVED FOR THE HUMAN LEAD | — | Whether to preserve the pre-rewrite hashes. |

## 4. P9 lanes A to D, P9-I, ADR-0018, P9-II (ADR-0017, ADR-0018, ADR-0019)

| Item | Original registered status (verbatim label) | Record (path) | Disposition | Named study | Note |
|---|---|---|---|---|---|
| Lane A, capacity (H17-CAP) | "CALIBRATION BLOCKED … not scientifically failed" | ADR-0017 status line and section 15.2 | SUPERSEDED BY | P10-S1 (ADR-0021) | P10-S1 asked the capacity question on an oracle-addressed store. Its open parts are in section 6. H17-CAP was not tested. |
| Lane B, optimization and collapse (H17-UTIL) | same | same | SUPERSEDED BY | P9-II (ADR-0019) | P9-II studied collapse of learned addressing. The usage term of H17-UTIL was not tested by any study. |
| Lane C, locality (H17-LOC) | same | same | CLOSED AS RECORDED | — | Unresolved. Stays calibration blocked. No P10-I study tests simulated page locality; P10-I-S5 has its own entry criteria. |
| Lane D, incremental (H17-INC) | same | same | CARRIED INTO | P10-I-S2 (candidate) | Depends on ADR-0025 containing a retention measure for the first set. If it does not, the lane stays calibration blocked and closed as recorded. Draft ADR-0025 declines it with reasons (its section 13 item 7); the choice is item 3 of the reserved list. |
| P9 testbed calibration | "TASK_CEILING_FAIL at 4,096"; frozen-hidden probes near chance | `results/p9-calibration-2026-11-14/README.md`; `docs/reviews/p9-calibration-audit-2026-11-14/AUDIT.md` | CLOSED AS RECORDED | — | A measurement about that testbed. |
| P9-I outcome | "COMPLETE — NO_INTERFACE_SELECTED" | `results/p9i-run-attempt2-2026-11-15/OUTCOME.md`; ADR-0017 section 15.9 | CLOSED AS RECORDED | — | For the tested interfaces, within 8,192 updates. Accepted as a registered negative result. |
| P9-I attempt 1 | "stopped at the gates stage before any training" | `results/p9i-run-attempt1-2026-11-14/` | CLOSED AS RECORDED | — | |
| Natural-query generalisation | N natural query "FAILS" (at chance at every size) | `results/p9i-run-attempt2-2026-11-15/OUTCOME.md` | CLOSED AS RECORDED | — | Unresolved and kept visible (`DIRECTION.md` section 6). In P9-II and P10-S0 the memory is told the answer position in every arm. No P10-I study is directed to test natural queries. |
| P9-I diagnostics: address collapse; draw sensitivity of W7 | Diagnostic, "not registered results" | same; `docs/reviews/p9i-results-2026-11-15/REVIEW.md` | SUPERSEDED BY | P9-II (ADR-0019) | P9-II registered A0's unreliability across draws (4 of 16 at 4,096). |
| ADR-0018 | "WITHDRAWN as a separate ADR … Never approved; nothing was implemented or run under it" | ADR-0018 status line | SUPERSEDED BY | P9-I (ADR-0017 Part I) | Folded in by the human lead's decision (ADR-0017 section 15.3). |
| P9-II outcome | "COMPLETE — ADDRESSING-RELIABLE: A5-D (LABEL-FREE); IMPROVES ON A0 at 4,096, NOT DISTINGUISHED at 16,384" | `results/p9ii-run-2026-11-15/OUTCOME.md`; ADR-0019 section 16 | CLOSED AS RECORDED | — | Accepted by the human lead as registered. |
| P9-II audit F1: A5-D not probed at 65,536 | "SCALE PROBE UNINFORMATIVE"; carried-forward arm A0 | `results/p9ii-run-2026-11-15/OUTCOME.md` | SUPERSEDED BY | P10-S0 (ADR-0020) | S0 probed its candidate at 65,536 (3 of 3 draws; "not a qualification"). See section 5. |
| P9-II audit F2: mechanism of collapse | H19-A "not supported" | same | CLOSED AS RECORDED | — | Unresolved: the collapse is observed, the registered mechanism is not. |
| P9-II: A5-D against A0 at 16,384 | "NOT DISTINGUISHED FROM A0" | same | SUPERSEDED BY | P10-S0 (ADR-0020) | Replicated there with the same label. |
| P9-II README errors | Corrected in a separate file | `results/p9ii-run-2026-11-15/CORRECTION.md` | CLOSED AS RECORDED | — | |
| In-place correction of approved text (optimizer clause) | "PENDING LEAD REVIEW / human acknowledgement" | ADR-0017 section 15.4; `CONSOLIDATION_RECEIPT.md` section 6 item 4 | RESERVED FOR THE HUMAN LEAD | — | |

## 5. P10-S0 (ADR-0020)

Accepted by the human lead as registered and unchanged on 2026-11-16 (ADR-0020, last addendum). `OUTCOME.md` was written before the acceptance and says so.

| Item | Original registered status (verbatim label) | Record (path) | Disposition | Named study | Note |
|---|---|---|---|---|---|
| Outcome | "ADDRESSING-QUALIFIED (4,096 AND 16,384)", arm A5-D | `results/p10s0-run-2026-11-16/OUTCOME.md` | CLOSED AS RECORDED | — | Cited only with its caveat lines. For A5-D a confirmatory replication, not an unbiased first test. |
| Overload | "OVERLOAD NOT QUALIFIED" (1 of 10 cells at 8K facts on 4K slots; failures on held-out templates only) | same | CARRIED INTO | P10-I-S0 | Binding (`DIRECTION.md` section 4): several loads; convergence-based training length; the 0.90 threshold is not lowered. |
| One load, one training length | Design limit | same; `DIRECTION.md` section 5 | CARRIED INTO | P10-I-S0 | Design ceiling under the policy on limits. |
| A5-D against A0 at 16,384 | "NOT DISTINGUISHED FROM A0 at 16,384 slots (d = +1); H20-D reads not supported" | same | CARRIED INTO | P10-I-S0 (candidate) | Accepted caveat. |
| Record-length-free variant | "RECORD-LENGTH-FREE VARIANT: DOES NOT PASS" (2 of 10 and 0 of 10) | same | CLOSED AS RECORDED | — | Accepted caveat. "not evidence that the record length is required". Unresolved: draft ADR-0023 declines it with reasons (its section 16) and the confirmation review judged that sound. |
| 65,536 slots | "a probe only (3 of 3 draws, one initialization seed, per-draw bound 0.368); not a qualification" | same | CLOSED AS RECORDED | — | Unresolved: addressing at 65,536 is not qualified by any study. Draft ADR-0023 declines it with reasons, and no P10-I draft has a lane for it. |
| A1 and A2 | A1 "UNRELIABLE at 16,384 (H20-B CONTRADICTED)"; A2 "FAILS at both (H20-C CONTRADICTED)" | same | CLOSED AS RECORDED | — | |
| Condition 6 decided no class | Observation "for the design of later studies" | same | CARRIED INTO | P10-I-S0 | A design note; it changes nothing in P10-S0. |
| Presentation defects of `RESULTS.md` | Recorded, not corrected | same; `docs/reviews/p10s0-results-2026-11-16/REVIEW.md` | CLOSED AS RECORDED | — | "qualifies at 16,384 ONLY" for A0 does not stand as a qualification. |
| Sequential addition of facts | "moved to the integrated study or P10-I" | ADR-0020 section 12.2 | CARRIED INTO | P10-I-S2 (candidate) | Same question as Lane D; section 12.2 lists the design conditions. Draft ADR-0025 declines it with reasons; the choice is item 3 of the reserved list. |
| Learned addressing in the loaded regime | "OMITTED — NOT OVERLOAD-QUALIFIED" (lane L of P10-S1) | ADR-0021 section 25.17 | CARRIED INTO | P10-I-S0 (the licence) and P10-I-S1 (lane L) | A learned-address lane in a capacity study depends on S0's overload result. In draft ADR-0024 lane L is "to be specified in a revision" and is not approved with that draft. |
| Hour cap | 6.09 h charged of 22 h; every planned cell ran | `OUTCOME.md` | CLOSED AS RECORDED | — | P10-S0 was not stopped by a cap. |

## 6. P10-S1 (ADR-0021)

Accepted by the human lead as recorded on 2026-11-17 (`results/p10s1-run-2026-11-17/ACCEPTANCE.md`). No line is positive for the store. Every label below stays as printed.

| Item | Original registered status (verbatim label) | Record (path) | Disposition | Named study | Note |
|---|---|---|---|---|---|
| Capacity line; milestone question 1 | "CAPACITY-INCONCLUSIVE: F-OQ DEPENDENCE_FAILED; F-OQ-IVF DEPENDENCE_FAILED; T-OQ INTERMEDIATE; 16,384→65,536 NOT TESTED"; "Not established" | `results/p10s1-run-2026-11-17/OUTCOME.md` section 2; `ACCEPTANCE.md` | CARRIED INTO | P10-I-S1 | The alternative reading (CAPACITY-NEGATIVE (b)) is disclosed, not adopted. |
| Early-snapshot dependence condition | DEPENDENCE_FAILED from a_use ≥ 0.95 × raw accuracy at 2,048 updates (ratios 0.9425–0.9471); R2 fails it 12 times | `OUTCOME.md` section 4 finding 1; `ACCEPTANCE.md` ruling 1 | CARRIED INTO | P10-I-S1 | In the acceptance's carried list. The reference arm goes through every validity check in rehearsal. |
| 16,384→65,536 transition | "16,384→65,536 NOT TESTED" | `OUTCOME.md` section 2; ADR-0021 line 28 | CARRIED INTO | P10-I-S1 | Noted by the human lead in `ACCEPTANCE.md`. |
| Saturation line | "SATURATION-INCONCLUSIVE: F-OQ INTERMEDIATE; T-OQ SATURATION_NOT_MEASURED" | `OUTCOME.md` section 2 | CARRIED INTO | P10-I-S1 (candidate) | Not in the acceptance's list; the lead's proposal. |
| Efficiency line and the cell-combination rule | "EFFICIENCY-NEGATIVE (DENSE FASTER), sizes 1,024–16,384" | `OUTCOME.md` finding 2; `ACCEPTANCE.md` ruling 2 | CARRIED INTO | P10-I-S1 | A registered combination rule; each cell reported; analytic compute and measured training cost kept apart. The label is not reinterpreted. A matched-cost quality comparison belongs to P10-I-S4 if entered. |
| Registered throughput stage | "INCOMPLETE: failed after 1.4 s on a code defect"; throughput "NOT MEASURED" | `OUTCOME.md` section 3; ADR-0021 section 25.21 | CARRIED INTO | P10-I-S1 | Every registered stage is rehearsed against the frozen plan before Decision 2. Wall-time comparisons only on stages that can be isolated (`DIRECTION.md` section 7). |
| Supplementary throughput | Descriptive; "not the registered stage and enters no outcome line" | `results/p10s1-run-2026-11-17/supplement/`; `ACCEPTANCE.md` ruling 4 | CLOSED AS RECORDED | — | It does not repair the failed stage. Not measured efficiency of a system. |
| Seed-block section defect | 28 lines compare the wrong reads | `ERRATUM_SEED_BLOCK.md`; `OUTCOME.md` finding 3 | CARRIED INTO | P10-I-S1 | `RESULTS.md` kept as written. The analysis is tested on a synthetic registry, descriptive sections included. |
| Dense comparisons and matched compute at 32K/16K | "F-OQ and H8 DENSE AHEAD"; "DENSE HOLDS MORE AT SATURATION" | `OUTCOME.md` section 2 and finding 4; `ACCEPTANCE.md` | CARRIED INTO | P10-I-S1 | At matched compute F-OQ is ahead of D-OQ by 0.24–0.33 bits in 5 of 5 replicates; the labels come from matched updates and D-OQ's best snapshot. |
| Flat against tree quality gap | "hierarchy TREE_BEHIND" (read at U_P) | `OUTCOME.md` section 2; `LITERATURE_AND_ROUTING_NOTE.md` section 5 | CARRIED INTO | P10-I-R (ADR-0029) | Own outcome line. The label is not changed by the run-length figures. |
| Post-hoc index over the flat memory | F-OQ-IVF "DEPENDENCE_FAILED"; "conventional retrieval not sufficient for the three memory arms" | `OUTCOME.md` section 2; `audit/AUDIT.md` | CARRIED INTO | P10-I-R (ADR-0029) | Candidate recall reported beside accuracy, at more than one candidate count. |
| Dictionary baseline | "DICT DOMINATES ON THIS TASK" | `OUTCOME.md` section 2; `ACCEPTANCE.md` | CARRIED INTO | P10-I-S1 | The baseline is kept. Value a plain lookup cannot provide is unresolved; a later study has to show it. |
| Untuned memory learning rate | Memory arms 0.003 "untuned by design"; D-OQ calibrated | `OUTCOME.md` section 4 | CARRIED INTO | P10-I-S1 (candidate) | Not in the acceptance's list; the lead's proposal. |
| Smaller report defects | Finding 5 (dropped replicates, "185 cells read", unlabelled rehearsal timing, two cap figures) | `OUTCOME.md` finding 5 | CARRIED INTO | P10-I-S1 | Reporting requirements only. |
| Attempt 1 | "S1-INCOMPLETE" on an engineering stop caused by the lead | ADR-0021 sections 25.19–25.20; `attempt1/` | CLOSED AS RECORDED | — | Its cells were not opened. The lesson (frozen-input set; resumable stages) binds every P10-I specification. |
| Hour cap raised 49 to 53 h | Raised before the second freeze, with the human lead's word | `OUTCOME.md` section 1 | CLOSED AS RECORDED | — | Charged 25.39 h; no cut. |
| Exact-tie assertion | Made on the platform of record only | ADR-0021 section 25.23 | CLOSED AS RECORDED | — | |

## 7. P10-S2 (ADR-0022 and its addendum)

Accepted by the human lead as registered and unchanged on 2026-11-16 (ADR-0022, last addendum). No student was trained.

| Item | Original registered status (verbatim label) | Record (path) | Disposition | Named study | Note |
|---|---|---|---|---|---|
| Outcome; the transfer question | "TRANSFER-INCONCLUSIVE: TEACHERS-NOT-QUALIFIED"; the question is "**not tested**" | `results/p10s2-datagen-2026-11-16/README.md` | CARRIED INTO | P10-I-S2 | Nothing supports or contradicts transfer. |
| Count gates | Q_check accepted 78 and 22 against 150; pools 7,804 and 2,341 against 8,000; quality conditions pass | same; `docs/reviews/p10s2-qualification-2026-11-16/REVIEW.md` | CARRIED INTO | P10-I-S2 | "Generate until met, within a stated budget" where the count is not the claim. No P10-S2 threshold is changed. |
| Gate inputs not stored | Major (auditability) | `REVIEW.md` finding 1 | CARRIED INTO | P10-I-S2 | Per-item inputs are persisted. |
| Word count undefined; thread-count dependence of teacher outputs | Minor; reproduction note | `REVIEW.md` finding 2; `README.md` | CARRIED INTO | P10-I-S2 | |
| Combined tasks C1, C2 and the strengthened COMPOSES rule | Approved and adopted; never run | `docs/decisions/ADR-0022-addendum-combined-tasks.md` | CARRIED INTO | P10-I-S2 (candidate) | Whether a sequential design keeps them is ADR-0025's choice. |
| Fallback teacher; eight data-step attempts | Not applicable; all attempts kept | `README.md`; `datagen_attempts/` | CLOSED AS RECORDED | — | |

## 8. Governance and record-keeping

| Item | Original registered status (verbatim label) | Record (path) | Disposition | Named study | Note |
|---|---|---|---|---|---|
| ADR-0012 (governance) | "PROPOSAL — PENDING HUMAN RESEARCH LEAD APPROVAL. Not in force." Approval record: "*Empty.*" | ADR-0012 status line and section 7 | RESERVED FOR THE HUMAN LEAD | — | No ruling is proposed. P6 to P10 ran under study-specific directions. |
| Astra review | "Astra review: NOT_PERFORMED" | every ADR and record from P1 to P10 | CLOSED AS RECORDED | — | Historically true and unchanged. Whether to seek one is ADR-0012 section 7 item 5. |
| Stale status lines | ADR-0017, ADR-0019 to ADR-0022 status lines predate their outcomes ("nothing implemented or run" in ADR-0020 and ADR-0022) | the ADRs; `CONSOLIDATION_RECEIPT.md` section 6 item 3 | RESERVED FOR THE HUMAN LEAD | — | The outcomes are in addenda and `results/`. The ADRs are immutable; a correction needs the human lead's word. |
| Platform of record | Bit-identical reproduction claimed for macOS arm64 only; manifests do not record OS or hardware | `CONSOLIDATION_RECEIPT.md` section 6 item 8; `docs/reviews/p10-consolidation-2026-11-16/` | CARRIED INTO | P10-I-S0 to S5 | Each specification names the platform of record and makes bit-exact assertions on it only. |
| Checks run locally | Local pass on the platform of record; it "does not show a pass on Linux" | ADR-0021 section 25.23 | CLOSED AS RECORDED | — | Each P10-I specification says so. |
| Repository clean-up, per-study reproduction lists, `CITATION.cff` | Task "for after the three P10 studies" | `docs/reviews/p10-design-2026-11-15/HUMAN_DECISIONS_2026-11-15.md` | RESERVED FOR THE HUMAN LEAD | — | Now due. Needs the human lead's yes on the deletion list and the author details. |
| `docs/RESEARCH_LOG.md` | Last entry: P9-II acceptance (2026-11-15) | `docs/RESEARCH_LOG.md` | RESERVED FOR THE HUMAN LEAD | — | Section 9. Append only. |

## 9. RESEARCH_LOG reconciliation

`docs/RESEARCH_LOG.md` ends with the human lead's acceptance of P9-II (2026-11-15 UTC). It is not edited here. The entries below would bring it through P10. They are proposed as an append-only change for the human lead's approval; no existing line changes. Dates are UTC. Merge commits were read from `git log` on `claude/p10-i-design`.

| # | Study | ADR | Date | Registered outcome or event | Record path |
|---|---|---|---|---|---|
| 1 | P10 design | ADR-0020, 0021, 0022 | 2026-11-15 | Three specifications drafted and reviewed; the human lead's decisions and delegations recorded. No outcome. | `docs/reviews/p10-design-2026-11-15/HUMAN_DECISIONS_2026-11-15.md` |
| 2 | P10-S1 calibration | ADR-0021 | 2026-11-15 | Calibration returned to the human lead; the capacity grid shifted down (revision 5). No outcome. | ADR-0021 sections 23–25; `results/p10s1-calibration-2026-11-15/` |
| 3 | P9-II and P10 design consolidation | ADR-0019 | 2026-11-16 | PR 8 merged (`68b1e64`; PR 7's head is its ancestor) after a test-only CI fix approved by the human lead. No study outcome changes. | `docs/reviews/p10-consolidation-2026-11-16/` |
| 4 | P10-S0 | ADR-0020 | 2026-11-16 | ADDRESSING-QUALIFIED (4,096 AND 16,384), arm A5-D; OVERLOAD NOT QUALIFIED; NOT DISTINGUISHED FROM A0 at 16,384. Recomputed (1,065 comparisons, 0 disagreements). Accepted as registered with its caveats. | `results/p10s0-run-2026-11-16/OUTCOME.md`; ADR-0020 last addendum |
| 5 | P10-S2 | ADR-0022 | 2026-11-16 | TRANSFER-INCONCLUSIVE: TEACHERS-NOT-QUALIFIED; stopped before the freeze on counts; no student trained. Accepted as registered. | `results/p10s2-datagen-2026-11-16/README.md`; `docs/reviews/p10s2-qualification-2026-11-16/REVIEW.md` |
| 6 | P10-I | — | 2026-11-16 | The human lead: P10-I waits for P10-S1's analysis; S1 is reviewed and merged first. | `docs/reviews/p10-design-2026-11-15/HUMAN_DECISIONS_2026-11-15.md` |
| 7 | P10-S1 attempt 1 | ADR-0021 | 2026-11-17 | S1-INCOMPLETE on an engineering stop caused by the lead; cells not opened; second attempt approved. | ADR-0021 sections 25.19–25.20; `results/p10s1-run-2026-11-17/attempt1/` |
| 8 | P10-S1 attempt 2 | ADR-0021 | 2026-11-17 | CAPACITY-INCONCLUSIVE; SATURATION-INCONCLUSIVE; EFFICIENCY-NEGATIVE (DENSE FASTER); milestone question 1 not established; 16,384→65,536 NOT TESTED. Registered throughput stage INCOMPLETE. Recomputed (1,085 comparisons, 0 differences). Accepted as recorded with every audit finding. | `results/p10s1-run-2026-11-17/OUTCOME.md`, `ACCEPTANCE.md`, `ERRATUM_SEED_BLOCK.md`, `audit/AUDIT.md` |
| 9 | P10-S1 supplement | ADR-0021 | 2026-11-17 | Supplementary throughput, descriptive only; not the registered stage. | `results/p10s1-run-2026-11-17/supplement/`; ADR-0021 section 25.21 |
| 10 | P10 consolidation | ADR-0020, 0021, 0022 | 2026-11-17 | PR 9 (P10-S0, `bfd9859`), PR 10 (P10-S2, `fccbd6d`) and PR 12 (P10-S1, `7111fbb`) merged into `main`; checks run locally on the platform of record. | ADR-0021 section 25.23 |
| 11 | P10-I direction | proposed ADR-0023 to 0028 | 2026-11-17 | Direction recorded: six studies, policy on limits, closure ledger. Not a specification; nothing approved to run. | `docs/reviews/p10-i-direction-2026-11-17/DIRECTION.md`, `LITERATURE_AND_ROUTING_NOTE.md` |

Each appended entry ends with `Astra review: NOT_PERFORMED`, as the existing entries do.

## 10. Reserved for the human lead

1. The ruling on ADR-0012. None is proposed here.
2. Approval of this ledger, and of each disposition marked SUPERSEDED BY for P9 lanes A and B. `DIRECTION.md` section 6 keeps the lanes calibration blocked "unless each is explicitly superseded"; that step is the human lead's.
3. Whether Lane D and the sequential addition of facts (ADR-0020 section 12.2) go into P10-I-S2, or stay closed as recorded.
4. Whether the items marked "candidate" are binding on the named specification.
5. Whether natural-query generalisation, Lane C (locality) and H3 stay without a successor in P10-I.
6. Approval of the append-only change to `docs/RESEARCH_LOG.md` (section 9), and who writes it.
7. The ADR-0015 status line ("PENDING HUMAN REVIEW"), the preservation of the P8 freeze hash `80f46ae`, the in-place correction recorded in ADR-0017 section 15.4, and the stale status lines of ADR-0017 and ADR-0019 to ADR-0022.
8. The repository clean-up list, the per-study reproduction lists and `CITATION.cff`.
9. Entry decisions for P10-I-S4 and P10-I-S5 (`DIRECTION.md` section 8). This ledger carries items towards them and authorizes neither.

`Astra review: NOT_PERFORMED`.

## Revision note (2026-11-17 UTC)

After the independent reviews of the drafts, the lead aligned this ledger with them: the routing diagnosis is P10-I-R (draft ADR-0029, split out of ADR-0024; ruled by the human lead on 2026-11-17: "Keep ADR-0029"); the record-length-free variant and the 65,536-slot item of P10-S0 are closed as recorded (unresolved) because draft ADR-0023 declines them; lane L is split between P10-I-S0 (the licence) and P10-I-S1 (the lane, not yet specified); Lane D and the sequential addition of facts are declined by draft ADR-0025 and stay with the human lead. No original status changed.
