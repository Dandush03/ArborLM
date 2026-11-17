"""Recompute P9-II's code identity in the frozen tree (to explain the 6 'theirs' identity blocks of G4)."""
import hashlib, json, sys, tomllib
from pathlib import Path
t = Path(sys.argv[1])
f = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
c = lambda o: (json.dumps(o, sort_keys=True, separators=(",", ":")) + "\n").encode()
h = {}
for p in sorted((t/"studies/p9ii").glob("*.py")): h[f"studies/p9ii/{p.name}"] = f(p)
for p in sorted((t/"studies/p9ii/launch").glob("*.sh")): h[f"studies/p9ii/launch/{p.name}"] = f(p)
for n in ("__init__","classes","core","evaluate","model","report","stages","train"): h[f"studies/p9i/{n}.py"] = f(t/"studies/p9i"/f"{n}.py")
for n in ("__init__","controls","core","data","evaluate","model","objective","pool","train"): h[f"studies/p9/{n}.py"] = f(t/"studies/p9"/f"{n}.py")
print("p9ii source", hashlib.sha256(c(h)).hexdigest())
print("p9ii config", hashlib.sha256(c(tomllib.loads((t/"configs/p9ii_addressing.toml").read_text()))).hexdigest())
