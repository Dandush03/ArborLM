"""Fixed strings of ADR-0020 3.4 against every place the report prints them. Usage: python3 -I strings.py <ADR> <run record dir>"""
import json, re, sys
from pathlib import Path
adr = Path(sys.argv[1]).read_text().splitlines()
rec = Path(sys.argv[2])
fourth = adr[129].strip().strip("*")
f1 = re.search(r"OUTCOME.md`: \*(.+)\*$", adr[131]).group(1)
fixed = re.search(r'\*\*"(.+)"\*\*$', adr[133]).group(1)
print("ADR strings:\n ", fourth, "\n ", f1, "\n ", fixed)
md = (rec / "RESULTS.md").read_text()
print("RESULTS.md counts: fourth", md.count(fourth), "f1", md.count(f1), "fixed", md.count(fixed))
R = json.loads((rec / "results.json").read_text())
p = R["result"]["a5d_provenance"]
print("results.json a5d_provenance equal:", p["fourth_arm_string"] == fourth, p["f1_annotation"] == f1, p["provenance_sentence"] == fixed)
csvt = (rec / "classes.csv").read_text()
print("classes.csv header lines equal:", csvt.splitlines()[0] == "# " + fourth, csvt.splitlines()[1] == "# " + f1, csvt.splitlines()[2] == "# " + fixed)
# sections of RESULTS.md and whether each carries the three strings
secs = re.split(r"\n## ", md)
for s in secs:
    title = s.splitlines()[0][:60]
    print(f"  section {title!r}: fourth {fourth in s}, f1 {f1 in s}, fixed {fixed in s}, mentions A5-D {'A5-D' in s}")
# hypothesis rows containing a raw dict, and whether the dict content equals the fixed strings
for line in md.splitlines():
    if line.startswith("| H20-") and "{" in line:
        print("  raw dict in row:", line[:40], "| contains exact fourth/f1/fixed:", fourth in line, f1 in line, fixed in line)
