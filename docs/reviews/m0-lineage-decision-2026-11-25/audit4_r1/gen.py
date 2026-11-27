# ruff: noqa
"""Shim: audit-3 scripts import `gen`; here it serves the audit-4 set (registered_v3) through gen4."""
from gen4 import lineages, items  # noqa: F401
