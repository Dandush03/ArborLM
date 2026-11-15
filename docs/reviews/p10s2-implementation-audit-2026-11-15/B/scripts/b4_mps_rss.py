"""Audit B, check B4: does the rehearsal's memory measure (ru_maxrss) see memory allocated on MPS? 2 GiB of float32 on MPS, then ru_maxrss and torch.mps counters."""
import json, resource, torch
def rss(): return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss  # bytes on darwin
out = {"maxrss_before_bytes": rss()}
x = torch.ones(512 * 2**20, device="mps")  # 2 GiB
y = (x * 2).sum().item()
torch.mps.synchronize()
out.update({"maxrss_after_bytes": rss(), "mps_current_allocated_bytes": torch.mps.current_allocated_memory(), "mps_driver_allocated_bytes": torch.mps.driver_allocated_memory(), "check": y})
out["maxrss_increase_GiB"] = (out["maxrss_after_bytes"] - out["maxrss_before_bytes"]) / 2**30
out["mps_allocated_GiB"] = out["mps_current_allocated_bytes"] / 2**30
print(json.dumps(out, indent=1))
