#!/usr/bin/env python3
import sys, json, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
run, rep, bd = sys.argv[1], sys.argv[2], sys.argv[3]
payload = json.load(open(rep, encoding="utf-8")); aid = ids.artifact_id("BugValidationReport")
bdp = store.load(store.find_artifact(bd))["payload"]
art = {"artifact_id": aid, "artifact_type": "BugValidationReport", "schema_version": "1.0", "version": 1, "run_id": run, "task_id": "T2", "iteration": 0,
       "created_by": "agent-bug-validator", "created_at": store.now(), "status": "DRAFT", "source": {"type": "BugDraft", "ids": [bd]},
       "references": [{"entity_type": "Artifact", "id": bd}] + [{"entity_type": "Evidence", "id": e} for e in bdp["evidence_ids"]], "requires_approval": None, "payload": payload}
p = store.ROOT / "artifacts" / "validation" / run / f"{aid}.yaml"; store.save(p, art); print(p.relative_to(store.ROOT))
