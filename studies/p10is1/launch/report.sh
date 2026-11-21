#!/bin/sh
# Registered stage report (ADR-0024). Refuses unless frozen and decided.. Usage: <script> <run-dir> <freeze-commit>
exec uv run --locked python -m studies.p10is1.stages registered report --run-dir "$1" --freeze-commit "$2"
