"""Collect every lineage-id-shaped string from every file under studies/m0/manifests (json, md, txt, jsonl), and compare with the code enumeration (e01 output).
Standard library only; reads files as text; computes no rate."""
import os, re, sys, json, hashlib
root = 'studies/m0/manifests'
code_out = sys.argv[1]
pat = re.compile(r'(?<![A-Za-z0-9_.])((?:R1|R2|M1|C1|K0)\.[a-z][a-z0-9_]*)')
code_ids = set()
for line in open(code_out):
    if line[:3] in ('R1.', 'R2.', 'M1.', 'C1.', 'K0.'):
        code_ids.add(line.split()[0])
per_file = {}
for fn in sorted(os.listdir(root)):
    p = os.path.join(root, fn)
    if not os.path.isfile(p): continue
    t = open(p, encoding='utf-8', errors='replace').read()
    per_file[fn] = set(pat.findall(t))
man_ids = set().union(*per_file.values())
print('manifest files', len(per_file))
print('ids in manifests', len(man_ids), 'ids in code', len(code_ids))
print('IN CODE, IN NO MANIFEST:', len(code_ids - man_ids))
for i in sorted(code_ids - man_ids): print('  ', i)
print('IN A MANIFEST, NOT IN CODE:', len(man_ids - code_ids))
for i in sorted(man_ids - code_ids):
    print('  ', i, 'in', ','.join(f for f, s in per_file.items() if i in s))
