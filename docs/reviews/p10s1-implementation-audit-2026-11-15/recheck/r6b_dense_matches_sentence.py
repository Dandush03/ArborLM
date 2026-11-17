"""M5 follow-up: can DENSE MATCHES still be printed, and is its mandated sentence (ADR 8.5 row 3) printed where it is? The predecessor's slow_large scenario with a CPU
table in which D-OQ at 16,384 slots costs 2.5 x F-OQ (so the 16K dense pair is established: madds 2.53 -> grid 3 -> 24,576 <= 32,768); every other figure as in c5.
Run (worktree root): TMPDIR=<scratch> PYTHONPATH=. uv run --locked python docs/reviews/p10s1-implementation-audit-2026-11-15/recheck/r6b_dense_matches_sentence.py
Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval."""
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import c5_synthetic_registry as P  # noqa: E402
import r6_synthetic_registry_updated as U6  # noqa: E402

P.CPU[("D-OQ", 16384)] = 2.5 * P.CPU[("F-OQ", 16384)]
out = []
with tempfile.TemporaryDirectory(prefix="p10s1-recheck-r6b-") as tmp:
    for name, seed, kind in (("slow_large", 921603, "slow_large"), ("capacity", 921600, "capacity")):
        r = U6.compare(P.Scenario(name, seed, kind), Path(tmp))
        text = (Path(tmp) / name / "results" / "RESULTS.md").read_text() if r["report"] == "written" else ""
        lines = [ln for ln in text.splitlines() if "DENSE MATCHES" in ln]
        out.append({k: r[k] for k in ("scenario", "diffs", "capacity", "dense", "arm_classes", "report", "report_has_DENSE_MATCHES_sentence", "analysis_has_DENSE_MATCHES_sentence", "arms_labelled_DENSE_MATCHES")} | {"report_lines_with_DENSE_MATCHES": lines[:6]})
json.dump(out, sys.stdout, indent=1, default=str)
print()
