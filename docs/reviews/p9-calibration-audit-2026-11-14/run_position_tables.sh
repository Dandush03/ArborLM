#!/bin/sh
# Auditor's frozen-upper-block probes, rehearsal draw 0. Run from the repo root.
P="uv run --locked python docs/reviews/p9-calibration-audit-2026-11-14/position_tables.py"
O=docs/reviews/p9-calibration-audit-2026-11-14/outputs
( $P --probe unigram --facts 2048 --updates 8192 > $O/pt_unigram_full.log 2>&1
  $P --probe unigram --facts 2048 --updates 8192 --sigma > $O/pt_unigram_sigma.log 2>&1
  $P --probe bigram --facts 2048 --updates 8192 > $O/pt_bigram_full.log 2>&1
  $P --probe bigram --facts 2048 --updates 8192 --sigma > $O/pt_bigram_sigma.log 2>&1 ) &
( $P --probe fact_at_id5 --facts 2048 --updates 8192 > $O/pt_fact_at_id5_full.log 2>&1
  $P --probe fact_at_id5 --facts 2048 --updates 8192 --sigma > $O/pt_fact_at_id5_sigma.log 2>&1
  $P --probe fact_at_site --facts 2048 --updates 8192 > $O/pt_fact_at_site_full.log 2>&1
  $P --probe trigram --facts 2048 --updates 8192 --sigma > $O/pt_trigram_sigma.log 2>&1 ) &
wait
