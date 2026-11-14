#!/bin/sh
# Follow-up oracle probes, rehearsal draw 0. Run from the repo root.
P="uv run --locked python docs/reviews/p9-calibration-audit-2026-11-14/position_tables_extra.py"
O=docs/reviews/p9-calibration-audit-2026-11-14/outputs
( $P --probe fact_at_prefix --lr 0.003 --sigma > $O/pte_fact_at_prefix_sigma_lr0.003.log 2>&1
  $P --probe fact_at_prefix --lr 0.003 > $O/pte_fact_at_prefix_full_lr0.003.log 2>&1 ) &
( $P --probe fact_at_id5 --lr 0.003 --sigma > $O/pte_fact_at_id5_sigma_lr0.003.log 2>&1
  $P --probe fact_at_id5 --lr 0.001 --sigma > $O/pte_fact_at_id5_sigma_lr0.001.log 2>&1 ) &
wait
