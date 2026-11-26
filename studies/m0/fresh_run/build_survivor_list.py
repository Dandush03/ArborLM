"""Build the survivor list of record (ADR-0033 addendum 1, section 4A, stage 0).

Two inputs and no other: the four fix-4 survivor manifests and the drops file.
Standard library only. Writes studies/m0/manifests/survivor_list_of_record.json
with deterministic bytes. Stops, writing nothing, on any mismatch.
"""

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MANIFESTS = "studies/m0/manifests"
DROPS = (
    "docs/reviews/m0-lineage-decision-2026-11-25/cross_evaluation_map/"
    "drops_after_final_checks.txt"
)
OUTPUT = f"{MANIFESTS}/survivor_list_of_record.json"
EVALUATIONS = ("R1", "R2", "M1", "C1")
EXPECTED_COUNTS = {"R1": 10, "R2": 17, "M1": 29, "C1": 26}
EXPECTED_PREFIX = {
    "R1": "e1a7a092",
    "R2": "2456dac6",
    "M1": "153e6837",
    "C1": "eaedec75",
}
EXPECTED_SUFFIX = {
    "R1": "749b",
    "R2": "a102",
    "M1": "1986",
    "C1": "3603",
}
DROPS_PREFIX = "b714f102"
DROPS_SUFFIX = "0bd5"


class Stop(Exception):
    pass


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest_path(ev: str) -> str:
    return f"{MANIFESTS}/{ev.lower()}_fix4_survivors.json"


def require(cond: bool, message: str) -> None:
    if not cond:
        raise Stop(message)


def load(ev: str) -> dict:
    data = json.loads((ROOT / manifest_path(ev)).read_text())
    require(isinstance(data, dict), f"{ev}: top level is not an object")
    return data


def read_r1(data: dict) -> list[str]:
    ok = "shapes" in data and isinstance(data["shapes"], list)
    require(ok, "R1: field shapes absent or not a list")
    out = []
    for entry in data["shapes"]:
        require("status" in entry and "name" in entry, "R1: shapes entry lacks status or name")
        if entry["status"] == "SURVIVES":
            out.append(entry["name"])
    return out


def read_r2(data: dict) -> list[str]:
    ok = "lineages" in data and isinstance(data["lineages"], dict)
    require(ok, "R2: field lineages absent or not an object")
    out = []
    for key in sorted(data["lineages"]):
        entry = data["lineages"][key]
        ok = "status_before_capacity" in entry and "id" in entry
        require(ok, "R2: lineages entry lacks status_before_capacity or id")
        if entry["status_before_capacity"] == "SURVIVES":
            out.append(entry["id"])
    return out


def read_m1(data: dict) -> list[str]:
    ok = "survivors" in data and isinstance(data["survivors"], list)
    require(ok, "M1: field survivors absent or not a list")
    return list(data["survivors"])


def read_c1(data: dict) -> list[str]:
    ok = "lineages" in data and isinstance(data["lineages"], list)
    require(ok, "C1: field lineages absent or not a list")
    out = []
    for entry in data["lineages"]:
        require("status" in entry and "name" in entry, "C1: lineages entry lacks status or name")
        if entry["status"] == "SURVIVES":
            out.append(entry["name"])
    return out


READERS = {"R1": read_r1, "R2": read_r2, "M1": read_m1, "C1": read_c1}


def read_drops(path: Path) -> list[str]:
    out = []
    for line in path.read_text().splitlines():
        text = line.strip()
        if text and not text.startswith("#"):
            out.append(text)
    return out


def build() -> bytes:
    hashes = {}
    for ev in EVALUATIONS:
        digest = sha256_of(ROOT / manifest_path(ev))
        require(
            digest.startswith(EXPECTED_PREFIX[ev]) and digest.endswith(EXPECTED_SUFFIX[ev]),
            f"{ev}: manifest SHA-256 does not match the text",
        )
        hashes[manifest_path(ev)] = digest
    drops_digest = sha256_of(ROOT / DROPS)
    require(
        drops_digest.startswith(DROPS_PREFIX) and drops_digest.endswith(DROPS_SUFFIX),
        "drops file SHA-256 does not match the text",
    )
    hashes[DROPS] = drops_digest

    lists = {}
    for ev in EVALUATIONS:
        ids = READERS[ev](load(ev))
        require(all(isinstance(i, str) for i in ids), f"{ev}: ids not all strings")
        lists[ev] = ids

    for drop in read_drops(ROOT / DROPS):
        ev = drop.split(".")[0]
        require(ev in lists, f"drop {drop}: unknown evaluation prefix")
        require(drop in lists[ev], f"drop {drop}: not in the list read for {ev}")
        lists[ev] = [i for i in lists[ev] if i != drop]

    result = {}
    for ev in EVALUATIONS:
        ids = sorted(lists[ev])
        require(len(ids) == len(sorted(set(ids))), f"{ev}: duplicate ids")
        want = EXPECTED_COUNTS[ev]
        require(len(ids) == want, f"{ev}: count {len(ids)} differs from {want}")
        result[ev] = ids

    out = {
        "evaluations": result,
        "input_sha256": hashes,
        "script_sha256": sha256_of(Path(__file__).resolve()),
    }
    text = json.dumps(out, sort_keys=True, indent=2, separators=(",", ": "), ensure_ascii=True)
    return (text + "\n").encode()


def main() -> int:
    try:
        payload = build()
    except Stop as exc:
        sys.stderr.write(f"STOP: {exc}\n")
        return 1
    (ROOT / OUTPUT).write_bytes(payload)
    counts = json.loads(payload)["evaluations"]
    sys.stdout.write(" ".join(f"{ev}={len(counts[ev])}" for ev in EVALUATIONS) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
