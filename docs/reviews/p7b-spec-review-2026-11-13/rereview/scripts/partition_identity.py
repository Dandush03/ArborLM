"""Identity of the five registered partitions (ADR-0014 rev 3 section 4). Stdlib only.
Hash: SHA-256 of 4096 little-endian uint8 group IDs, slot order 0..4095 (auditor's encoding).
Also the shuffled list itself (4096 little-endian uint16), group ordering independent."""
import hashlib, random, sys, itertools, array
print(sys.version.split()[0])
G = {}
for s in (91601, 91602, 91603, 91604, 91605):
    lst = list(range(4096)); random.Random(s).shuffle(lst)
    gid = [0] * 4096
    for g in range(16):
        for x in lst[256 * g:256 * g + 256]:
            gid[x] = g
    G[s] = gid
    a = array.array("H", lst)
    if sys.byteorder != "little": a.byteswap()
    print(s, "group-id sha256", hashlib.sha256(bytes(gid)).hexdigest(), "shuffled-list sha256", hashlib.sha256(a.tobytes()).hexdigest(), "first5", lst[:5])
# pairwise: identical as set partitions? max co-membership overlap between any two groups
for a, b in itertools.combinations(G, 2):
    sets_a = [frozenset(i for i in range(4096) if G[a][i] == g) for g in range(16)]
    sets_b = [frozenset(i for i in range(4096) if G[b][i] == g) for g in range(16)]
    same = set(sets_a) == set(sets_b)
    mx = max(len(x & y) for x in sets_a for y in sets_b)
    print(f"{a} vs {b}: identical partition {same}; max group overlap {mx}/256")
# overlap of random groups with real branches
for s in G:
    mx = max(sum(1 for i in range(256 * b, 256 * b + 256) if G[s][i] == g) for b in range(16) for g in range(16))
    print(s, "max slots shared by a group and a real branch", mx, "(expected 16)")
