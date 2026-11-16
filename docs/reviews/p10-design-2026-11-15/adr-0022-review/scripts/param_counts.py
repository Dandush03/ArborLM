"""Auditor's arithmetic for ADR-0022 review: parameter counts from the fetched config.json files,
memory and LoRA sizes, download totals from the fetched Hub tree listings. Usage:
python3 -I param_counts.py <web dir>"""
import json, sys, os
W = sys.argv[1]
j = lambda f: json.load(open(os.path.join(W, f)))
c = j("smol_config.json")
d, L, V, F, H, KV = c["hidden_size"], c["num_hidden_layers"], c["vocab_size"], c["intermediate_size"], c["num_attention_heads"], c["num_key_value_heads"]
hd = d // H; kvd = KV * hd
blk = d*d + 2*d*kvd + d*d + 3*d*F + 2*d
smol = L*blk + d + V*d
print("SmolLM2-135M params (tied emb):", smol, "| Hub safetensors total 134515008 ->", smol == 134515008)
mem = 4096*(16+d)+1
lora_per_rank = L*((d+d) + (d+kvd))
print("memory params N=4096:", mem, "| LoRA q,v params per rank:", lora_per_rank)
for target, name in ((mem, "one memory"), (2*mem-1, "two memories (M-joint 2N)")):
    r = round(target/lora_per_rank); print(f"  LoRA rank for {name}: {r} -> {r*lora_per_rank} ({100*(r*lora_per_rank-target)/target:+.2f}%)")
tot_t = 0
for n in ("en-de", "en-fr", "en-es"):
    c = j(f"opus_{n}_config.json")
    dm, Vt, Ft = c["d_model"], c["vocab_size"], c["encoder_ffn_dim"]
    att = 4*(dm*dm+dm); ffn = dm*Ft+Ft+Ft*dm+dm
    p = Vt*dm + c["encoder_layers"]*(att+ffn+4*dm) + c["decoder_layers"]*(2*att+ffn+6*dm) + Vt
    pos = 2*c["max_position_embeddings"]*dm
    print(f"opus-mt-{n}: params {p} (+{pos} sinusoidal position buffers = {p+pos})")
    if n != "en-es": tot_t += p
print("two primary teachers:", tot_t, "| student + two memories:", smol + 2*mem, "| ratio", round((smol+2*mem)/tot_t, 4))
