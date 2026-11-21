"""The README's progress scorecard is generated from its data file and stays in step with it."""

from __future__ import annotations

import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "docs" / "scorecard" / "render_scorecard.py"
DATA = ROOT / "docs" / "scorecard" / "scorecard.toml"


def test_readme_and_image_are_in_step_with_the_data_file() -> None:
    done = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert done.returncode == 0, done.stdout + done.stderr


def test_every_row_has_a_score_evidence_and_links_that_exist() -> None:
    data = tomllib.loads(DATA.read_text(encoding="utf-8"))
    assert data["row"]
    for row in data["row"]:
        assert isinstance(row["score"], int) and 0 <= row["score"] <= 10
        assert row["evidence"] and row["next"].strip() and row["note"].strip()
        for line in row["evidence"]:
            targets = re.findall(r"\]\(([^)]+)\)", line)
            assert targets, f"evidence without a link: {line}"
            for target in targets:
                assert (ROOT / target).exists(), f"missing link target: {target}"


def test_the_section_says_the_scores_are_not_registered_results() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "not registered results and not success claims" in readme
