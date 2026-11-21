# ruff: noqa: E501
"""Runs a module of this repository with ``python -I`` (no user site, no current directory, no PYTHONPATH): the repository root is put on sys.path explicitly. For the stages that read downloaded files (fetch, D0), so that a planted module next to the data cannot be imported."""

import runpy
import sys
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    module = sys.argv[1]
    sys.argv = [module, *sys.argv[2:]]
    runpy.run_module(module, run_name="__main__", alter_sys=True)
