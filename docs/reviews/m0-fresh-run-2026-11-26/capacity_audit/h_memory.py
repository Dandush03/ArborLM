"""Item 6 memory: the structures one cell holds at 240,000 keys (capacity._advance: a set of 16-byte bytes, a bytearray
of keys, an array('I') of attempts) and the Draw.keys bytes returned; measured with tracemalloc and ru_maxrss. Synthetic
keys (os.urandom), no generator."""
import array, os, resource, tracemalloc
N = 240_000
tracemalloc.start()
seen = set(); keys = bytearray(); first = array.array("I")
for i in range(N):
    k = os.urandom(16)
    seen.add(k); keys += k; first.append(i + 1)
draw_keys = bytes(keys)
cur, peak = tracemalloc.get_traced_memory()
print(f"one cell at {N} keys: tracemalloc current {cur/2**20:.1f} MiB, peak {peak/2**20:.1f} MiB; "
      f"process max RSS {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/2**20:.1f} MiB (macOS reports bytes)")
print(f"16 workers x peak: {16*peak/2**20:.0f} MiB; Draw.keys returned to the parent: {len(draw_keys)/2**20:.2f} MiB per cell")
