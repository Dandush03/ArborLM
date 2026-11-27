# Process log (auditor, kept as it happened)

- 14:22:22Z judgement part 1 (clusters, partition) hashed: JUDGEMENT_PART1_SHA256.txt.
- Then read lineages_r1_clusters.py through strip_doc.py (code only).
- DEVIATION: a `grep -rn ... studies tests` for where pilot lineages are wired into core.REGISTRY also matched
  studies/m0/NOTES_LINEAGE_REPAIR.md lines 76, 80 and 107 and the manifest note in r1_pilot_manifest.json line 565, and
  printed them, BEFORE my full judgement (revised shapes, keys, shortcuts) was written and hashed. Content seen: lead rulings
  A-E as recorded by arbor-lead (strict reading; "no strict cluster in both parts, parts by core.family_partition's rule";
  mandatory shortcut gate; fix or mark NOT REGISTERED; drop op-profile similarity); the author's statement that its
  family-closure reading of ruling B is its own ("ruling needed"), the 43 / 31 / 13 / 18 figures, the six-family key, and
  that the raw rule over the 16 original families would split two cross-part clusters; "NOT REGISTERED: none"; manifest
  note "No second solvers exist yet; none of these lineages is registered in core.REGISTRY". Nothing about similarity of the 8
  new lineages or about the revised shapes' defects was seen. My cluster judgement (part 1) predates this and is hashed.
- text_solvers attempt 1 (text_solvers_run1.txt): 3,500 false mismatches on conditional_threshold_rule_r3 from MY regex bug
  (matched "or no." in "Answer yes or no."). Fixed in text_solvers.py (comment at the fix). Kept run1.
- DEVIATION: strip_doc.py, show.py and text_solvers attempt 1 were run with system python3 (3.x, no repo imports), not
  `uv run --locked --offline`. All later numeric runs use uv run --locked --offline.
- heuristics run1 (heuristics_reg_run1.txt): MY ERROR: venn heuristic "M:sign_error_on_triple" (T - S + P - t) is in fact the
  correct inclusion-exclusion formula, so its 1.000 is expected and is not a shortcut. Renamed in run2 to
  "PROCEDURE_CHECK:inclusion_exclusion" and replaced by an extra auditor heuristic. run1 kept.
