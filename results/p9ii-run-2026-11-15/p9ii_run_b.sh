#!/bin/bash
R=/Users/daniellaloush/dandush03/ArborLM/experiments/P9IIP-registered-20261115b
F=d2746d3ba57b9666a6100bda8b5d0e7414883e3a
L="$TMPDIR/p9ii_run.log"
for st in stage2 stage3_gate stage3 analysis report; do
  echo "=== $st $(date -u +%H:%M:%S)" >> "$L"
  sh studies/p9ii/launch/$st.sh "$R" "$F" >> "$L" 2>&1
  code=$?
  echo "$st exit $code"
  grep -v "UserWarning\|cpu = _conv" "$L" | tail -1 | cut -c1-400
  if [ $code -ne 0 ]; then exit $code; fi
done
