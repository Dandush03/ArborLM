# NOTES_RECORDS (final_v3): what changed from final_v2

Self-check by the implementer; not independent review, not Astra validation. Astra review: NOT_PERFORMED.
final_v2/NOTES_RECORDS.md still describes the field map (item of stage 6 -> field), the family counts, section 9 item 5 and the
reason tiers; those are unchanged except as listed here.

- Record is `studies/m0/manifests/g_gen_record.json` with the status sentence given by the coordinator. `domain_list` is the content of the new input
  `studies/m0/manifests/domain_list.json` (decision, record path and hash of `HUMAN_LEAD_WORDS_13.md`, the section 6.8 rows, `code_writing: NOT MEASURED`).
  The script checks that file against the table of section 6.8 read from the ADR-0033 file and against the recorded hashes, and stops on any difference.
  For the run here the file was passed with `--domain-list` because it is not yet in the worktree; the record names it by its worktree path.
- Strictest counts follow R-65 (chain reading); `choice_left` is removed; the direct-pairs count is labelled `..._information_only_not_the_strictest_count`.
- `lead_rulings` lists `LEAD_RULINGS_8.md` and `LEAD_RULINGS_9.md` with the hash of the worktree file at run time. R-65 is not listed as a departure.
- The status record header now has `reason_tiers_of_the_263_not_registered_before_the_survivor_list`: named sources 83, supersession only 39, no single committed reason 141.
- Statuses in the three files no longer say DRAFT. `g_gen_record_DRAFT.json` is not in final_v3.
- Section 6.8 mapped cleanly. Notes: the Language understanding row prints "—" beside it; the gate-candidate cells carry "(public)" text, kept as written in `gate_candidates_as_written`.
