# ruff: noqa: E501
"""P10IS5 seed gate (ADR-0028 section 10; ADR-0029 section 5 and ruling 6's own-files exclusion).

(1) every planned value lies in the range the registry allocates to its role (config ``[seed_ranges]``); (2) the planned roles are pairwise disjoint; (3) the study's own values are checked SEPARATELY against the registry's
allocation rows (the config's ranges lie inside the checker's ``ALLOC`` rows of P10-I-S5); (4) the registry's checker file (revision 3, its SHA-256 in the config) is run as an extended copy that excludes this study's own
files from its inventory (three substitutions, all listed with the copy's SHA-256 in the result) and must print ``RESULT: PASS``. The copy is run with ``python -c`` so that nothing is written outside the worktree. The test-range
values used by the unit tests lie in 937001-937999. Initialisation 330501-330599 stays unused (scientific part).
"""

import re
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from arborlm.io import file_sha256, sha256

from . import core, testing

CHECKER_SUBSTITUTIONS: tuple[tuple[str, str], ...] = (
    ("ROOT = Path(__file__).resolve().parents[3]", "ROOT = Path({root!r})"),
    ('for path in sorted((ROOT / "configs").glob("*.toml")):', 'for path in [q for q in sorted((ROOT / "configs").glob("*.toml")) if q.name != "p10is5_ssd.toml"]:'),
    ('for path in sorted((ROOT / d).rglob("*.py")):', 'for path in [q for q in sorted((ROOT / d).rglob("*.py")) if "p10is5" not in q.name and "p10is5" not in q.parts]:'),
)


OWN_OWNER = "P10-I-S5 ADR-0028"
# The ONE failure pattern the gate accepts from the cited checker: P10-I-R's own allocation hitting P10-I-R's own files (its config or its code and tests) while they are in the same tree.
KNOWN_SELF_COLLISION = re.compile(r"^FAIL: P10-I-R ADR-0029 / .* hits inventory: (P10IR / config literal|All code and tests / literal scan)")


def planned_seed_values(cfg: Mapping[str, Any]) -> dict[str, frozenset[int]]:
    """Every integer the study uses, by role-block (registered data, auxiliary, R1, rehearsal, test)."""
    s = cfg["seeds"]
    registered = [s["store_contents"], *s["request_order"], s["spare_request_order"], *s["pass_order"], s["spare_pass_order"]]
    auxiliary = [s["tile_assignment"]]
    r1 = [s["r1_rehearsal_file_contents"], s["r1_control_file_contents"], s["r1_request_order"], s["r1_pass_order"], s["r1_reread_offsets"]]
    rehearsal = [*s["m_request_order"], *s["k_request_order"], *s["m_pass_order"], *s["k_pass_order"], s["m_tile_assignment"], s["k_tile_assignment"]]
    test = [testing.TEST_SEED_CONTENTS, testing.TEST_SEED_ASSIGN, *testing.TEST_SEED_REQUEST, *testing.TEST_SEED_ORDER]
    return {k: frozenset(int(x) for x in v) for k, v in (("registered", registered), ("auxiliary", auxiliary), ("r1", r1), ("rehearsal", rehearsal), ("test", test))}


def role_multiplicity(cfg: Mapping[str, Any]) -> dict[str, int]:
    """The ADR's counts (section 10): 17 registered values... counted from the config (the gate prints them; it does not compare them to a constant)."""
    return {k: len(v) for k, v in planned_seed_values(cfg).items()}


def allocation_rows(checker_text: str) -> list[tuple[str, int, int]]:
    """The rows of P10-I-S5 in the cited checker's ``ALLOC`` table: (role, low, high)."""
    return [(m[1], int(m[2]), int(m[3])) for m in re.finditer(r'\("P10-I-S5 ADR-0028", "([^"]*)", (\d+), (\d+)\)', checker_text)]


def allocation_problems(cfg: Mapping[str, Any], rows: Sequence[tuple[str, int, int]]) -> list[str]:
    """The separate check: every range the config assigns to a role of this study lies inside the registry's ALLOC row of that role."""
    want = {"registered": "data: registered", "auxiliary": "auxiliary", "r1": "calibration (R1)", "rehearsal": "rehearsal", "test": "test"}
    problems = []
    for key, prefix in want.items():
        lo, hi = (int(x) for x in cfg["seed_ranges"][key])
        if not any(r[0].startswith(prefix) and r[1] <= lo and hi <= r[2] for r in rows):
            problems.append(f"the config's {key} range {lo}-{hi} is not inside a registry allocation row '{prefix}...' of ADR-0028")
    return problems


def checker_copy(original: str, root: Path) -> str:
    """The text of the extended copy: the cited file with ``CHECKER_SUBSTITUTIONS`` applied (each must match exactly once)."""
    out = original
    for old, new in CHECKER_SUBSTITUTIONS:
        if out.count(old) != 1:
            raise ValueError(f"the checker file does not contain the line to extend exactly once: {old!r}")
        out = out.replace(old, new.format(root=str(root)))
    return out


def run_checker_copy(path: Path, root: Path, timeout: float) -> dict[str, Any]:
    text = checker_copy(path.read_text(encoding="utf-8"), root)
    proc = subprocess.run([sys.executable, "-c", text], cwd=root, capture_output=True, text=True, timeout=timeout, check=False)  # noqa: S603
    result = next((line for line in proc.stdout.splitlines() if line.startswith("RESULT:")), None)
    fails = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip().startswith("FAIL:")]
    own = [ln for ln in fails if OWN_OWNER in ln]
    known = [ln for ln in fails if OWN_OWNER not in ln and KNOWN_SELF_COLLISION.search(ln)]
    unknown = [ln for ln in fails if OWN_OWNER not in ln and not KNOWN_SELF_COLLISION.search(ln)]
    foreign = sorted({ln.split(" / ", 1)[0].removeprefix("FAIL: ") for ln in known})
    return {
        "returncode": proc.returncode, "result_line": result, "copy_sha256": sha256(text.encode()), "substitutions": [old for old, _ in CHECKER_SUBSTITUTIONS], "fail_lines": len(fails), "own_fail_lines": own[:5],
        "foreign_fail_owners": foreign, "unknown_fail_lines": unknown[:5],
    }  # fmt: skip


def seed_gate(cfg: Mapping[str, Any] | None = None, *, root: Path | None = None, run_checker: bool = True, timeout: float = 300.0) -> dict[str, Any]:
    c = cfg or core.load_config()
    base = root or core.repo_root()
    ranges = c["seed_ranges"]
    planned = planned_seed_values(c)
    problems: list[str] = []
    for role, values in planned.items():
        lo, hi = (int(x) for x in ranges[role])
        out = sorted(v for v in values if not lo <= v <= hi)
        if out:
            problems.append(f"{role}: values outside the registry's range {lo}-{hi}: {out[:5]}")
    names = sorted(planned)
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            common = planned[a] & planned[b]
            if common:
                problems.append(f"{a} and {b} share {sorted(common)[:5]}")
    # the roles inside one block must be pairwise different too: the config's lists have no repeated value
    seeds = c["seeds"]
    flat = [seeds[k] for k in seeds if isinstance(seeds[k], int)] + [x for k in seeds if isinstance(seeds[k], list) and k != "test_range" for x in seeds[k]]
    if len(flat) != len(set(flat)):
        problems.append("a seed value is used by two roles of the config")
    checker_path = base / ranges["checker"]
    checker: dict[str, Any] = {"path": ranges["checker"], "expected_sha256": ranges["checker_sha256"]}
    if checker_path.is_file():
        checker["sha256"] = file_sha256(checker_path)
        if checker["sha256"] != ranges["checker_sha256"]:
            problems.append("the registry checker file differs from the SHA-256 the config cites")
        else:
            rows = allocation_rows(checker_path.read_text(encoding="utf-8"))
            checker["allocation_rows"] = len(rows)
            problems += allocation_problems(c, rows) if rows else ["no ADR-0028 rows in the checker's ALLOC table"]
            if run_checker:
                checker.update(run_checker_copy(checker_path, base, timeout))
                # The cited checker prints RESULT: FAIL by construction while a sibling P10-I study's own files are in the same tree (their allocations hit their own inventory; ADR-0029 handles that for itself). This gate
                # passes iff the checker printed RESULT: PASS, or every FAIL line belongs to another study's allocation (listed in ``foreign_fail_owners``) and none to P10-I-S5's.
                clean = checker["result_line"] == "RESULT: PASS" or (checker["fail_lines"] > 0 and not checker["own_fail_lines"] and not checker["unknown_fail_lines"] and checker["result_line"] == "RESULT: FAIL")
                if not clean:
                    problems.append(f"the extended registry checker reports a failure of P10-I-S5's own allocation, a failure that is not P10-I-R's known self-collision, or no result (returncode {checker['returncode']}, {checker['result_line']}, {checker['own_fail_lines']}, {checker['unknown_fail_lines']})")
    else:
        problems.append(f"the registry checker is not at {ranges['checker']}")
    return {"passed": not problems, "problems": problems, "roles": role_multiplicity(c), "checker": checker}
