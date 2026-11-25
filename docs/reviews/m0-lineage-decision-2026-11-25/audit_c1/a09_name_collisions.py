# ruff: noqa
# Audit: fixed variable names written by generators ('w' in cellular_update, 'tot' fast_power, 'far' turtle_walk, 'cst' string_pair_table,
# 'find' union_find_links) colliding with names drawn from VARS. Reads the a04 items (gen1) and the fixtures.
# (Saved copy of the code that was run inline as a heredoc with `python3 -`; output in a09_name_collisions_out.txt.)
import gzip, json, collections
FIX = '/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f/studies/m0/fixtures/c1_batch1/C1.cellular_update.jsonl'
VARS = ["a","b","c","d","e","m","n","p","q","r","s","t","u","v","w","x","y","z","total","count","acc","res","val","cur","best","out","k","j"]
def cellular_roles(prog):
    cells=prog[0][1]; rule=prog[1][1]; loop=prog[2]; g=loop[1]; nxt=loop[5][0][1]; i=loop[5][1][1]
    return dict(cells=cells,rule=rule,g=g,nxt=nxt,i=i)
for src in ['gen1','fixtures']:
    tot=coll=bad=0; roles=collections.Counter()
    if src=='gen1':
        recs=[]
        for lv in range(7):
            recs+= [json.loads(l) for l in gzip.open(f'gen1/items_C1.cellular_update_L{lv}.jsonl.gz','rt')]
    else:
        recs=[json.loads(l) for l in open(FIX)]
        recs=[{'prog':r['structured']['program'],'ans':r['answer'],'id':r['id']} for r in recs]
    for r in recs:
        p=r['prog']
        weighted = any(st[0]=='set' and st[1]=='w' and st[2]==['n',0] for st in p[3:])
        if not weighted: continue
        tot+=1
        ro=cellular_roles(p)
        for k,v in ro.items():
            if v=='w': roles[k]+=1; coll+=1
        if ro['i']=='w' or ro['cells']=='w':
            bad+=1
            if src=='fixtures': print('  fixture item with broken weighted shape:', r['id'], r['ans'])
    print(src, 'weighted-shape items', tot, 'items where a role variable is named w', coll, 'by role', dict(roles), 'semantics broken (i or cells == w)', bad)
for lid,fixed in [('fast_power','tot'),('turtle_walk','far'),('string_pair_table','cst'),('union_find_links','find')]:
    print(lid, fixed, 'in VARS:', fixed in VARS)
