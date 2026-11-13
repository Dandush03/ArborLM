# ArborLM — Scientific Paper Outline (living draft)

**Not a submission or evidence of success. No results yet.** Authorship is a human decision. AI tools may assist with drafting and must be disclosed under applicable venue policies.

## Candidate title
**ArborLM: Learning Hierarchical Parameter Memory for Storage-Aware Language Modeling**

## Abstract scaffold
- Problem: total learned model capacity exceeds fast memory; disk-streamed inference suffers from parameter transfer and random-access costs.
- Approach: trainable, sparse, hierarchical neural parameter memory integrated into a small causal backbone; optional I/O-aware regularization and clustered storage.
- Methods: dense, flat memory, fixed hierarchy, learned hierarchy; RAM-first then checkpoint-identical SSD studies.
- Results: **PENDING — never write unmeasured numbers.**
- Implications/limitations: **PENDING.**

## Sections

1. **Introduction:** bandwidth/memory wall; original question, learning to reduce accessed parameters rather than just move/compress them faster.
2. **Related work:** product-key memory, memory layers, UltraMem, UltraMemV2, expert offloading, storage-aware routing, hierarchical KV memory; explicitly explain differences and overlaps.
3. **Formal problem:** total vs active parameters, physical I/O, objective and constraints.
4. **ArborLM method:** backbone, router, branch selection, lookup, fusion, loss, training topology, physical placement.
5. **Experimental setup:** datasets/licenses, compute/hardware, fair baselines, seeds, implementation and hyperparameter budgets.
6. **Results:** held-out quality, I/O per token, latency, compute/accuracy Pareto, scaling (if supported).
7. **Ablations:** tree vs flat, fixed vs learned, topology updates, locality loss, top-k, cache conditions.
8. **Failure modes/limitations:** random I/O overhead, training collapse, sensitivity, accuracy trade-offs, hardware dependence.
9. **Reproducibility and ethics:** code/data/reproduction paths, human oversight/AI assistance, licenses, resource use.
10. **Conclusion:** exactly supported conclusions and open questions.

## Tables/figures to prepare

- Quality vs active FLOPs/token, with total parameters separately labelled.
- Physical disk read bytes/token and end-to-end decode tok/sec, cold and warm.
- Memory size versus achieved quality, fixed backbone and selected-memory count.
- Router entropy, branch usage distribution, temporal and spatial locality.
- Architecture diagram and end-to-end disk read trace.
- Prior-work comparison (claim/architecture/scale/storage-awareness/novelty difference).

## Publication checklist

- Complete related-work review including papers released after project launch.
- Preserve pre-registration, run hashes and raw data.
- Reproduction commands plus training/eval hyperparameters and accessible model assets as appropriate.
- Confirm all sources/datasets/checkpoints can be shared under license.
- Check current venue anonymity and AI-use policies; do not assume the repo can be named in a blind submission.
- Use human authorship decisions. AI agent is not listed as co-author.

Reference: https://neurips.cc/public/guides/PaperChecklist
