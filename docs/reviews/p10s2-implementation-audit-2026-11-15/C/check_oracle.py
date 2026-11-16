"""Auditor C: attempts to print a class, mechanism, router, composition or cost line without the oracle-assisted line.
Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval."""
import io, re, sys
PIN = sys.argv[1]; sys.path.insert(0, PIN); sys.path.insert(0, PIN + "/src"); sys.path.insert(0, sys.argv[2])
from studies.p10s2 import core, output, report, analysis
import check_rules as K, spec_rules as S
adr = open(PIN + "/docs/decisions/ADR-0022-p10-s2-two-teacher-transfer.md").read()
m = re.search(r'fixed line: \*\*"(.+?)"\*\*', adr)
print("ORACLE_LINE equals the ADR's fixed line:", m is not None and m.group(1) == core.ORACLE_LINE)
print("LEAD_RULE quoted exactly in ADR header, 11.3 and 18:", adr.count('"' + core.LEAD_RULE + '"'), "occurrences; core.LEAD_RULE =", repr(core.LEAD_RULE))
def attempt(name, fn):
    buf = io.StringIO()
    try:
        fn(buf)
        txt = buf.getvalue()
        print(f"{name}: PRINTED {'WITH' if core.ORACLE_LINE in txt else 'WITHOUT'} the line: {txt.strip()[:110]!r}")
    except output.OracleLineMissing as e:
        print(f"{name}: refused ({str(e)[:60]})")
    except Exception as e:
        print(f"{name}: raised {type(e).__name__}: {str(e)[:80]}")
from studies.p10s2 import classes as C
vr = C.value_rows(5000.0, 2419200.0, 8192)["line"]
vr2 = C.value_rows(5e6, 2419200.0, 8192)["line"]
ss = C.stored_size_line(134515008, 8192, [73944309, 74669178], 0.8, 0.7, 576)
attempt("A1 emit cost line FEWER VALUE ROWS ACTIVE", lambda b: output.emit([vr], b))
attempt("A2 emit cost line 'value rows active not fewer'", lambda b: output.emit([vr2], b))
attempt("A3 emit stored-size cost line", lambda b: output.emit([ss], b))
attempt("A4 emit teacher inference cost line", lambda b: output.emit(["teacher inference cost per accepted training item: 0.4 s"], b))
attempt("A5 emit router accuracy line", lambda b: output.emit(["replicate 0, router AB: route accuracy {'A': 1.0, 'B': 1.0, 'general': 1.0}"], b))
attempt("A6 emit GEN line", lambda b: output.emit(["r0/MAF/AB GEN loss increase 0.001: gate passes; the keyword router stayed silent"], b))
attempt("A7 emit_plain lower-case label", lambda b: output.emit_plain("label: transfer-positive (append-frozen)", b))
attempt("A8 emit_plain mixed-case class", lambda b: output.emit_plain("M-append-frozen: Acquires-And-Retains in both orders", b))
attempt("A9 emit_plain rehearsal rung outcome NOT STARTED: BUDGET (stages.cmd_rehearse:388)", lambda b: output.emit_plain("rehearsal record written to x; rung rule outcome: NOT STARTED: BUDGET", b))
attempt("A10 emit class line", lambda b: output.emit(["M-ii: AB ACQUIRES-AND-RETAINS"], b))
for name, rec in (("R1 record with router_table only", {"router_table": [{"accuracy": {"A": 1.0}}]}), ("R2 record with gen only", {"gen": {"M-append-frozen": True}}),
                  ("R3 record with cost_lines", {"cost_lines": ["TRAINING COST COMPARABLE"]}), ("R4 record with 'Class' (capitalized key)", {"Class": "ACQUIRES-AND-RETAINS"}),
                  ("R5 record with label inside a list of strings", {"summary": ["TRANSFER-POSITIVE (append-frozen)"]})):
    try:
        output.check_record(rec); print(name + ": ACCEPTED without the line")
    except output.OracleLineMissing:
        print(name + ": refused")
# full report on a good synthetic record: summary lines carry (n, U)?
base = {"s0": {"E_A": 0.1, "E_B": 0.1}, "t": {"E_A": 0.9, "E_B": 0.9}, "s0sub": {"E_A": 0.12, "E_B": 0.12}, "tsub": {"E_A": 0.88, "E_B": 0.88}}
cells = {}
for r in range(3):
    for (g, v), (ga, gb) in K.TEMPLATE.items():
        p = {"E_A": ga, "E_B": gb}
        cells[(r, g, v)] = S.Cell(panels=p, abl={q: {"unablated": p[q], "value_perm": 0.05, "code_perm": 0.08, "marker_only": 0.1} for q in p} if g in K.MEMORY else None, gen=0.001 if g in K.GEN else None)
nc = K.numeric_cells(base, cells)
out = analysis.analyze(K.serialize(base, nc, 3))
buf = io.StringIO(); output.emit(report.summary_lines(out), buf); print("terminal summary:\n" + buf.getvalue())
txt = report.render_report(out)
print("report mentions M-ii GEN result:", "M-ii" in txt and "GEN" in txt and "row 8" in txt, "| bootstrap interval printed:", "bootstrap" in txt.lower(), "| single-reference scores printed:", "single-reference" in txt.lower(), "| changed-row share printed:", "changed" in txt.lower())
print("report contains LEAD_RULE sentence:", core.LEAD_RULE in txt)
