"""Auditor probe: does the documented datagen.sh sequence (install_datagen, then datagen with a clean-HEAD check) work in one invocation, and on a re-run?
Runs in a throwaway shallow clone with a FAKE installer (no network). Usage (cwd = the clone): <python> <this> <clone> <tmp>"""

import subprocess
import sys
from pathlib import Path

clone, tmp = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
sys.path.insert(0, str(clone))
from studies.p10s2 import fetch_guard, freeze  # noqa: E402
from studies.p10s2 import install_datagen as ins  # noqa: E402
from studies.p10s2.ledger import Ledger  # noqa: E402

assert Path(ins.__file__).resolve().is_relative_to(clone), ins.__file__
tmp.mkdir(parents=True, exist_ok=True)
h = " \\\n    --hash=sha256:" + "0" * 64
req = tmp / "req.txt"
req.write_text("".join(f"{n}=={v}{h}\n" for n, v in ins.EXPECTED_PINS.items()))


def fake_installer(requirements: Path, target: Path) -> None:
    for n, v in ins.EXPECTED_PINS.items():
        d = target / f"{n.replace('-', '_')}-{v}.dist-info"
        d.mkdir(parents=True)
        (d / "METADATA").write_text(f"Metadata-Version: 2.1\nName: {n}\nVersion: {v}\n")


head = subprocess.run(["git", "-C", str(clone), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
print("clean before install:", freeze.check_code_commit(clone, head) == head)
ins.run(req, clone / ins.INSTALL_DIR, led=Ledger(tmp / "ledger.jsonl"), download_ledger=clone / fetch_guard.DOWNLOAD_LEDGER, installer=fake_installer)
print("git status after install_datagen.run:", subprocess.run(["git", "-C", str(clone), "status", "--porcelain"], capture_output=True, text=True).stdout.strip())
try:
    freeze.check_code_commit(clone, head)
    print("datagen's clean-HEAD check after the install: ACCEPTED")
except freeze.FreezeRefused as e:
    print("datagen's clean-HEAD check after the install: REFUSED ->", str(e).splitlines()[0])
try:
    ins.run(req, clone / ins.INSTALL_DIR, led=Ledger(tmp / "ledger.jsonl"), download_ledger=clone / fetch_guard.DOWNLOAD_LEDGER, installer=fake_installer)
    print("second install (datagen.sh re-run): accepted")
except ins.InstallRefused as e:
    print("second install (datagen.sh re-run): InstallRefused ->", e, "(main returns 2; datagen.sh has set -eu, so the datagen line is never reached)")
