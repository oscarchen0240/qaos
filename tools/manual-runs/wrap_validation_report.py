#!/usr/bin/env python3
"""把 Validator subagent 輸出的 payload JSON 包成 TestValidationReport artifact。用法：wrap_validation_report.py <run_id> <task_id> <iteration> <report.json> <draft_aid> <rm_aid>"""
import sys, json, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
run, task, it, rep, did, rmid = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4], sys.argv[5], sys.argv[6]
payload = json.load(open(rep, encoding="utf-8"))
aid = ids.artifact_id("TestValidationReport")
art = {"artifact_id": aid, "artifact_type": "TestValidationReport", "schema_version": "1.0", "version": 1, "run_id": run, "task_id": task, "iteration": it,
       "created_by": "agent-test-validator", "created_at": store.now(), "status": "DRAFT", "source": {"type": "TestCaseDraft", "ids": [did]},
       "references": [{"entity_type": "Artifact", "id": did}, {"entity_type": "Artifact", "id": rmid}], "requires_approval": None, "payload": payload}
p = store.ROOT / "artifacts" / "validation" / run / f"{aid}.yaml"; store.save(p, art); print(p.relative_to(store.ROOT))
