"""Re-check auditor C: the predecessor's oracle-line counterexamples A1-A10 and R1-R5 on the fixed output module, the
report on complete synthetic records (composition included), and a scan of the report for autonomous-memory wording.
Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval. Usage: <python> check_oracle_v2.py <pin>"""

import copy
import io
import re
import sys
from pathlib import Path

PIN = sys.argv[1]
sys.path.insert(0, PIN)
sys.path.insert(0, PIN + "/src")
sys.path.insert(0, str(Path(__file__).parent))

from studies.p10s2 import analysis, core, output, report  # noqa: E402
from studies.p10s2 import classes as C  # noqa: E402

import check_edges_v2_lib as E  # noqa: E402

adr = open(PIN + "/docs/decisions/ADR-0022-p10-s2-two-teacher-transfer.md").read()
add = open(PIN + "/docs/decisions/ADR-0022-addendum-combined-tasks.md").read()
m = re.search(r'fixed line: \*\*"(.+?)"\*\*', adr)
print("ORACLE_LINE equals the ADR s11.3 fixed line:", m is not None and m.group(1) == core.ORACLE_LINE)
m2 = re.search(r'Second fixed line, on every composition line and every composition table:\*\* "(.+?)"', add)
print("COMBINED_LINE equals the addendum s9 second fixed line:", m2 is not None and m2.group(1) == core.COMBINED_LINE)
print("LEAD_RULE quoted exactly: ADR", adr.count('"' + core.LEAD_RULE + '"'), "times; addendum", add.count('"' + core.LEAD_RULE + '"'), "times")


def attempt(name, fn):
    buf = io.StringIO()
    try:
        fn(buf)
        txt = buf.getvalue()
        lines = txt.strip().split("\n")
        print(f"{name}: printed, first line is the oracle line: {lines[0] == core.ORACLE_LINE}; text: {lines[-1][:90]!r}")
    except output.OracleLineMissing as e:
        print(f"{name}: refused ({str(e)[:60]})")
    except Exception as e:  # noqa: BLE001
        print(f"{name}: raised {type(e).__name__}: {str(e)[:80]}")


vr = C.value_rows(5000.0, 2419200.0, 8192)["line"]
vr2 = C.value_rows(5e6, 2419200.0, 8192)["line"]
ss = C.stored_size_line(134515008, 8192, [73944309, 74669178], 0.8, 0.7, 576)
attempt("A1 emit FEWER VALUE ROWS ACTIVE", lambda b: output.emit([vr], b))
attempt("A2 emit 'value rows active not fewer'", lambda b: output.emit([vr2], b))
attempt("A3 emit stored-size line", lambda b: output.emit([ss], b))
attempt("A4 emit teacher inference cost line", lambda b: output.emit(["teacher inference cost per accepted training item: 0.4 s"], b))
attempt("A5 emit router accuracy line", lambda b: output.emit(["replicate 0, router AB: route accuracy {'A': 1.0}"], b))
attempt("A6 emit GEN line", lambda b: output.emit(["r0/MAF/AB GEN loss increase 0.001: the keyword router stayed silent"], b))
attempt("A7 emit_plain lower-case label", lambda b: output.emit_plain("label: transfer-positive (append-frozen)", b))
attempt("A8 emit_plain mixed-case class", lambda b: output.emit_plain("M-append-frozen: Acquires-And-Retains in both orders", b))
attempt("A9 emit_plain rung outcome NOT STARTED: BUDGET", lambda b: output.emit_plain("rehearsal record written to x; rung rule outcome: NOT STARTED: BUDGET", b))
attempt("A10 emit class line", lambda b: output.emit(["M-ii: AB ACQUIRES-AND-RETAINS"], b))
attempt("A11 emit_plain lower-case composition line", lambda b: output.emit_plain("C1 M-append-frozen: composes", b))
attempt("A12 emit_plain 'H_a 0.91 on the second answer' (a composition number, no word)", lambda b: output.emit_plain("C1 M-ii r0: H_a 0.91 / 0.88 on the second answer", b))
for name, rec in (("R1 router_table only", {"router_table": [{"accuracy": {"A": 1.0}}]}), ("R2 gen only", {"gen": {"M-append-frozen": True}}),
                  ("R3 cost_lines", {"cost_lines": ["TRAINING COST COMPARABLE"]}), ("R4 'Class' key", {"Class": "ACQUIRES-AND-RETAINS"}),
                  ("R5 label in a list of strings", {"summary": ["TRANSFER-POSITIVE (append-frozen)"]}),
                  ("R6 composition field without the second line", {"oracle_line": core.ORACLE_LINE, "composition": "COMPOSES"}),
                  ("R7 H values under a neutral key", {"h_by_answer": {"A": 0.9, "B": 0.85}})):
    try:
        output.check_record(rec)
        print(name + ": ACCEPTED without the line")
    except output.OracleLineMissing:
        print(name + ": refused")
for name, text in (("T1 composition block without the second line", core.ORACLE_LINE + "\n- C2 L-sep: COMPOSES"),
                   ("T2 composition line split off by a blank line", core.ORACLE_LINE + "\n" + core.COMBINED_LINE + "\nTable 4\n\n- C2 L-sep: COMPOSES")):
    try:
        output.check_text(text)
        print(name + ": ACCEPTED")
    except output.OracleLineMissing:
        print(name + ": refused")

st = E.build()
out = analysis.analyze(copy.deepcopy(st))
buf = io.StringIO()
output.emit(report.summary_lines(out), buf)
print("terminal summary (each class line with the design suffix):")
print(buf.getvalue())
txt = report.render_report(out)
rec = report.render_json(out)
print("report renders and passes check_text; JSON passes check_record:", bool(txt) and bool(rec))
print("report label row:", out["label_row"], "| composition section present:", "Table 4. Composition" in txt)
comp = [ln for ln in txt.split("\n") if ln.startswith("- C1 ") or ln.startswith("- C2 ")]
print("composition lines:", len(comp), "| example:", comp[2][:200] if len(comp) > 2 else comp)
blocks = txt.split("\n\n")
cb = [b for b in blocks if "Table 4. Composition" in b][0].split("\n")
print("composition block starts with the oracle line then the second line:", cb[0] == core.ORACLE_LINE and cb[1] == core.COMBINED_LINE)
print("item count n (|E_C|) printed on a composition line:", any(re.search(r"\bn = %d\b|\bitems\b" % 6, ln) for ln in comp), "| '(n replicates, U = ...)' on each composition line:", all("U =" in ln for ln in comp if not ln.startswith("  ")))
print("report contains the human lead's sentence verbatim:", core.LEAD_RULE in txt)
risky = [ln for ln in txt.split("\n") if re.search(r"autonomous|learned[- ]memory|success|proves?|demonstrat", ln, re.IGNORECASE)]
print("lines in the report with autonomous/learned-memory/success wording:")
for ln in risky:
    print("   ", ln[:200])

# a record whose composition lines carry COMPOSES (Stage 0 low, teachers high, arms keep their gain) against one whose lines are all NOT_EVALUATED
import synth as Y  # noqa: E402

for title, arm_k in (("arms keep 0.95 of their gain", 0.95), ("all lines NOT_EVALUATED (arm single gap below 0.50)", None)):
    st2 = copy.deepcopy(st)
    s0c = Y.comb_record({"C1": {"A": 0.2, "B": 0.2}, "C2": {"A": 0.2, "B": 0.2}, "single": {"A": 0.2, "B": 0.2}})
    ensc = Y.comb_record({"C1": {"A": 0.8, "B": 0.8}, "C2": {"A": 0.8, "B": 0.8}, "single": {"A": 0.8, "B": 0.8}})
    armc = Y.comb_record({"C1": {"A": 0.2 + 0.5 * arm_k, "B": 0.2 + 0.5 * arm_k}, "C2": {"A": 0.2 + 0.5 * arm_k, "B": 0.2 + 0.5 * arm_k}, "single": {"A": 0.7, "B": 0.7}}) if arm_k else Y.comb_record({"C1": {"A": 0.3, "B": 0.3}, "C2": {"A": 0.3, "B": 0.3}, "single": {"A": 0.3, "B": 0.3}})
    st2["baseline"]["combined"] = {"stage0": s0c, "ensemble": ensc}
    for rep in st2["replicates"]:
        for c in rep["cells"].values():
            for sn in c["scores"].values():
                if "combined" in sn:
                    sn["combined"] = armc
        for a in ("M-i-separate", "L-sep"):
            rep["assembled"][a]["combined"] = armc
    o2 = analysis.analyze(st2)
    t2 = report.render_report(o2)
    cb2 = [b for b in t2.split("\n\n") if "Table 4. Composition" in b][0].split("\n")
    print(f"[{title}] classes: {sorted({v['composition'] for k in ('C1', 'C2') for a, v in o2['composition']['arms'][k].items() if not a.startswith('_')})}"
          f" | block header = oracle line: {cb2[0] == core.ORACLE_LINE}, second fixed line: {cb2[1] == core.COMBINED_LINE}")
