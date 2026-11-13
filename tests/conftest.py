import pytest

from arborlm.engine import configure_cpu


@pytest.fixture(scope="session", autouse=True)
def deterministic_cpu() -> None:
    configure_cpu()
