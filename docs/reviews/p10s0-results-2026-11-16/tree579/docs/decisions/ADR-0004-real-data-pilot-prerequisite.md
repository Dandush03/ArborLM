# ADR-0004 — Small real-data pilot prerequisite

- Date: 2026-11-12
- Status: **DATA SELECTION APPROVED BY AUTHORIZED REVIEWER AND HUMAN FOR LOCAL PILOT**.
- Human record: the lead explicitly answered **“Approve WikiText-2 for local pilot”** in this project chat after reviewing the pinned 7.75 MB proposal and publisher license metadata. This approves local acquisition/use, not publication or redistribution.
- E0 remains the current implementation milestone. No dataset bytes have been downloaded for this proposal; only publisher metadata was inspected. No downstream model/training settings are approved by this document.

## Concrete acquisition proposal

After G0 acceptance, use the `wikitext-2-raw-v1` subset of [Salesforce/WikiText](https://huggingface.co/datasets/Salesforce/wikitext/blob/main/README.md), pinned to revision `b08601e04326c79dfdd32d625aee71d232d685c3`. The publisher card lists CC-BY-SA-3.0 and GFDL; retain the card, source/revision, attribution and license references alongside the local manifest. This records publisher metadata, not a legal determination or authorization to publish derived weights/data.

The repository API supplied the following sizes and SHA-256 LFS object IDs. Verify actual downloaded bytes against these before parsing; stop on mismatch or transfer beyond a 10 MB total payload cap. Exact directory at that revision: `wikitext-2-raw-v1/`.

| File | Bytes | Expected SHA-256 |
|---|---:|---|
| `train-00000-of-00001.parquet` | 6,357,543 | `e83889baabc497075506f91975be5fac0d45c5290b6b20582c8cd1e853d0c9f7` |
| `validation-00000-of-00001.parquet` | 657,209 | `204929b7ff9d6184953f867dedb860e40aa69c078fc1e54b3baaa8fb28511c4c` |
| `test-00000-of-00001.parquet` | 732,610 | `5f1bea067869d04849c0f975a2b29c4ff47d867f484f5010ea5e861eab246d91` |

Total corpus payload: 7,747,362 bytes. Preserve the official train/validation/test separation. Test content remains uninspected until a later preregistered final-evaluation decision; it must not be used to tune the pilot. Keep data local and ignored by Git. No external paid compute, deployment, pretrained model or dataset redistribution is part of this proposal.

## Why this prerequisite exists

The experiment protocol requires real openly licensed data before language-model quality claims, with an explicit dataset decision and contamination assessment. A tiny synthetic E0 cannot prove or disprove the concept. WikiText-2 is proposed as a small, identifiable real-text source with existing splits; it is not sufficient by itself to demonstrate broad generalization, reasoning or novelty.

Before training, a separate approved pilot specification must freeze tokenizer/preprocessing, boundary handling, duplicate/contamination audit, model and memory settings, dense/flat/fixed/learned controls, seeds, matched budgets and numerical gates. Strong product-key baseline adequacy and tuning/compute mismatches must be addressed explicitly. No pilot training is authorized solely by approving this data acquisition.

Human approval now permits these small local downloads and their use in the preregistered RAM-only pilot once G0 passes. Publication/release approval remains separate.

## Post-acquisition metadata observation

The pinned publisher README's front matter lists CC-BY-SA-3.0 and GFDL, while its later licensing paragraph says CC BY-SA 4.0. Preserve both statements and the exact README checksum; do not silently choose a governing license or rewrite the original acquisition record. This remains an unresolved licensing detail for any redistribution/release review. The human approved local use of the exact pinned corpus bytes; the local pilot proceeds within that authorization, with no claim of legal resolution or permission to publish corpus/weights. Raw acquisition records stay immutable and the observation is an appended provenance note.
