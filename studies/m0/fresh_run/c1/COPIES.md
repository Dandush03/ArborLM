# C1 run copies (stage 1S point 3)
Originals are the files at `b78e58b1` (`git show b78e58b1:<path>`). Written by `make_c1_copies.py`. Every other C1 script is run as committed.

## f5_closed_forms.py
- original path: `docs/reviews/m0-lineage-decision-2026-11-25/final_c1/f5_closed_forms.py`
- original SHA-256 (of `git show b78e58b1:docs/reviews/m0-lineage-decision-2026-11-25/final_c1/f5_closed_forms.py`): `9c9936546d9abe70446370ba35301fc00b3c357ea9662bcf218deffe1ab74d75`
- copy path: `studies/m0/fresh_run/c1/f5_closed_forms.py`
- copy SHA-256: `7e9455104d0cdb2f2b4cf6f51a2dc2a5abbf50befbbad44d38a00aa1f2604e49`
- hunks: 1. Kind **S2 (b)**: the entry `"C1.sieve_marking_f4": sieve` of `FNS` (a lineage not on the survivor list of record) is removed; the other four entries are unchanged.
- not changed, by choice: the inline map of base file names inside `main()` also has a `C1.sieve_marking_f4` key; no `FNS` key reaches it any more, so it is dead; the function `sieve` stays defined. Neither is an entry of `FNS`; the diff is the one line.

```diff
--- a/docs/reviews/m0-lineage-decision-2026-11-25/final_c1/f5_closed_forms.py
+++ b/studies/m0/fresh_run/c1/f5_closed_forms.py
@@ -139 +139 @@
-FNS = {"C1.sieve_marking_f4": sieve, "C1.fast_power_f4": fast_power, "C1.counter_list_f3": counter_list, "C1.func_branch_f4": func_branch, "C1.slices_f4": slices}
+FNS = {"C1.fast_power_f4": fast_power, "C1.counter_list_f3": counter_list, "C1.func_branch_f4": func_branch, "C1.slices_f4": slices}
```

## f5b_closed_forms_v2.py
- original path: `docs/reviews/m0-lineage-decision-2026-11-25/final_c1/f5b_closed_forms_v2.py`
- original SHA-256 (of `git show b78e58b1:docs/reviews/m0-lineage-decision-2026-11-25/final_c1/f5b_closed_forms_v2.py`): `c7d4c7fbf40b6e5df6eef82ca7103dea5774870eeeec955d99fed0cc54e50564`
- copy path: `studies/m0/fresh_run/c1/f5b_closed_forms_v2.py`
- copy SHA-256: `3429dcda6f69921d789be38607a8af81a42d4d0562f7e86466b32fe385790a37`
- hunks: 1. Kind **S2 (b)**: the entry `"C1.sieve_marking_f4": sieve` of `FNS` (a lineage not on the survivor list of record) is removed; the other four entries are unchanged.
- not changed, by choice: the inline map of base file names inside `main()` also has a `C1.sieve_marking_f4` key; no `FNS` key reaches it any more, so it is dead; the function `sieve` stays defined. Neither is an entry of `FNS`; the diff is the one line.

```diff
--- a/docs/reviews/m0-lineage-decision-2026-11-25/final_c1/f5b_closed_forms_v2.py
+++ b/studies/m0/fresh_run/c1/f5b_closed_forms_v2.py
@@ -140 +140 @@
-FNS = {"C1.sieve_marking_f4": sieve, "C1.fast_power_f4": fast_power, "C1.counter_list_f3": counter_list, "C1.func_branch_f4": func_branch, "C1.slices_f4": slices}
+FNS = {"C1.fast_power_f4": fast_power, "C1.counter_list_f3": counter_list, "C1.func_branch_f4": func_branch, "C1.slices_f4": slices}
```
