# M0 fresh run, stage 0: auditor derivation of the survivor list of record

Specification: ADR-0033 addendum 1 at `d70ba38d`, section 4A stage 0, "The survivor list of record", points 1-6.
Auditor model: Claude Opus 5.5 (`claude-opus-5-5`), running as the `arbor-auditor` context. I wrote none of the lineages, the rule scripts or the implementer's script. I did not read `studies/m0/fresh_run/` or `studies/m0/manifests/survivor_list_of_record.json`.
Astra review: NOT_PERFORMED. This is independent engineering evidence. It is not Astra validation or human approval, and it does not call anything a success.

## Environment and command
- Read-only inputs come through `git -C /Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f show <rev>:<path>` (that worktree's HEAD and `claude/m0-impl` are both `f627389a15ea1611ce5861df0b2bdec8f58e05ef`).
- `cd /Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f && PYTHONDONTWRITEBYTECODE=1 uv run --locked python /Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_fr_survivors_audit_20261126/deliver/derive_survivors_auditor.py`
- Python 3.12.14 (locked env, standard library only); git 2.54.0 (Apple Git-157); macOS (darwin).
- The script output is in `derive_survivors_auditor.out.txt`. The script's own hash is in `SHA256SUMS.txt`.

## Five input hashes (SHA-256 of `git show` bytes)
| Input | SHA-256 | Text | Match |
|---|---|---|---|
| `7cd0ac5a:studies/m0/manifests/r1_fix4_survivors.json` | `e1a7a092a709de28e7fdbf07c93f8451543841e1a407b6ff2ae5b9a2bd90749b` | `e1a7a092…749b` | yes |
| `7cd0ac5a:studies/m0/manifests/r2_fix4_survivors.json` | `2456dac6fd735f87ef3f4ba55f0c2058ae9226ae458e5be35732fc603425a102` | `2456dac6…a102` | yes |
| `7cd0ac5a:studies/m0/manifests/m1_fix4_survivors.json` | `153e68374e8f34dfdbd96fdab73085227e29165a7122247748f38331963d1986` | `153e6837…1986` | yes |
| `7cd0ac5a:studies/m0/manifests/c1_fix4_survivors.json` | `eaedec75b53e7d09b486596c1f78af3b2144bfd127a69c2587017fecb70d3603` | `eaedec75…3603` | yes |
| `b78e58b1:docs/reviews/m0-lineage-decision-2026-11-25/cross_evaluation_map/drops_after_final_checks.txt` | `b714f1026923a4b5f64fd34320d095f1ba0be2aac98218f0b506983cd3bf0bd5` | `b714f102…0bd5` | yes |

The text gives only the first 8 and last 4 hex digits of each hash, so the match checks those 12 digits and nothing more.
"Unchanged since": the git blob ids of all five files are identical at `7cd0ac5a`/`b78e58b1` and at the tip of `claude/m0-impl` (`f627389a`).

## Counts
| Eval | Read under point 2 | Less drops | Text | |
|---|---|---|---|---|
| R1 | 12 | 10 | 10 | equal |
| R2 | 19 | 17 | 17 | equal |
| M1 | 29 | 29 | 29 | equal |
| C1 | 27 | 26 | 26 | equal |
| Total | 87 | 82 | 82 | equal |

Drop ids (5): `R1.graph_shortest_route_r6`, `R1.conditional_decision_tree_r6`, `R2.digit_root`, `R2.interval_scheduling`, `C1.sieve_marking_f4`. All five appear in the list read under point 2, so **no drop id is missing**.
Point 5: all 8 capacity-held M1 lineages (from the field names of `capacity_as_written_failures_listed_for_the_lead`) and `R2.to_base_wide` are in the output.

Output: `survivor_ids_auditor.json` (format fixed by the brief; keys R1, R2, M1, C1; ids sorted with Python `sorted`, which gives code-point order).

## Ambiguities in reading the fields (field names only)
1. **R1, "lineage id".** Entries of `shapes` have no field called `id`. They have `name` and `earlier_id`. I used `name`, because `earlier_id` is null for most entries and holds the superseded id where it is set, and the drops file names R1 ids in the `name` form. If `earlier_id` were used, both R1 drops would fail to match and the script would stop. PENDING LEAD REVIEW only if the implementer read it differently.
2. **C1, "lineage id".** Entries of `lineages` have no field called `id`. I used `name`.
3. **R2, "every entry of `lineages`".** `lineages` is a JSON object (a dict keyed by id), not a list. I took the entries to be its values and read `id` from each. In every entry, `id` equals its key. The entries also carry a separate `status` field, which was not read, as point 2 requires.
4. **Drops file format.** The file has one comment line starting with `#`, followed by one id per line. I skip blank lines and `#` lines. The text does not specify how to parse the file. Exactly five ids result, which matches "five ids under lead ruling R-38".
5. **Abbreviated hashes**, as noted above.

## Fields and files read
- Probe 1 (`probe_field_names.py`) printed only key names and value types. Its first attempt failed because the Write tool refused the path. That attempt's error output is kept as `probe_field_names.out.txt`, and the successful run is in `probe_field_names.out2.txt`.
- Probe 2 (`probe_id_fields.py`) printed only these string fields: R1 `shapes[].name`/`earlier_id`/`status`; R2 per-entry key names, `id`, `status_before_capacity`; M1 `survivors`; C1 `lineages[].name`/`status`; the drops file text.
- Neither probe printed a figure. Key names in probe 1 output reveal that the manifests contain other fields (for example excess, capacity), but their values were not printed or used. No other file was read.
