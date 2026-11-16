# ruff: noqa: E501
"""Install the data-generation packages with hashes required (ADR-0022 section 14.2; the lead's ruling R2 of 2026-11-15, re-check A).

The requirements file is checked FROM THE LOCKED ENVIRONMENT, before anything is installed: every pin carries ``--hash=sha256:`` and no option line other than ``--hash`` is accepted (``-e``, ``-r``,
``--index-url``, ``--extra-index-url`` ... are refused). Then the packages are installed with ``uv pip install --require-hashes --target <dir> -r <file>`` into ONE dedicated git-ignored directory
(``data/datagen-packages``), which ``launch/datagen.sh`` puts on the path of the data-generation process only (the locked environment, ``uv.lock`` and ``pyproject.toml`` are untouched, and no second
virtual environment exists). A download-ledger row is written before the install and completed after it (the installed bytes), and the install is charged on the study ledger. It is its own launch step (``launch/install_datagen.sh``, run by the lead; the ledger change is then committed by the lead); ``launch/datagen.sh`` only runs ``--verify``. Afterwards the installed
versions must equal the eight pins of the ADR, and the directory must not shadow the locked ``torch``. Nothing here runs in the tests except on fakes: the installer is injected.
"""

import argparse
import importlib.metadata as metadata
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from . import core, datagen, fetch_guard
from .ledger import Ledger

INSTALL_DIR = Path("data/datagen-packages")  # under the git-ignored data/
EXPECTED_PINS = {"transformers": "4.57.1", "tokenizers": "0.22.1", "safetensors": "0.6.2", "huggingface-hub": "0.35.3", "sentencepiece": "0.2.1", "numpy": "2.3.3", "sacremoses": "0.1.1", "sacrebleu": "2.5.1"}
SHADOWING = ("torch", "pyarrow")  # packages of the lock that the data-generation directory must never replace


class InstallRefused(RuntimeError):
    """The requirements file or the installed set does not satisfy the ruling: nothing is (or stays) installed."""


def logical_lines(text: str) -> list[str]:
    out: list[str] = []
    cur = ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        cur += " " + line.rstrip("\\").strip()
        if not line.endswith("\\"):
            out.append(cur.strip())
            cur = ""
    if cur.strip():
        out.append(cur.strip())
    return out


def refused_option_lines(text: str) -> list[str]:
    """Every logical line that is an option (starts with ``-``): ``--hash`` continuations are part of their pin's line, so any standalone option line (``-e``, ``-r``, an index URL ...) is refused."""
    return [ln for ln in logical_lines(text) if ln.startswith("-")]


def pins_of(text: str) -> dict[str, str]:
    pins: dict[str, str] = {}
    for ln in logical_lines(text):
        if ln.startswith("-"):
            continue
        head = ln.split()[0]
        if "==" in head:
            name, version = head.split("==", 1)
            pins[name.lower().replace("_", "-")] = version
    return pins


def check_requirements(path: Path) -> dict[str, str]:
    """The pre-flight, run in the locked environment before any install: hashes on every pin, no option line but ``--hash``, and all eight pins present at their ADR versions."""
    text = path.read_text()
    options = refused_option_lines(text)
    if options:
        raise InstallRefused(f"refused: {path} has option lines other than --hash: {options[:3]}")
    datagen.check_requirements_hashed(path)  # raises DatagenStop for a pin without a hash
    pins = pins_of(text)
    for name, version in EXPECTED_PINS.items():
        if pins.get(name) != version:
            raise InstallRefused(f"refused: {path} does not pin {name}=={version} (found {pins.get(name)!r})")
    return pins


def installed_versions(directory: Path) -> dict[str, str]:
    return {d.metadata["Name"].lower().replace("_", "-"): d.version for d in metadata.distributions(path=[str(directory)])}


def lock_versions(lock: Path | None = None) -> dict[str, str]:
    """name -> version of every package of ``uv.lock`` (the locked environment the data-generation process runs on)."""
    import tomllib

    data = tomllib.loads((lock or core.ROOT / "uv.lock").read_text())
    return {p["name"].lower().replace("_", "-"): p["version"] for p in data.get("package", []) if "version" in p}


def check_installed(directory: Path, lock: dict[str, str] | None = None) -> dict[str, str]:
    """The installed versions must equal the eight pins, the directory must not shadow ``torch`` or ``pyarrow``, and no distribution in it may be one of the lock's packages at another version (re-check
    confirmation F7: filelock, typing-extensions, fsspec ... would shadow the locked copy that torch imports)."""
    got = installed_versions(directory)
    for name, version in EXPECTED_PINS.items():
        if got.get(name) != version:
            raise InstallRefused(f"the installed {name} is {got.get(name)!r}, the pin is {version}")
    shadow = [n for n in SHADOWING if (directory / n).exists()]
    if shadow:
        raise InstallRefused(f"the install directory would shadow the locked {shadow}: refused")
    locked = lock_versions() if lock is None else lock
    clash = sorted(f"{n} {v} (locked {locked[n]})" for n, v in got.items() if n in locked and locked[n] != v)
    if clash:
        raise InstallRefused(f"the install directory holds packages of the lock at another version: {clash[:6]}")
    return got


def directory_bytes(directory: Path) -> int:
    return sum(p.stat().st_size for p in directory.rglob("*") if p.is_file())


def pip_install(requirements: Path, target: Path) -> None:  # pragma: no cover - the one call that reaches the network
    uv = shutil.which("uv")
    if uv is None:
        raise InstallRefused("uv is not on the path")
    subprocess.run([uv, "pip", "install", "--require-hashes", "--target", str(target), "--python", sys.executable, "-r", str(requirements)], check=True)  # noqa: S603


INSTALL_CAP_SECONDS = 1800.0  # the install's stage cap (a killed install is charged at most this: F4)
ROW_WHAT = "data-generation packages (hash-pinned wheels, uv pip install --require-hashes)"


def requirements_revision(requirements: Path) -> str:
    return fetch_guard.sha256_file(requirements)[:12]


def verify(requirements: Path, target: Path, download_ledger: Path, lock: dict[str, str] | None = None) -> dict[str, str]:
    """What ``datagen.sh`` runs before the step (F1): the install is complete and is the one this requirements file asked for. The requirements file passes the pre-flight, the directory exists, the installed
    versions equal the pins without shadowing, and the (committed) download ledger holds a ``completed`` row of the data-generation packages whose revision is this file's SHA-256 (first 12 hex digits). Nothing
    is installed or written here, so the launcher can be re-run after an engineering stop."""
    check_requirements(requirements)
    if not target.is_dir():
        raise InstallRefused(f"refused: {target} does not exist: run launch/install_datagen.sh first")
    got = check_installed(target, lock)
    _head, rows, _tail = fetch_guard._read_ledger(download_ledger)
    rev = requirements_revision(requirements)
    if not any(r[2] == ROW_WHAT and r[4] == rev and r[8].strip().startswith("completed") for r in rows):
        raise InstallRefused(f"refused: the download ledger {download_ledger} has no completed row of the data-generation packages for requirements revision {rev}: commit the ledger after the install")
    return got


def run(requirements: Path, target: Path, *, led: Ledger, download_ledger: Path, installer: Callable[[Path, Path], None] = pip_install) -> dict[str, str]:
    """Check, charge, ledger-row before, install, verify, ledger-row after. A directory that already exists is refused (one install; delete it deliberately to redo)."""
    pins = check_requirements(requirements)
    if target.exists():
        raise InstallRefused(f"refused: {target} exists: the packages are installed once")
    index = fetch_guard.ledger_begin(download_ledger, what=ROW_WHAT, source="PyPI, hashes from " + str(requirements.name), revision=requirements_revision(requirements), licence="various", declared_bytes=0)
    status = "failed"
    nbytes = 0
    try:
        led.refuse_if_over(INSTALL_CAP_SECONDS / 3600.0, None, "the install of the data-generation packages")
        with led.measure("install", process="data-generation packages", cap_seconds=INSTALL_CAP_SECONDS):
            installer(requirements, target)
            nbytes = directory_bytes(target) if target.exists() else 0
            got = check_installed(target)
        status = "completed"
    except BaseException:
        shutil.rmtree(target, ignore_errors=True)  # a failed or refused install leaves nothing on the path
        raise
    finally:
        fetch_guard.ledger_complete(download_ledger, index, actual_bytes=nbytes, status=status)
    return {n: got[n] for n in pins if n in got}


def main(argv: Sequence[str] | None = None) -> int:  # pragma: no cover
    p = argparse.ArgumentParser(prog="python -m studies.p10s2.install_datagen")
    p.add_argument("--code-commit", required=True, help="must equal a clean HEAD")
    p.add_argument("--verify", action="store_true", help="only check that the completed install is the one this requirements file asked for (launch/datagen.sh runs this); installs and writes nothing")
    a = p.parse_args(argv)
    from . import freeze

    freeze.check_code_commit(core.ROOT, a.code_commit)
    try:
        if a.verify:
            verify(core.ROOT / datagen.REQUIREMENTS, core.ROOT / INSTALL_DIR, core.ROOT / fetch_guard.DOWNLOAD_LEDGER)
            return 0
        run(core.ROOT / datagen.REQUIREMENTS, core.ROOT / INSTALL_DIR, led=Ledger(), download_ledger=core.ROOT / fetch_guard.DOWNLOAD_LEDGER)
    except (InstallRefused, datagen.DatagenStop) as e:
        sys.stderr.write(f"{e}\n")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
