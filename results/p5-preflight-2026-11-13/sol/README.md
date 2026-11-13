# Sol implementation handoff — P5 hierarchy ablation

Sol implemented the isolated P5 code and config for
[ADR-0010](../../../docs/decisions/ADR-0010-hierarchical-memory-ablation.md).
This is engineering preflight evidence. No P5 corpus model forwards, training,
scientific evaluations, or registered timing workers ran during these checks.
No P1–P4 numerical source, config, spec, lock, or historical result was changed.
The independent review and source freeze are separate steps owned by the
human-authorized reviewer. Astra review: **NOT_PERFORMED**.

- [Implementation fingerprints](implementation-sha256.txt) identify the P5 source,
  config and Sol tests. They are not an execution freeze.
- [Check commands](run-checks.sh) run the locked whole-repository Ruff, mypy,
  pytest and E0 smoke sequence from the repository root.
- The [initial full check log](full-checks.log) records Ruff passing, mypy checking
  47 source files, and 156 tests passing. The [E0 regression](e0-result.json)
  passed all 11 gates. The warnings were the existing missing NumPy warning
  and PyTorch's duplicate-parameter warning from the intentional optimizer
  corruption fixture.
- The final ACK accounting correction has a preserved
  [failing regression](delayed-invalid-ack-before.log) and
  [passing focused check](delayed-invalid-ack-after.log). An invalid or interrupted
  reporting wait remains charged. The implementation fingerprints above include
  this correction; the reviewer independently checks the final tree.
- [Engineering findings](engineering-findings.md) and the
  [intermediate regression log](regression-attempt-01.log) preserve the
  preflight defects, failed test fixtures and corrections. The
  [implementation checks](implementation-checks.log) and
  [optimizer guard checks](optimizer-guard-checks.log) preserve focused checks.
- The [reviewer's strict restore and frozen data audit](../root-strict-restore/README.md)
  verified all nine actual P4 parents against the upstream P3 tensors with
  no forwards, and matched all 2,560 ranked validation IDs to
  [Luna's independent raw-data and parent reconstruction](../independent-data-parent-audit.md).
  The new panel bytes SHA-256 is
  `d50cbe4c303791148c922bfe9201fe00b192c44deef855077860ffc98cc72b98`;
  the frozen dataset manifest SHA-256 is
  `481dba62b283fc7b732bcf3692f38f37c2891b9d2200f9e1fc304c0f5721e848`.

After separate reviewer execution authorization and freeze, the registered
invocation from the repository root is:

```sh
uv run --locked --extra pilot python -m arborlm.hierarchy_ablation \
  --data-dir data/wikitext2 --output-root experiments --results-root results/p5-2026-11-13
```

It requires the original registered P4 and upstream P3 binary artifacts; a
newly recreated suite is not a replacement. The output directory must not
already exist. Compact evidence excludes weights, optimizer binaries, corpus
bytes and source archives, which are retained locally. A failing worker or
budget breach preserves available evidence and halts subsequent work.

The runner emits `timing_ack_required` after closing the quality stage and
after each timing worker exits and its compact bundle is finalized. No timing
child runs during that wait. After reporting that evidence and pushing its
checkpoint, the operator may publish the ACK with the exact event fields:

```sh
python3 - "$P5_ACK_PATH" "$P5_SUITE_ID" "$P5_WORKER_ID" "$P5_PUSHED_COMMIT" <<'PY'
import json
import os
import sys
import tempfile
from pathlib import Path

destination = Path(sys.argv[1])
payload = {
    "suite_id": sys.argv[2],
    "worker_id": sys.argv[3],
    "commit": sys.argv[4],
    "push_completed": True,
}
if destination.exists():
    raise FileExistsError(destination)
with tempfile.NamedTemporaryFile(
    "w", dir=destination.parent.parent, prefix=".operator-ack-", delete=False
) as stream:
    json.dump(payload, stream)
    stream.write("\n")
os.replace(stream.name, destination)
PY
```

Use the full lowercase 40-character commit. Temporary files must stay outside
the watched `report-acks` directory. The runner rejects early, unexpected,
mismatched and reused ACKs. Only the measured wait for a validated ACK is deducted;
announcements, verification, supervision and packaging count toward the
registered stage deadlines. Keep Git and audit work outside live timing workers.
