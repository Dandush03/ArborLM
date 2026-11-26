# ORDER.md — order of work of the independent partition audit (M0, 2026-11-26)

Auditor: arbor-auditor context, model Claude Opus 5.5 (claude-opus-5-5). Not Astra review; not human approval.

Step 1 (from the text alone). Read: AGENTS.md; experiments/_scratch/m0_fr_briefs_20261126/COMMON.md;
the approved addendum `git -C .../m0-spec-push-20261126 show 2c944302:docs/decisions/ADR-0033-addendum-1-lineage-clusters.md`
(copy saved as ../work/addendum1_2c944302.md, SHA-256 154d16a0597dc8b2d41179ded63a5da3e6e92aa4f7b414fefda1f93cd4d0923c),
sections 0, 3, 4, 4A (stages 2, 3), 13. To learn the input format I also read the top-level structure of
`studies/m0/manifests/map_of_record.json` (keys, counts, first entries; no partition computed).
Not opened before the hash below: studies/m0/registration/ (any file), partition_vector_rev*.py and their outputs,
partition_from_text_review3.py, partition_check4.py.

partition_audit.py, first version, written and saved:
  time   2026-11-26T16:54:35-0500
  SHA-256 fe9636827f010fcbe7cd9fbdde5982a0a05e0b07b4511e996e4a3a42c78927c8
  (frozen copy: ../work/partition_audit_v1.py, same hash)
