#!/bin/sh
# Re-check of ADR-0016 revision 2 (auditor, 2026-11-14): can tests/test_p8s_*.py import a
# top-level supplements/p8s package under the repository's unchanged pytest/mypy/ruff config?
# Usage: sh recheck_import_probe.sh <worktree root> <empty scratch dir>
# Builds a throwaway mini-repo in the scratch dir (copy of pyproject.toml, tests/conftest.py,
# src/) and runs the worktree's locked tools against it. Writes nothing in the worktree.
set -u
W="$1"
S="$2"
mkdir -p "$S/tests" "$S/supplements/p8s"
cp "$W/pyproject.toml" "$S/"
cp "$W/tests/conftest.py" "$S/tests/"
touch "$S/supplements/__init__.py"
echo 'X = 1' > "$S/supplements/p8s/__init__.py"
printf 'from arborlm import p8_sim\n\n\ndef f() -> int:\n    return int(p8_sim.counted_queries(4))\n' \
  > "$S/supplements/p8s/mod.py"
printf 'from supplements.p8s import X\n\n\ndef test_x() -> None:\n    assert X == 1\n' \
  > "$S/tests/test_p8s_plain.py"
cat > "$S/tests/test_p8s_syspath.py" <<'EOF'
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from supplements.p8s import X


def test_x() -> None:
    assert X == 1
EOF
cd "$S" || exit 1
echo "== 1. uv run --locked pytest, plain import (expected: ModuleNotFoundError)"
uv run --locked --project "$W" pytest -q -p no:cacheprovider tests/test_p8s_plain.py 2>&1 \
  | grep -E "ModuleNotFoundError|passed|error" | head -3
echo "== 2. uv run --locked pytest, sys.path insertion (expected: pass)"
uv run --locked --project "$W" pytest -q -p no:cacheprovider tests/test_p8s_syspath.py 2>&1 | tail -1
echo "== 3. ruff E402 on the sys.path test file (expected: no E402)"
"$W/.venv/bin/ruff" check --config "$W/pyproject.toml" --select E402 tests/test_p8s_syspath.py 2>&1 | tail -1
echo "== 4. mypy supplements/p8s alone (expected: import-untyped, arborlm has no py.typed)"
"$W/.venv/bin/mypy" --config-file "$W/pyproject.toml" supplements/p8s 2>&1 | head -1
echo "== 5. mypy src/arborlm supplements/p8s (expected: success)"
cp -R "$W/src" "$S/src"
find "$S/src" -name __pycache__ -prune -exec rm -rf {} +
"$W/.venv/bin/mypy" --config-file "$W/pyproject.toml" src/arborlm supplements/p8s 2>&1 | tail -1
