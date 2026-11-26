"""Write deliver/registered_generator_files.json from out/generator_files_raw.json (auditor's script)."""
import json
import sys
from pathlib import Path

D = Path(sys.argv[1])
raw = json.loads((D / "out/generator_files_raw.json").read_text())
reg = json.loads(Path("studies/m0/manifests/registration_record.json").read_text())["registered_lineages"]
r = raw["registered_65"]
res = {
    "what": "The module files that define the 65 registered lineages' builders (the first solver is the builder's key, lead ruling R-52), with SHA-256 at HEAD of claude/m0-impl, for G-gen's record so that the freeze at 7cd0ac5a names files. Auditor's listing; independent engineering evidence, not Astra validation, not human approval. Astra review: NOT_PERFORMED.",
    "head_of_claude_m0_impl": raw["head"],
    "generators_commit": "7cd0ac5a2a2c5261352e66b4a41650576dcfe1be",
    "unchanged_since_generators_commit": "git diff --name-status 7cd0ac5a HEAD -- studies/m0 shows only additions (51, all under fresh_run/, registration/, solvers2/); every file below is byte-identical at 7cd0ac5a and HEAD, and the working tree is clean for them",
    "method": raw["method"],
    "a_files_that_define_Lineage_build": {"count": len(r["a_build_defined_in"]), "sha256": r["a_build_defined_in"]},
    "b_files_of_every_function_reachable_from_build": {"count": len(r["b_files_of_functions_behind_build"]), "sha256": r["b_files_of_functions_behind_build"]},
    "c_static_import_closure_of_b_recommended_freeze_list": {"count": len(r["c_static_import_closure"]), "sha256": r["c_static_import_closure"]},
    "d_every_worktree_file_loaded_by_importing_the_four_loaders_superset": {"count": len(raw["d_files_loaded_by_importing_the_four_loaders"]), "sha256": raw["d_files_loaded_by_importing_the_four_loaders"]},
    "loaders_named_by_capacity_RealSource": raw["loaders"],
    "per_registered_lineage": {x: {k: raw["per_lineage"][x][k] for k in ("build_defined_in", "build_qualname", "family", "files_of_functions_behind_build")} for x in sorted(reg)},
    "survivors_82_for_reference": {
        "a_count": len(raw["survivors_82"]["a_build_defined_in"]),
        "b_count": len(raw["survivors_82"]["b_files_of_functions_behind_build"]),
        "c_count": len(raw["survivors_82"]["c_static_import_closure"]),
        "c_sha256": raw["survivors_82"]["c_static_import_closure"],
    },
}
(D / "registered_generator_files.json").write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
print(len(r["a_build_defined_in"]), len(r["b_files_of_functions_behind_build"]), len(r["c_static_import_closure"]), len(raw["d_files_loaded_by_importing_the_four_loaders"]))
