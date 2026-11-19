# ruff: noqa: E501
"""Exceptions shared by the stage modules."""

from .core import Paused


class ColdFinal(Paused):
    """After the one recovery rebuild the store is still not cold: ENGINEERING NOT EVALUABLE — STORE CANNOT BE HELD COLD (a final status), not a pause."""

    def __init__(self, detail: str = "") -> None:
        super().__init__("ENGINEERING NOT EVALUABLE — STORE CANNOT BE HELD COLD", detail)
