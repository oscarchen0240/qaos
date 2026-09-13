#!/usr/bin/env python3
"""印出某 run 中指定 artifact_type 且 status=VALID 的 artifact_id（避免用 ls -t 拿到被 SUPERSEDED 的舊檔）。用法：pick_valid.py <run_id> <ArtifactType>"""
import sys, pathlib, yaml
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store
run, typ = sys.argv[1], sys.argv[2]
hits = [a for p in (store.ROOT / "artifacts").rglob(f"{run}/ART-*.yaml") for a in [store.load(p)] if a["artifact_type"] == typ and a["status"] == "VALID"]
if len(hits) != 1: sys.exit(f"{run} {typ} VALID 數量 = {len(hits)}")
print(hits[0]["artifact_id"])
