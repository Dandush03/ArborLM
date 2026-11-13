import json, torch
c = json.load(open("results/p5-2026-11-13/b101-o301-flat-s501/result.json"))["final"]["retrieval"]["selected_slot_counts"]
w = torch.tensor(c, dtype=torch.float32)
def gen(n):
    torch.set_num_threads(n); g = torch.Generator().manual_seed(91301000)
    a = torch.cat([torch.multinomial(w.expand(2048, 4096), 8, replacement=False, generator=g) for _ in range(16)])
    p = torch.randperm(32768, generator=torch.Generator().manual_seed(91201))
    b = torch.randint(0, 512, (1000, 512), generator=torch.Generator().manual_seed(91401))
    return a, p, b
default = torch.get_num_threads()
x = gen(default); y = gen(1)
print("default threads", default, "equal:", all(torch.equal(i, j) for i, j in zip(x, y)))
