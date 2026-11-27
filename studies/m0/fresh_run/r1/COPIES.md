# M0 fresh run, stage 1S point 3: run copies of evaluation R1

Originals are the files at commit `b78e58b1f47619f070dfc6c0a88999d345b1a34b` (`git show b78e58b1f47619f070dfc6c0a88999d345b1a34b:<path>`). Self-check by the implementer context (Claude Sonnet 5.5); not an independent review, not Astra validation, not human approval.
Written by `studies/m0/fresh_run/r1/make_copies_md_r1.py`. A copy differs from its original only by the hunks listed, each placed under S1 to S4. Copies are not lint-fixed.

## `studies/m0/fresh_run/r1/r1_fix4_tells.py`

- original path: `studies/m0/r1_fix4_tells.py`
- original SHA-256: `047ed9b9e8bc904547937f7cfebbe1c3afd1e601a59511f9fa92927fbe1d68a7`
- copy SHA-256: `812e0d38c3c1c167e586091dfceac95b63943e43889b97c0e5eaf311f4eab45a`
- hunks: 1

  - hunk 1: S1: the four seed literals 8300, 8400, 8500, 8600 (fit and test roots of the two lookup groups) replaced by the integers read from the environment variables M0FR_R1A_FEAT1_FIT, M0FR_R1A_FEAT1_TEST, M0FR_R1A_FEAT2_FIT, M0FR_R1A_FEAT2_TEST (read inline with __import__, so that no import line is added)

```diff
--- a/studies/m0/r1_fix4_tells.py
+++ b/studies/m0/fresh_run/r1/r1_fix4_tells.py
@@ -59,3 +59,3 @@
     bs = base_of(lin.id)
-    for feats, fit_root, test_root in ((FEATS_1, 8300, 8400), (FEATS_2, 8500, 8600)):
+    for feats, fit_root, test_root in ((FEATS_1, int(__import__("os").environ["M0FR_R1A_FEAT1_FIT"]), int(__import__("os").environ["M0FR_R1A_FEAT1_TEST"])), (FEATS_2, int(__import__("os").environ["M0FR_R1A_FEAT2_FIT"]), int(__import__("os").environ["M0FR_R1A_FEAT2_TEST"]))):
         for name, f in sorted(feats.get(bs, {}).items()):
```

## `studies/m0/fresh_run/r1/r1_fix4_measure.py`

- original path: `studies/m0/r1_fix4_measure.py`
- original SHA-256: `daa131f157391f391017973a3fdb0ba24984648fb5d82beb217a412f67012a68`
- copy SHA-256: `cce2747a072a8aef83862f9e95f925f493d23a280ec491ebaa3a04127507ef72`
- hunks: 1

  - hunk 1: S4: the import of feature_rows from studies.m0.r1_fix4_tells redirected to its copy studies.m0.fresh_run.r1.r1_fix4_tells

```diff
--- a/studies/m0/r1_fix4_measure.py
+++ b/studies/m0/fresh_run/r1/r1_fix4_measure.py
@@ -25,3 +25,3 @@
     from studies.m0 import r1_fix4_gen as gen
-    from studies.m0.r1_fix4_tells import feature_rows
+    from studies.m0.fresh_run.r1.r1_fix4_tells import feature_rows
 
```

## `studies/m0/fresh_run/r1/new_rules_final.py`

- original path: `docs/reviews/m0-lineage-decision-2026-11-25/final_r1/new_rules_final.py`
- original SHA-256: `98b896e4f12caa23e8bd384c63a2ea36fce9c97bdf6d2d33de1df5d3c80e0b51`
- copy SHA-256: `a57be6728a81f710d001437eaad624243bd8362a4f683fe9c30e6aa5129bdf60`
- hunks: 1

  - hunk 1: S2b: the entry of SPEC (a table keyed by lineage) for R1.conditional_decision_tree_r6, which is not on the survivor list of record, removed; no other entry touched

```diff
--- a/docs/reviews/m0-lineage-decision-2026-11-25/final_r1/new_rules_final.py
+++ b/studies/m0/fresh_run/r1/new_rules_final.py
@@ -163,3 +163,2 @@
     "R1.compass_turns": {"rules": compass_rules},
-    "R1.conditional_decision_tree_r6": {"rules": dtree_rules},
 }
```

