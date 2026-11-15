"""ADR-0016 spec review: can the frozen P8 identity checks pass for a supplementary run?

Read-only on the repository. (1) Calls the frozen ``p8_train.verify_freeze`` against the pushed
freeze commit 378aeac (same tree as 80f46ae) and against 80f46ae, at the current HEAD.
(2) Computes the frozen ``p8_core.source_digest`` recipe over a scratch COPY of src/arborlm with
one extra empty module ``p8s_placeholder.py`` added, to show that any new file under src/arborlm
changes the digest that every frozen stage compares with eval/sim records.
(3) Reports the current ``spec_sha256`` against the value recorded in all P8 records.

Imports no analysis module. Not Astra validation.

Run: uv run --locked python -I docs/reviews/p8-supplement-spec-review-2026-11-14/freeze_feasibility.py SCRATCH_DIR
"""

import json
import shutil
import sys
from pathlib import Path

from arborlm import p8_core as core
from arborlm import p8_train

FROZEN_SOURCE = "8b5a03a08fc10a4ac29bdf9c6dd2d21945b9bb3aff459766b58304545d570507"
FROZEN_SPEC = "979274e915341327bcb10cebf69a218b3ad7447116f4a53ae82340e093fa40ba"


def main() -> int:
    scratch = Path(sys.argv[1])
    out: dict[str, object] = {"label": "read-only feasibility check; not Astra validation"}
    for commit in ("378aeac", "80f46ae"):
        try:
            p8_train.verify_freeze(commit)
            out[f"verify_freeze_{commit}"] = "PASSED"
        except p8_train.FreezeError as exc:
            out[f"verify_freeze_{commit}"] = f"REFUSED: {exc}"
    current = core.source_digest()
    out["source_digest_now"] = current
    out["source_digest_now_equals_frozen"] = current == FROZEN_SOURCE
    out["spec_sha256_now"] = core.spec_sha256()
    out["spec_sha256_now_equals_frozen"] = core.spec_sha256() == FROZEN_SPEC
    copy = scratch / "arborlm_copy"
    if copy.exists():
        shutil.rmtree(copy)
    shutil.copytree(Path(core.__file__).resolve().parent, copy,
                    ignore=shutil.ignore_patterns("__pycache__"))
    out["copy_digest_unchanged"] = core.source_digest(copy) == FROZEN_SOURCE
    (copy / "p8s_placeholder.py").write_text("")
    with_new = core.source_digest(copy)
    out["copy_digest_with_one_new_p8s_file"] = with_new
    out["copy_digest_with_new_file_equals_frozen"] = with_new == FROZEN_SOURCE
    json.dump(out, sys.stdout, indent=1, sort_keys=True)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
