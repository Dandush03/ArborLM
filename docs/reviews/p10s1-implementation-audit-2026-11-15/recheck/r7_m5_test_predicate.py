"""m5 / item 4: what the rewritten 'no existing file is edited' test (tests/test_p10s1_core.py, test_no_existing_file_is_edited_and_p9_modules_are_imported_not_patched) lets
through. Its two predicates are copied verbatim below and applied to synthetic `git status --porcelain` lines (no git call, no file touched), next to the old predicate.
Run: python3 docs/reviews/p10s1-implementation-audit-2026-11-15/recheck/r7_m5_test_predicate.py
Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval."""
import json

protected = ("src/", "uv.lock", "pyproject.toml", "studies/p9", "supplements/", "docs/decisions/", "experiments/")  # copied from the test at 82e58dd
own = ("studies/p10s1/", "configs/p10s1_capacity.toml", "tests/test_p10s1_", "docs/decisions/ADR-0021")  # copied
old_allowed = ("?? studies/p10s1/", "?? configs/p10s1_capacity.toml", "?? tests/test_p10s1_")  # the test at 8747af2


def new_fails(line):
    touched = line[3:].startswith(protected) and not line[3:].startswith(own)
    other_configs = line[3:].startswith("configs/") and not line[3:].startswith(own)
    return touched or other_configs


lines = [
    "?? docs/reviews/p10s1-implementation-audit-2026-11-15/recheck/", " M docs/decisions/ADR-0021-p10-s1-useful-capacity-scaling.md", " M docs/decisions/ADR-0020-p10-s0.md",
    " M results/p5-something/OUTCOME.md", " D results/p9i-run-attempt2-2026-11-15/OUTCOME.md", " M tests/test_p9i_core.py", " M tests/test_p5_gates.py", " M AGENTS.md", " M CLAUDE.md",
    " M docs/reviews/p9i-results-2026-11-15/REVIEW.md", " M docs/RESEARCH_LOG.md", " M studies/p10s0/core.py", " M studies/p9/core.py", " M src/arborlm/p7a_core.py", " M configs/p9i.toml",
    '?? "studies/p9/\\303\\251.py"', "R  studies/p9/a.py -> studies/p10s1/a.py",
]
out = {ln: {"old_test_fails": not ln.startswith(old_allowed), "new_test_fails": new_fails(ln)} for ln in lines}
json.dump(out, __import__("sys").stdout, indent=1)
print()
