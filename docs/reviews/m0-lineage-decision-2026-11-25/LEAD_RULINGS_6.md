# M0 lineage repair: lead rulings after the narrow round, before the independent re-measurement (2026-11-25)

By the scientific lead (Claude Fable 5.2). Written before any auditor's re-measurement of the fix-4 sets was started. Nothing here registers a lineage.

Implementers' results (their own measurements, four `arbor-implementer` subagents, Claude Sonnet 5.5): R1 12 shapes in 10 clusters; R2 19 lineages in 18 clusters; M1 29 lineages in 17 clusters; C1 27 lineages in 18 clusters (16 without the two variants).

- **R-30 (G in the demand).** G in `10 x (ceil(4000/G) + ceil(20000/G) + 100)` is the number of clusters in ONE part, and the smaller part decides: G = floor(surviving clusters / 2). The lead's brief for the narrow round said "the number of surviving clusters", which was ambiguous; that is the lead's error. R1 and M1 used the per-part reading; R2 used the total (14,350 instead of 27,680) and is being recomputed.
- **R-31 (which rules count).** The rules counted against the bound are exactly the classes the audit-4 auditor of that evaluation counted in its "bound 0.15" column, because that table is what the human lead chose from: cheap rules. Rules the auditor classed as the correct procedure, as costly or partial-trace, or as artefacts are measured and reported but not counted. Lineages that would drop if they counted are listed for the human lead.
- **R-32 (which estimate decides).** Per lineage and level, the excess is the item-weighted pooled estimate over the implementer's primary and replicate seeds and the auditor's fresh seeds. Pooled excess above 0.15 in absolute value: dropped. This supersedes the R1 implementer's "primary run decides". A lineage already dropped stays dropped; nothing is brought back.
- **R-33 (correction).** The human lead's words set "a bound of 0.15". The two-sided reading is the lead's (R-3, R-24), not the human lead's words; `LEAD_RULINGS_5.md` R-24 and changelog row 45 credit it wrongly. It is listed for the human lead to confirm.
- **R-34 (unit).** The bound is applied per lineage and level over all of the lineage's shapes together, as audit 4 measured it. Within-shape rates are reported, not counted.
- **R-35.** Accepted: M1's level repairs of `average_missing` and `clock_duration` (collapsed levels in audit 4's profile); R1's drops of `event_timeline_r6` and `spatial_relative_directions_r6` under R-19; C1's drop of `majority_vote_scan_f3` on the audit figure.
- **R-36.** Lineages failing capacity only under `core.generate_pool` as written (M1: ages, consecutive, fraction_remainder, grid_perimeter, percent_change, pipes_work, ratio_share, rectangle) are held, neither counted as passing nor dropped, until the human lead decides the pool builder.
- **R-37 (slip).** The M1 implementer ran `ruff check --fix` over `studies/m0/`, touching other implementers' files. The tracked diff shows only import ordering; the full suite decides.

Astra review: NOT_PERFORMED
