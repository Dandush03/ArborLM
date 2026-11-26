#!/bin/bash
# usage: run_pool.sh FIXTURE_DIR RUN_NAME [PLAN_SHA FIELD_SHA AMEND_SHA]  (defaults: the actual hashes of the files given)
IW=/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f
CT=/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/arborlm-consolidation-experiment-2b31c1/docs/reviews/adr-0033-m0-2026-11-20/addendum1_scripts/addendum1_rev7_uncounted_rules.json
R=/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_fr_pool_audit_20261126/deliver_recheck/runs
F=$1; N=$2
FT=$IW/studies/m0/fresh_run/field_table.json
PS=${3:-$(shasum -a 256 $F/plan.json | cut -c1-64)}; FS=${4:-$(shasum -a 256 $FT | cut -c1-64)}; AS=${5:-$(shasum -a 256 $F/amend.json | cut -c1-64)}
cd $IW && PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 timeout 300 uv run --locked python -I studies/m0/fresh_run/pool_fresh.py --plan $F/plan.json --survivors $F/survivors.json \
  --class-table $CT --amendments $F/amend.json --field-table $FT --out $R/$N --expect-plan-sha256 $PS --expect-field-table-sha256 $FS --expect-amendment-sha256 $AS \
  > $R/$N.stdout.txt 2> $R/$N.stderr.txt
echo "$N exit=$? stderr=[$(cat $R/$N.stderr.txt)] outdir=$(test -e $R/$N && echo yes || echo no)"
