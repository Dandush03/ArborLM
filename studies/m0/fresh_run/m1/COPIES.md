# COPIES.md: run copies for unit M1a (M0 fresh run, ADR-0033 addendum 1, section 4A stage 1S point 3)

Originals are `git show b78e58b1f47619f070dfc6c0a88999d345b1a34b:<path>`. Copies are written by `make_copies_m1.py` (same directory). Each hunk is one line and is one of S1 (seed from an environment variable), S2 (lineage set), S3 (path), S4 (import / importlib path). No S2 hunk exists in unit M1a: the 29 lineages are given on the command line by `--only` (see run_plan_m1.json).

Self-check, not independent review.

## m1_fix3_shortcuts.py

- original path: `studies/m0/m1_fix3_shortcuts.py`
- original SHA-256 (`git show b78e58b1:<path>`): `7eef7c7cb64195376d2424ce51b22db97c52b0164d894875310c3576a2552936`
- copy path: `studies/m0/fresh_run/m1/m1_fix3_shortcuts.py`
- copy SHA-256: `5961ccfc3388267d6d50a4d32e542b9ca3ed05ab5c24ae9306b50098a327c1ee`
- hunks:
  - S1: replaces `SEED = 410302  # throwaway integer, not a registered study seed`

```diff
--- a/studies/m0/m1_fix3_shortcuts.py (b78e58b1)
+++ b/studies/m0/fresh_run/m1/m1_fix3_shortcuts.py
@@ -29 +29 @@
-SEED = 410302  # throwaway integer, not a registered study seed
+SEED = int(__import__("os").environ["M1A_SEED_OWN"])  # throwaway integer, not a registered study seed
```

## shortcuts_a4.py

- original path: `docs/reviews/m0-lineage-decision-2026-11-25/audit4_m1/shortcuts_a4.py`
- original SHA-256 (`git show b78e58b1:<path>`): `bd5cd0ef84ccb23f51ae0a364059f4a23c71f12319a1efbf6ae7521943a1f088`
- copy path: `studies/m0/fresh_run/m1/shortcuts_a4.py`
- copy SHA-256: `f6f63e1aaed5a5bc8d02a89f1c65ba5868b6da0b6d6bc74e9d173452adbf6743`
- hunks:
  - S1: replaces `SEED = 17`
  - S4: replaces `from studies.m0.m1_fix3_shortcuts import spec`

```diff
--- a/docs/reviews/m0-lineage-decision-2026-11-25/audit4_m1/shortcuts_a4.py (b78e58b1)
+++ b/studies/m0/fresh_run/m1/shortcuts_a4.py
@@ -25 +25 @@
-SEED = 17
+SEED = int(__import__("os").environ["M1A_SEED_A4"])
@@ -174 +174 @@
-    from studies.m0.m1_fix3_shortcuts import spec
+    from studies.m0.fresh_run.m1.m1_fix3_shortcuts import spec
```

## shortcuts_a3.py

- original path: `docs/reviews/m0-lineage-decision-2026-11-25/audit3_m1/shortcuts_a3.py`
- original SHA-256 (`git show b78e58b1:<path>`): `7182713b0932ef6615bacf281c91eb73a37e8bca8098802a43cbafe0bba98a83`
- copy path: `studies/m0/fresh_run/m1/shortcuts_a3.py`
- copy SHA-256: `c3d0bd399cd35e36caee6eaab7e8b163fd3bce538388bfd7804d569d2505aeb2`
- hunks:
  - S1: replaces `SEED = 5`

```diff
--- a/docs/reviews/m0-lineage-decision-2026-11-25/audit3_m1/shortcuts_a3.py (b78e58b1)
+++ b/studies/m0/fresh_run/m1/shortcuts_a3.py
@@ -20 +20 @@
-SEED = 5
+SEED = int(__import__("os").environ["M1A_SEED_A3"])
```

## m1_fix4_battery.py

- original path: `studies/m0/m1_fix4_battery.py`
- original SHA-256 (`git show b78e58b1:<path>`): `d83e701f338b93ab54184a3d03ef41b717f538ca8a4a99368457c5416c0e5e6c`
- copy path: `studies/m0/fresh_run/m1/m1_fix4_battery.py`
- copy SHA-256: `17c3de3775bd888dccdd6cb46cea2f6138b4dc0227cd4d3900e0527f15e23d30`
- hunks:
  - S3: replaces `ROOT = Path(__file__).resolve().parents[2]`
  - S4: replaces `from studies.m0.m1_fix3_shortcuts import PROCEDURE`
  - S4: replaces `return _load(A4 / "shortcuts_a4.py", "shortcuts_a4_fix4")`
  - S4: replaces `return common, _load(A3 / "shortcuts_a3.py", "shortcuts_a3_fix4")`
  - S4: replaces `import studies.m0.m1_fix3_shortcuts as sc`

```diff
--- a/studies/m0/m1_fix4_battery.py (b78e58b1)
+++ b/studies/m0/fresh_run/m1/m1_fix4_battery.py
@@ -33 +33 @@
-ROOT = Path(__file__).resolve().parents[2]
+ROOT = Path("/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f")
@@ -62 +62 @@
-    from studies.m0.m1_fix3_shortcuts import PROCEDURE
+    from studies.m0.fresh_run.m1.m1_fix3_shortcuts import PROCEDURE
@@ -90 +90 @@
-    return _load(A4 / "shortcuts_a4.py", "shortcuts_a4_fix4")
+    return _load(ROOT / "studies" / "m0" / "fresh_run" / "m1" / "shortcuts_a4.py", "shortcuts_a4_fix4")
@@ -96 +96 @@
-    return common, _load(A3 / "shortcuts_a3.py", "shortcuts_a3_fix4")
+    return common, _load(ROOT / "studies" / "m0" / "fresh_run" / "m1" / "shortcuts_a3.py", "shortcuts_a3_fix4")
@@ -101 +101 @@
-    import studies.m0.m1_fix3_shortcuts as sc
+    import studies.m0.fresh_run.m1.m1_fix3_shortcuts as sc
```
