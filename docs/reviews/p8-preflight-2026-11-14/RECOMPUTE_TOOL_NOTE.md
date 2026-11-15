# Changes to independent_recompute_p8.py (auditor tool), before any outcome

- Auditor: Claude Opus 5.5 (`claude-opus-5-5`). Not Astra validation, not human approval.
- When: 2026-11-14 UTC, before the freeze. No real P8 record existed yet, and only synthetic dry-run fixtures had been seen.
- Why: the lead's rulings on AUDIT_EVAL_SIM_ANALYSIS.md, relayed by the coordinator and to be written into ADR-0015 revision 3.

| Version | sha256 |
|---|---|
| v1 (as audited) | `bf8d84c9ddc79152455a1884b70dc28bf26a48853f89810e2ad78d2f8475f068` |
| v2 (this version) | `dc3e7269976b6fdcb8accf5189ab5709f1db9b94bf03b73c3d274b655e6f1acb` |

## What changed

1. **Retention (MAJOR-2 ruling).** Gain retention and association retention are now undefined when the baseline mean is ≤ 0. Previously they were undefined only when the baseline mean was exactly 0. An undefined retention fails the quality guard, as it already did in v1. I removed the v1 helper field `quality_passes_if_nonpositive_baseline_undefined`, because the ruling makes it the main rule.
2. **Undefined U-ratio (vii ruling).** LOC true with an undefined U-ratio gives INTERMEDIATE. v1 already did this, so there is no code change; only the docstring now cites the ruling.
3. **Decision map.** The new rules are:
   - **(a)** if C07 or C09 has an architecture advantage and the concentration controls do not bind;
   - **else (b)** if C06 or C08 is study-class LOCALITY-POSITIVE **and beats optimized flat**, no tree case (C02, C03, C05, C07, C09, C10) has an architecture advantage, and the controls do not bind;
   - **else (c)**.

   NOT REPLICATED and INTERMEDIATE regularized cases are now listed in `open_questions`, but they do not cancel (a) or (b). Compared with v1, (b) now also requires "beats optimized flat" and no tree architecture advantage, and the bind check is applied to each option instead of being tested first. Both versions give the same option whenever the controls bind.

Nothing else changed: m, E, the ratios, the OLS fit, the pair and parent counts, the classification order, the study class, beats-flat, the architecture advantage, the bind rule and the comparison code are all as in v1.

## Re-test on the dry-run fixtures

All runs compared against the implementation's analysis.json, which had **not yet been fixed** to the rulings.

| Fixture | Values compared | Max abs diff | Mismatches | What the mismatches are |
|---|---|---|---|---|
| Dry run | 2,060 | 0.0 | 58 | All retention fields: 21 gain, 35 association, 2 guard results. Each is a comparison whose baseline mean is ≤ 0, where v2 is now undefined. Classes and decision match: all QUALITY-FAILED, decision (c). |
| `stress_main` | 2,060 | 0.0 | 0 | None. |
| `stress_negbase` (≤ 0 baseline case) | 2,060 | 0.0 | 37 | All are consequences of the retention ruling. C06 is now QUALITY-FAILED (the implementation says LOCALITY-POSITIVE), so beats-flat flips and the decision is (c) where the implementation says (b). C04 and C08 stay QUALITY-FAILED in both, now because their retention is undefined. `open_questions` = [C10]. |
| `stress_inc` | 1,736 | 0.0 | 0 | None. INCOMPLETE 59/60, decision "none". |

These mismatches are expected until the implementer's fix lands. On the narrow re-check, the tool will be rerun unchanged and should report 0 mismatches.
