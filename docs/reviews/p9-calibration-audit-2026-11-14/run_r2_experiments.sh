#!/bin/sh
# Auditor's R2 experiments, rehearsal draw 0 only (init seeds 179001/179002). Run from the repo root.
set -e
P="uv run --locked python docs/reviews/p9-calibration-audit-2026-11-14/r2_train.py"
( $P --slots 4096 --parent b101 --init 179001 --updates 16384 --every 512 --tag base4096_b101_i179001 > docs/reviews/p9-calibration-audit-2026-11-14/outputs/r2_train_base4096_b101_i179001.log 2>&1
  $P --slots 4096 --parent b101 --init 179002 --updates 8192 --every 512 --tag base4096_b101_i179002 > docs/reviews/p9-calibration-audit-2026-11-14/outputs/r2_train_base4096_b101_i179002.log 2>&1
  $P --slots 4096 --parent b102 --init 179001 --updates 16384 --every 512 --tag base4096_b102_i179001 > docs/reviews/p9-calibration-audit-2026-11-14/outputs/r2_train_base4096_b102_i179001.log 2>&1 ) &
( $P --slots 4096 --parent b101 --init 179001 --updates 2048 --every 256 --variant warm --warm /Users/daniellaloush/dandush03/ArborLM/experiments/P9C-20261114T182513034263Z-a529fd1946ff4e52b19980bd6d3b6fcd/cells/CAL-A5-flat-R2-n16384-b101-o301-s1701/snapshots/u0008192 --tag warm4096_b101_i179001 > docs/reviews/p9-calibration-audit-2026-11-14/outputs/r2_train_warm4096_b101_i179001.log 2>&1
  $P --slots 4096 --parent b102 --init 179001 --updates 2048 --every 256 --variant warm --warm /Users/daniellaloush/dandush03/ArborLM/experiments/P9C-20261114T182513034263Z-a529fd1946ff4e52b19980bd6d3b6fcd/cells/CAL-A5-flat-R2-n16384-b102-o302-s1701/snapshots/u0008192 --tag warm4096_b102_i179001 > docs/reviews/p9-calibration-audit-2026-11-14/outputs/r2_train_warm4096_b102_i179001.log 2>&1
  $P --slots 4096 --parent b101 --init 179001 --updates 2048 --every 256 --variant lr --lr 0.01 --tag lr001_4096_b101_i179001 > docs/reviews/p9-calibration-audit-2026-11-14/outputs/r2_train_lr001_4096_b101_i179001.log 2>&1
  $P --slots 4096 --parent b101 --init 179001 --updates 8192 --every 512 --variant sigma_loss --tag sigma4096_b101_i179001 > docs/reviews/p9-calibration-audit-2026-11-14/outputs/r2_train_sigma4096_b101_i179001.log 2>&1
  $P --slots 16384 --parent b101 --init 179001 --updates 8192 --every 1024 --variant sigma_loss --tag sigma16384_b101_i179001 > docs/reviews/p9-calibration-audit-2026-11-14/outputs/r2_train_sigma16384_b101_i179001.log 2>&1 ) &
wait
