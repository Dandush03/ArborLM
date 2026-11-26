# ruff: noqa
"""Shim (as audit 4's gen.py): audit-3 scripts import `gen`; here it serves the fix-4 set through gen4."""
from gen4 import lineages, items  # noqa: F401
