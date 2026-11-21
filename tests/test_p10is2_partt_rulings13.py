# ruff: noqa: E501
"""P10IS2 Part T ruling 45 (docs/decisions/ADR-0025-addendum-part-t-rulings-13.md): seed registry revision 7 (revision 6 plus P10-I-S1 and P10-I-S6 as owners of their own files, nothing else). Self-check only."""

import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from arborlm.io import file_sha256  # noqa: E402
from studies.p10is2.common import core, gates  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "docs/reviews/p10-i-direction-2026-11-17"
OWN = (
    '    "P10-I-S1 ADR-0024": ("configs/p10is1_*", "studies/p10is1/*", "tests/test_p10is1_*"),  # revision 7',
    '    "P10-I-S6 ADR-0031": ("configs/p10i_s6_*", "studies/p10i_s6/*", "tests/test_p10i_s6_*"),  # revision 7',
)


def test_r7_checker_is_r6_plus_two_ownership_lines_and_a_note() -> None:
    r6 = (REG / "seed_registry_check_r6.py").read_text().split("\n")
    r7 = (REG / "seed_registry_check_r7.py").read_text().split("\n")
    assert r7[1].startswith('"""REVISION 7 (2026-11-21)')
    note_end = next(i for i, line in enumerate(r7) if line.startswith("REVISION 6 (2026-11-21)"))
    rebuilt = [r7[0], '"""' + r7[note_end], *r7[note_end + 1 :]]  # drop the revision-7 note, reopen the revision-6 docstring
    for line in OWN:
        assert rebuilt.count(line) == 1
        rebuilt.remove(line)
    rebuilt = [x.replace("seed_registry_check_r7.py [--tables]", "seed_registry_check_r6.py [--tables]") for x in rebuilt]
    assert rebuilt == r6  # nothing else differs: no seed value, block or row


def test_the_config_cites_r7_by_hash_and_r5_and_r6_are_unchanged() -> None:
    s = core.load_config("T")["seeds"]
    assert s["registry_checker"].endswith("seed_registry_check_r7.py") and s["registry_addendum"].endswith("SEED_REGISTRY_R7.md")
    assert file_sha256(ROOT / s["registry_checker"]) == s["registry_checker_sha256"] == "1f3b2de22ef3ff9bd01d81d67d7fcccac27710ed3394b62bec9c0688bc8b8f8f"
    assert file_sha256(ROOT / s["registry_addendum"]) == s["registry_addendum_sha256"]
    assert file_sha256(REG / "seed_registry_check_r6.py") == "eb757082dac6e0e34a28c4d2ac87e0b96cd0e1f6af68505dc434792f475280a4"  # revision 6 is never edited
    assert file_sha256(REG / "SEED_REGISTRY_R6.md") == "4f2afd94928c70229db5956a5781e53d8f25265a64318c9f56f608d5188a0efb"
    assert file_sha256(REG / "seed_registry_check_r5.py") == "8ce47ab52abbe25b4b308ca2a1e7587f5461b13340f1faa2a0c0cff6804f4611"


def test_g9_passes_on_this_tree_with_r7() -> None:
    res = gates.seed_gate("T", core.load_config("T"), root=ROOT)
    assert res["passed"], res["problems"]
    assert res["checker"]["result_line"] == "RESULT: PASS" and res["checker"]["unedited"] is True


def run_checker(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-I", str(REG / "seed_registry_check_r7.py"), "--root", str(root)], cwd=ROOT, capture_output=True, text=True, timeout=900, check=False)  # noqa: S603


def test_r7_still_fails_on_each_kind_of_planted_fault(tmp_path: Path) -> None:
    for name in ("configs", "studies", "src", "tests"):
        shutil.copytree(ROOT / name, tmp_path / name, ignore=shutil.ignore_patterns("__pycache__", ".venv", "experiments"))
    p = tmp_path / "configs/p10is1_capacity.toml"
    foreign, owned = 260000 + 131, 240000 + 1  # built, not written as literals: this very file is scanned by the checker as P10-I-S2's own file
    p.write_text(p.read_text() + f"\nplanted_seed = {foreign}\n")  # (a) a foreign value (P10-I-S3's joint seed) in an owned file
    (tmp_path / "src/arborlm/planted_b.py").write_text(f"import random\n\nrandom.Random({owned})\n")  # (b) an owned value (P10-I-S1's registered draw) in a file no study owns
    q = tmp_path / "configs/p10is2_partt.toml"
    text = q.read_text()
    assert text.count("init_test = [330281, 330289]") == 1
    q.write_text(text.replace("init_test = [330281, 330289]", "init_test = [900001, 330289]"))  # (c) a Part T value outside its rows
    proc = run_checker(tmp_path)
    fails = [x.strip() for x in proc.stdout.splitlines() if x.strip().startswith("FAIL:")]
    assert proc.returncode == 1 and "RESULT: FAIL" in proc.stdout
    assert any("hits inventory: P10IS1 / config literal" in x and "[entry owned by P10-I-S1 ADR-0024]" in x and x.startswith("FAIL: P10-I-S3") for x in fails)  # a
    assert any(x.startswith("FAIL: P10-I-S1 ADR-0024") and "literal scan" in x for x in fails)  # b
    assert any("initialisation values outside P10-I-S2's sub-row" in x for x in fails)  # c
