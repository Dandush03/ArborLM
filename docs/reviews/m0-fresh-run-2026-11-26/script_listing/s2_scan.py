"""Step 2 helper: AST scan of a file at b78e58b1 (via git cat-file) for every construct that can
reach another file: import / from-import, sys.path edits, importlib, runpy, exec/eval/compile,
subprocess/os.system, open()/Path()/read_text, and every string literal that looks like a path.
It prints facts with line numbers; resolution to repository files is done by s2_resolve.py and by
reading. Nothing scanned is executed."""
import ast, json, subprocess, sys

REPO = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f"
COMMIT = "b78e58b1"

def src(path):
    return subprocess.run(["git", "-C", REPO, "show", f"{COMMIT}:{path}"], check=True,
                          capture_output=True).stdout.decode()

CALLS = {"open", "Path", "exec", "eval", "compile", "__import__", "run", "Popen", "check_output",
         "check_call", "call", "system", "import_module", "spec_from_file_location", "run_path",
         "run_module", "read_text", "read_bytes", "insert", "append", "load", "loads",
         "module_from_spec", "exec_module", "getoutput"}

def callname(f):
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        base = callname(f.value) if isinstance(f.value, (ast.Name, ast.Attribute)) else "?"
        return f"{base}.{f.attr}"
    return "?"

def scan(path):
    s = src(path)
    t = ast.parse(s, filename=path)
    facts = []
    for n in ast.walk(t):
        if isinstance(n, ast.Import):
            for a in n.names:
                facts.append([n.lineno, "import", a.name])
        elif isinstance(n, ast.ImportFrom):
            facts.append([n.lineno, "from", ("." * n.level) + (n.module or ""),
                          [a.name for a in n.names]])
        elif isinstance(n, ast.Call):
            nm = callname(n.func)
            if nm.split(".")[-1] in CALLS:
                facts.append([n.lineno, "call", nm, ast.get_source_segment(s, n)[:300]])
        elif isinstance(n, ast.Constant) and isinstance(n.value, str):
            v = n.value
            if (".py" in v or ".json" in v or ".jsonl" in v or ".txt" in v or v.startswith("/")
                    or "studies/" in v or "docs/" in v or "_scratch" in v or "experiments/" in v
                    or "audit" in v or "final_" in v) and len(v) < 400:
                facts.append([n.lineno, "str", v])
    facts.sort(key=lambda x: (x[0], x[1]))
    return facts

if __name__ == "__main__":
    out = {p: scan(p) for p in sys.argv[1:]}
    json.dump(out, sys.stdout, indent=1, sort_keys=True)
    sys.stdout.write("\n")
