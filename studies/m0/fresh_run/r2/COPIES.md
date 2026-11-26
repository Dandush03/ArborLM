# R2 run copies (units R2a, R2b)

Originals are the files at `b78e58b1` (`git show b78e58b1:<path>`). Diffs are `diff -U0 original copy` (written by `build_r2_copies_md.py`; the copies were built by `build_r2_copies.py`).
Environment variable read by every S1 line: `M0_FR_TAG`; its value is the decimal text of the unit's `tag` seed integer (run plan).
Self-check, not independent review. No S2a copy, no S3 copy and no S4 edit is made (reasons at the end).

## `studies/m0/fresh_run/r2/r2_fix4_battery.py`

- original: `studies/m0/r2_fix4_battery.py`
- original SHA-256: `2e48179bf194be7e00411e44e982e7be1c35ab2b0f1a0434fdee8a288ef8b618`
- copy SHA-256: `920d246080a23e36e412a3ae2c669c9864cc1184c4a170cc17f741bbacfed0f9`

```diff
--- a/studies/m0/r2_fix4_battery.py
+++ b/studies/m0/fresh_run/r2/r2_fix4_battery.py
@@ -90 +90 @@
-    tag = "a4r2" if seeds == "a4" else "fix4"
+    tag = "a4r2" if seeds == "a4" else __import__("os").environ["M0_FR_TAG"]
```

- hunk at original line 90: S1 (string-seed tag `fix4` -> environment variable)

## `studies/m0/fresh_run/r2/f_rules.py`

- original: `docs/reviews/m0-lineage-decision-2026-11-25/final_r2/f_rules.py`
- original SHA-256: `1f29b2b6740a25d034fba7884b189b2a247d3959210c845c8e4e8bd9beef3449`
- copy SHA-256: `5f5fcee11234d40c4df1d603bc851ce6cfdf0a92f506f135a74281b0f93d297f`

```diff
--- a/docs/reviews/m0-lineage-decision-2026-11-25/final_r2/f_rules.py
+++ b/studies/m0/fresh_run/r2/f_rules.py
@@ -61,2 +61,2 @@
-        rtr = random.Random(f"finalr2|{lid}|{lv}|5")
-        rte = random.Random(f"finalr2|{lid}|{lv}|6")
+        rtr = random.Random(f"{__import__('os').environ['M0_FR_TAG']}|{lid}|{lv}|5")
+        rte = random.Random(f"{__import__('os').environ['M0_FR_TAG']}|{lid}|{lv}|6")
```

- hunk at original line 61: S1 (string-seed tag `finalr2` -> environment variable, train and test lines)

## `studies/m0/fresh_run/r2/f_rules_new.py`

- original: `docs/reviews/m0-lineage-decision-2026-11-25/final_r2/f_rules_new.py`
- original SHA-256: `3fa3efa21f11a3eb8534e89a8d0a024ccc5f433d5a3dce99e2a7ec09c80cd35a`
- copy SHA-256: `5b3019ced2307d9ab7776158151df14f7e33e74e2fcac73d527352f60c487dc0`

```diff
--- a/docs/reviews/m0-lineage-decision-2026-11-25/final_r2/f_rules_new.py
+++ b/studies/m0/fresh_run/r2/f_rules_new.py
@@ -29 +29 @@
-        rte = random.Random(f"finalr2|{lid}|{lv}|6")
+        rte = random.Random(f"{__import__('os').environ['M0_FR_TAG']}|{lid}|{lv}|6")
```

- hunk at original line 29: S1 (string-seed tag `finalr2` -> environment variable, test line)

## `studies/m0/fresh_run/r2/f_new_heur.py`

- original: `docs/reviews/m0-lineage-decision-2026-11-25/final_r2/f_new_heur.py`
- original SHA-256: `bbb0c233b607df80049a3a659007e846401630551f21fe3cb5518c7550d1975c`
- copy SHA-256: `30710a0f7e0efd0af79e946f099a7071eb89d73c39c47f7b12d23b611bb2e62b`

```diff
--- a/docs/reviews/m0-lineage-decision-2026-11-25/final_r2/f_new_heur.py
+++ b/studies/m0/fresh_run/r2/f_new_heur.py
@@ -56,10 +55,0 @@
-@rule("interval_scheduling", "(cue) fewest clashes first (ties by end, then number)")
-def _(s, q):
-    ms = _meet(q)
-    cl = lambda x, y: x[1] < y[2] and y[1] < x[2]
-    deg = {m[0]: sum(cl(m, o) for o in ms if o is not m) for m in ms}
-    chosen = []
-    for m in sorted(ms, key=lambda m: (deg[m[0]], m[2], m[0])):
-        if all(not cl(m, c) for c in chosen):
-            chosen.append(m)
-    return ", ".join(str(i) for i in sorted(c[0] for c in chosen))
@@ -68,6 +57,0 @@
-@rule("interval_scheduling", "(cue) keep every meeting that clashes with no shorter meeting")
-def _(s, q):
-    ms = _meet(q)
-    cl = lambda x, y: x[1] < y[2] and y[1] < x[2]
-    keep = [m for m in ms if not any(cl(m, o) and (o[2] - o[1]) < (m[2] - m[1]) for o in ms if o is not m)]
-    return ", ".join(str(i) for i in sorted(m[0] for m in keep))
@@ -76,4 +59,0 @@
-@rule("digit_root", "(cue) digit sum once, last digit")
-def _(s, q):
-    n = re.search(r"Add up the digits of (\d+)\.", q).group(1)
-    return str(sum(map(int, n)) % 10)
@@ -82,4 +61,0 @@
-@rule("digit_root", "(cue) digit sum once, first digit")
-def _(s, q):
-    n = re.search(r"Add up the digits of (\d+)\.", q).group(1)
-    return str(sum(map(int, n)))[0]
```

- hunk at original line 56: S2b (entries of `interval_scheduling`, rule 1: lineage not on the survivor list)
- hunk at original line 68: S2b (entries of `interval_scheduling`, rule 2)
- hunk at original line 76: S2b (entries of `digit_root`, rule 1: lineage not on the survivor list)
- hunk at original line 82: S2b (entries of `digit_root`, rule 2)

## Kinds not used, and why

- S2a: not needed. `r2_fix4_battery.py` takes its lineages from `--only` and `f_rules.py` from argv[3] (names without `R2.`); the run plan gives the 17 survivors there.
- S3: not needed. No absolute or scratch path in the four files; `REV` of `f_rules.py` is relative to the working directory, which the plan sets to the worktree root (R-49).
- S4: no edit. `f_rules_new.py` has `from f_new_heur import NEW` (lines 24 and 54). Run as a file from `studies/m0/fresh_run/r2/`, its own directory is `sys.path[0]`, so the line resolves to the copy `f_new_heur.py` next to it (UNITS.md D4, REPORT D4). The plan's `PYTHONPATH` is the worktree root alone, so the original directory `final_r2/` is not on the path.
- Imports of `studies.m0.*` modules are untouched: none of them is copied.
- Each S1 line uses `__import__("os")` inline so that no import line is added.
- S2b on `f_new_heur.py`: only the four decorated entries (decorator line through the last body line) are deleted; the blank lines between them are left; the helper `_meet`, now unused, stays (it is not an entry).
