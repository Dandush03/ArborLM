# ruff: noqa
"""Final R1 audit: shim replacing audit 4's gen4.py so that its unchanged heuristics3.py / heuristics4.py run on the fix-4 set.
lineages() = the twelve survivors (registered_v4); items() has audit 4's signature and convention (Random(seed_base + level), Retry skipped)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fgen


def lineages():
    return fgen.lineages()


def excluded():
    return {}


def items(lin, level, n, seed_base=3100, count_retries=False):
    return fgen.items(lin, level, n, seed_base, count_retries)
