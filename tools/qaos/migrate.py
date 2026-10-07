"""移轉 `migrate`、`migrate verify`、`migrate rollback`（需求 A 第 5 章 §11～§13；附錄 A 5-1～5-11）。

migrate（X）：
- 業務寫入在擷取中產生，順序：凍結 legacy audit → `--cancel-run` 的取消 → R000／R000.meta／索引 → run sidecar → CLR rev 0 → TC sidecar → 移轉標記；
  衍生輸出（CLR／APR render）與第一次 audit.log render 排在之後，最後是 completed 狀態紀錄。
- 保存計畫前（post_plan），依實際 pre-state 逐路徑產生清單（manifest）與 backup，以「清單一步、每個 backup 一步」插在最前面。
migrate rollback（R）：不經擷取，依 T1～T7 准入後直接建立計畫；步驟分 takeover／restore／marker／terminal 四組，執行時穿插檢查 A、檢查 B。
migrate verify：唯讀核對（不取鎖）。"""
import json, re, subprocess, yaml
from . import store, rm, spec_ops, sources, operation as op
from .operation import Refused, EvidenceConflict, OperationError

GLOBAL = op.GLOBAL
MARKER = op.MARKER_PATH

def manifest_path(x: str) -> str: return f"{op.op_dir(GLOBAL, x)}/manifest.yaml"
def backup_path(x: str, path: str) -> str: return f"{op.op_dir(GLOBAL, x)}/backup/{path}"

def _sha(path: str) -> str | None: return op._cur_sha(path)

# ---------------------------------------------------------------- migrate：擷取中的業務寫入
def _check_modes(ack: list[str], cancel: list[str]) -> list[str]:
    """RUNNING 的 run 必須逐一指定處理方式（§11.2；附錄 A 5-6）。回傳 RUNNING 的 run。"""
    runs = {p.parent.name: store.load(p) for p in store.glob("runs/*/run.yaml")}
    running = sorted(r for r, d in runs.items() if d.get("status") == "RUNNING")
    both = sorted(set(ack) & set(cancel))
    if both: raise Refused(f"同一個 run 不能同時 --acknowledge-idle 與 --cancel-run：{both}")
    bad = sorted(r for r in set(ack) | set(cancel) if r not in running)
    if bad: raise Refused(f"只有 RUNNING 的 run 需要指定處理方式；這些不是 RUNNING：{bad}")
    missing = [r for r in running if r not in set(ack) | set(cancel)]
    if missing: raise Refused(f"RUNNING 的 run 必須逐一指定處理方式（--acknowledge-idle 或 --cancel-run）：{missing}")
    return running

def _check_no_declarations():
    """移轉前不存在任何引用宣告；有就拒絕（第 5 章 §3.5；AC-09-91）。不能只看目前 references 是否非空。"""
    bad = []
    for p in store.glob("specs/*/*/*/spec.yaml"):
        for v in store.load(p)["versions"]:
            if v.get("references") or v.get("reference_declarations"): bad.append(f"{store.load(p)['spec_id']}@{v['spec_version']}")
    if bad: raise Refused(f"移轉前已有引用宣告（正式流程中不會發生）：{bad}；移轉拒絕")

def _legacy_rms() -> list[tuple[str, str]]:
    out = []
    for view in store.glob("artifacts/requirements/*/*/requirements.yaml"):
        sid, ver = view.parent.parent.name, view.parent.name[1:]
        if not rm.index(sid, ver): out.append((sid, ver))
    return sorted(out)

def _write_r000(sid: str, ver: str, x: str):
    """R000 = legacy requirements.yaml 的逐位元複本；R000.meta.yaml 只建立一次（target_decl_rev 0、reference_pins []）；索引。檢視不修改。"""
    data = store.read_bytes(store.requirements_path(sid, ver)); sha = store.sha256_bytes(data)
    store.write_bytes(rm.rev_path(sid, ver, "R000"), data)
    store.save(rm.meta_path(sid, ver), {"revision": "R000", "legacy": True, "revision_sha256": sha, "target_decl_rev": 0, "reference_pins": [], "created_by_op": x})
    store.save(rm.index_path(sid, ver), {"spec_id": sid, "spec_version": ver, "revisions": [
        {"revision": "R000", "path": rm.rev_path(sid, ver, "R000"), "sha256": sha, "created_at": store.now(), "op_id": x, "reason": "legacy"}]})

def _r000(sid, ver) -> dict | None:
    """本次移轉剛建立（overlay）或既有的 R000 pin。"""
    if not store.exists(rm.rev_path(sid, ver, "R000")): return None
    return {"spec_id": sid, "spec_version": str(ver), "revision": "R000", "sha256": store.sha256_file(rm.rev_path(sid, ver, "R000"))}

def _run_sidecar(run: dict, x: str) -> dict | None:
    """依綁定表的移轉欄（§4.2）；regression-generation 不產生 sidecar（明確例外）。"""
    wf, inp, rid = run["workflow_id"], run.get("input") or {}, run["run_id"]
    if run.get("requirement_model_revision") or run.get("from_requirement_model_revision"): return None
    sc = {"subject": {"run_id": rid}, "legacy_binding": wf in ("testcase-revision", "manual-test-to-regression"), "created_by_op": x}
    if wf == "regression-generation": return None
    if wf == "spec-change-impact":
        frm, to = _r000(inp["spec_id"], inp["from_version"]), _r000(inp["spec_id"], inp["to_version"])
        if frm: sc["from_requirement_model_revision"] = frm
        if to: sc["requirement_model_revision"] = to
        return sc if (frm or to) else None
    if wf == "manual-test-to-regression":
        from . import engine
        tgt = engine._target_of(wf, inp)
        if tgt is None: sc["binding"] = "none"; return sc                       # 附錄 A 5-4
        pin = _r000(*tgt)
        if pin is None: sc["binding"] = "none"; return sc
        sc["requirement_model_revision"] = pin; return sc
    sid, ver = inp.get("spec_id"), inp.get("spec_version")
    pin = _r000(sid, ver) if sid and ver else None
    if pin is None: return None                                                  # 例如 T1 尚未完成：不綁，之後正常綁定
    sc["requirement_model_revision"] = pin; return sc

def _body(by: str, ack: list[str], cancel: list[str]) -> dict:
    from . import engine, clarification
    x = store.capturing().op_id; exceptions = []
    if store.exists(MARKER): raise Refused("移轉標記已存在（已移轉）；移轉拒絕")
    running = _check_modes(ack, cancel)
    _check_no_declarations()
    # 1. 凍結 legacy audit
    logs, runs = {}, sorted(p.parent.name for p in store.glob("runs/*/run.yaml"))
    for lg in sorted({store.rel(p) for p in store.glob("runs/*/audit.log")} | ({"runs/_audit.log"} if store.exists("runs/_audit.log") else set())):
        legacy = lg.replace("audit.log", "audit.legacy.log")
        if store.exists(legacy): raise Refused(f"{legacy} 已存在，移轉拒絕")
        data = store.read_bytes(lg); store.write_bytes(legacy, data)
        logs[lg] = {"legacy": "frozen", "sha256": store.sha256_bytes(data)}
    if "runs/_audit.log" not in logs: logs["runs/_audit.log"] = {"legacy": "absent"}
    for r in runs:
        if f"runs/{r}/audit.log" not in logs: logs[f"runs/{r}/audit.log"] = {"legacy": "absent"}
    # 2. cancel-run：同一個移轉操作中先取消（只寫事件檔；render 在標記之後）
    cancelled_aprs = {}
    for r in cancel: cancelled_aprs[r] = engine.cancel_body(r, by, reason="migrate --cancel-run")
    # 3. R000、R000.meta、索引
    rms = _legacy_rms()
    for sid, ver in rms: _write_r000(sid, ver, x)
    # 4. run sidecar
    sidecars = []
    for r in runs:
        sc = _run_sidecar(store.load(f"runs/{r}/run.yaml"), x)
        if sc is not None: store.save(rm.run_sidecar_path(r), sc); sidecars.append(r)
    # 5. CLR rev 0（legacy basis；值由本計畫固定）
    rev0 = []
    for p in store.glob("clarifications/*/*/CLR-*.yaml"):
        c = store.load(p)
        if not c.get("answer") or c.get("answer_revisions"): continue
        try: c["answer_revisions"] = [clarification._legacy_rev0(c)]
        except spec_ops.SpecError as e:                                          # spec 版本沒有匯入：不捏造 pin，記在例外並回報（附錄 A 5-12）
            exceptions.append({"path": store.rel(p), "kind": "clr_rev0_skipped", "reason": str(e)}); continue
        clarification.save(c); rev0.append(c["clarification_id"])
    # 6. TC sidecar：ACTIVE、PENDING_APPROVAL 的 TC 版本綁該版本 spec_version 的 R000，legacy_binding: true
    tcs = []
    for p in store.glob("testcases/versions/*/v*.yaml"):
        v = store.load(p)
        if v.get("status") not in ("ACTIVE", "PENDING_APPROVAL") or v.get("requirement_model_revision"): continue
        pin = _r000(v["spec_id"], v["spec_version"])
        if pin is None: exceptions.append({"path": store.rel(p), "kind": "tc_sidecar_skipped", "reason": f"{v['spec_id']}@{v['spec_version']} 沒有需求模型"}); continue
        store.save(rm.tc_sidecar_path(v["testcase_id"], v["version"]), {"subject": {"testcase_id": v["testcase_id"], "version": v["version"]},
                                                                        "requirement_model_revision": pin, "legacy_binding": True, "created_by_op": x})
        tcs.append(f"{v['testcase_id']}-v{v['version']}")
    # 7. 移轉標記（manifest_sha256 在 post_plan 補上）
    mode = {**{r: "acknowledge_idle" for r in ack}, **{r: "cancel_run" for r in cancel}}
    store.save(MARKER, {"migrate_op_id": x, "migrated_at": store.now(), "migrated_by": by, "mode_per_run": mode, "runs": runs, "logs": logs,
                        "manifest_sha256": None, "exceptions": exceptions})
    store.audit(None, by, "MIGRATE", f"{len(logs)} logs; runs={len(runs)}; R000={len(rms)}; sidecars={len(sidecars)}; CLR rev0={len(rev0)}; TC sidecars={len(tcs)}; exceptions={len(exceptions)}")
    return {"logs": len(logs), "runs": len(runs), "r000": len(rms), "run_sidecars": len(sidecars), "clr_rev0": len(rev0), "tc_sidecars": len(tcs),
            "cancelled": cancelled_aprs, "exceptions": exceptions}

# ---------------------------------------------------------------- migrate：清單與 backup（post_plan）
def _untouched(restore_paths: set[str], step_paths: set[str]) -> list[dict]:
    pats = ["specs/*/*/*/spec.yaml", "testcases/versions/*/v*.yaml", "testcases/registry/*.yaml", "runs/*/run.yaml", "artifacts/requirements/*/*/requirements.yaml",
            "approvals/APR-*.yaml", "clarifications/*/*/CLR-*.yaml", f"{op.INDEX_DIR}/*.yaml", f"{op.STATUS_DIR}/*.yaml"]
    out = []
    for pat in pats:
        for p in sorted((store.ROOT).glob(pat)):
            r = store.rel(p)
            if p.is_file() and r not in restore_paths and r not in step_paths and not p.name.startswith(".qaos-tmp"):
                out.append({"path": r, "pre_sha256": store.sha256_bytes(p.read_bytes())})
    return out

def _base_commit():
    try: return subprocess.run(["git", "-C", str(store.ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5).stdout.strip() or None
    except Exception: return None

def _category(path: str) -> str:
    for prefix, cat in (("runs/", "run"), ("approvals/", "approval"), ("clarifications/", "clarification"), ("artifacts/requirements/_bindings/", "run_sidecar"),
                        ("testcases/_bindings/", "tc_sidecar"), ("artifacts/requirements/", "requirement_model")):
        if path.startswith(prefix): return "marker" if path == MARKER else cat
    return "other"

def post_plan(plan: dict, blobs: dict) -> tuple[dict, dict]:
    x = plan["op_id"]; steps = plan["steps"]
    body = [s for s in steps if s["kind"] != "status_final"]; final = steps[-1]
    restore, remove, events = [], [], []
    for s in body:
        if s["kind"] == "event": events.append(s); continue
        if s["expected_before"] is not None:
            restore.append({"path": s["path"], "category": _category(s["path"]), "pre_sha256": s["expected_before"], "backup_path": backup_path(x, s["path"]),
                            "backup_sha256": s["expected_before"], "planned_post_sha256": s["expected_after"]})
        else:
            remove.append({"path": s["path"], "category": _category(s["path"]), "planned_post_sha256": s["expected_after"]})
    # 移轉標記：補上 manifest_sha256（先以 None 計算清單，清單本身不記標記的 planned sha，避免循環；verify 依計畫步驟核對標記）
    for r in remove:
        if r["path"] == MARKER: r["planned_post_sha256"] = None
    # backup 步驟（每個 restore 一步）與清單步驟
    backups = []
    for r in restore:
        data = op._disk_bytes(r["path"]); sha = store.sha256_bytes(data); blobs[sha] = data
        backups.append({"path": r["backup_path"], "kind": "control", "expected_before": None, "expected_after": sha, "blob": sha})
    manifest = {"migrate_op_id": x, "created_at": plan["clock"], "base_commit": _base_commit(),
                "mode_per_run": yaml.safe_load(blobs[next(s["blob"] for s in body if s["path"] == MARKER)].decode())["mode_per_run"],
                "restore": restore, "remove": remove, "retain_audit": [], "planned_audit": [],
                "shared_control": [{"path": op.LOCK_PATH, "category": "control", "pre_state": "present" if (store.ROOT / op.LOCK_PATH).exists() else "absent", "rule": "必須存在；永不刪除"},
                                   {"path": op.OWNER_PATH, "category": "control", "pre_state": "present" if (store.ROOT / op.OWNER_PATH).exists() else "absent", "rule": "任意內容，只供診斷"},
                                   {"path": op.MAINT_PATH, "category": "control", "pre_state": "present", "rule": "依維護狀態，由 maintenance start|end 管理"},
                                   {"path": op.INDEX_DIR, "category": "control", "pre_state": "present", "rule": "只新增檔案；清單列出的既有紀錄不變"},
                                   {"path": op.STATUS_DIR, "category": "control", "pre_state": "present", "rule": "只新增檔案；清單列出的既有紀錄不變"}],
                "untouched": _untouched({r["path"] for r in restore}, {s["path"] for s in body})}
    # 重新編號：清單一步、backup 各一步，接著原有步驟
    new_steps = [{"seq": 0, "step_id": "manifest", "path": manifest_path(x), "kind": "control", "expected_before": None, "expected_after": None, "blob": None}]
    new_steps += [{**b, "step_id": f"backup{i + 1}"} for i, b in enumerate(backups)] + body + [final]
    for i, s in enumerate(new_steps, start=1): s["seq"] = i
    # 預定稽核輸出（事件、完成紀錄、completed）與控制證據
    for s in new_steps[1:-1]:
        circular = s["path"] == MARKER                                             # 標記內容含清單 sha：它的完成紀錄只列路徑（避免循環）
        manifest["planned_audit"].append({"path": op.progress_path(plan, s), "producing_step": s["seq"], "kind": "progress",
                                          "planned_sha256": None if circular else store.sha256_bytes(op.progress_bytes(plan, s))})
        if s["kind"] == "event": manifest["planned_audit"].append({"path": s["path"], "producing_step": s["seq"], "kind": "event", "planned_sha256": s["expected_after"]})
    manifest["planned_audit"].append({"path": op.progress_path(plan, new_steps[0]), "producing_step": 1, "kind": "progress", "planned_sha256": None})   # 清單自己的完成紀錄（含清單 sha，避免循環不列 sha）
    manifest["planned_audit"].append({"path": final["path"], "producing_step": final["seq"], "kind": "status", "planned_sha256": final["expected_after"]})
    manifest["retain_audit"] = [{"path": op.plan_path(GLOBAL, x), "category": "control", "producing_step": None, "kind": "control", "planned_sha256": None},
                                {"path": f"{op.INDEX_DIR}/<plan_seq>-{x}.yaml", "category": "control", "producing_step": None, "kind": "index", "planned_sha256": None}] + \
                               [{"path": b["path"], "category": "control", "producing_step": b["seq"], "kind": "control", "planned_sha256": b["expected_after"]} for b in new_steps[1:1 + len(backups)]]
    mdata = store.dump(manifest); msha = store.sha256_bytes(mdata); blobs[msha] = mdata
    new_steps[0]["expected_after"] = msha; new_steps[0]["blob"] = msha
    # 標記補上 manifest_sha256（標記步驟的內容因此改變；render 內容不受影響）
    mstep = next(s for s in new_steps if s["path"] == MARKER)
    mk = yaml.safe_load(blobs[mstep["blob"]].decode()); mk["manifest_sha256"] = msha
    mkdata = store.dump(mk); mstep["blob"] = mstep["expected_after"] = store.sha256_bytes(mkdata); blobs[mstep["blob"]] = mkdata
    plan["steps"] = new_steps; plan["manifest_sha256"] = msha
    return plan, blobs

def migrate(by: str, ack: list[str], cancel: list[str], new_request: bool = False):
    ack, cancel = sorted(ack), sorted(cancel)
    return op.run_operation("migrate", lambda: _body(by, ack, cancel), request=lambda: {"params": {"by": by, "acknowledge_idle": ack, "cancel_run": cancel}},
                            new_request=new_request, post_plan=post_plan)

def load_manifest(x: str) -> dict:
    p = manifest_path(x)
    if not store.exists(p): raise EvidenceConflict(f"{x} 的移轉清單不存在")
    return store.load(p)

def planned_manifest(xplan: dict) -> dict:
    """從 X 計畫的清單步驟取得清單內容（清單檔可能還沒寫）。"""
    st = xplan["steps"][0]
    if st["step_id"] != "manifest": raise EvidenceConflict(f"{xplan['op_id']} 的計畫沒有清單步驟")
    return yaml.safe_load(op._load_blob(xplan, st).decode())

# ---------------------------------------------------------------- rollback：x_progress、later_ops、可行性（T5～T7）
def x_progress(xplan: dict) -> dict:
    """T5：對 X 執行 classify_steps 並凍結結果（§13.5）。業務檔的 external_change 不列入 conflicts（由 T7 判斷）。"""
    status_x = op.plan_state(xplan["op_id"])
    cls = op.classify_steps(xplan)
    steps_out, tail = [], None
    final = xplan["steps"][-1]; final_present = (store.ROOT / final["path"]).is_file()
    for s in xplan["steps"][:-1]:
        st = cls.status.get(s["seq"]); proof = None; ev = None
        if st == "done": proof = "progress"; ev = {"path": s["path"], "sha256": s["expected_after"]}
        elif st == "tail": proof = "content_tail"; tail = s["seq"]; ev = {"path": s["path"], "sha256": s["expected_after"]}; st = "done"
        elif st == "external_change": proof = None
        steps_out.append({"seq": s["seq"], "step_id": s["step_id"], "kind": s["kind"], "status": st, "proof": proof, "evidence": ev})
    steps_out.append({"seq": final["seq"], "step_id": final["step_id"], "kind": "status", "status": "done" if final_present else "not_executed",
                      "proof": "completed_status" if final_present else None, "evidence": {"path": final["path"], "sha256": final["expected_after"]} if final_present else None})
    conflicts = [dict(c, step_id=next((s["step_id"] for s in xplan["steps"] if s["seq"] == c.get("seq")), None)) for c in cls.conflicts]
    if status_x == "completed":                                                  # §13.4：X 已完成時不跑尾端推導
        tail = None
        for s, row in zip(xplan["steps"][:-1], steps_out):
            pp = store.ROOT / op.progress_path(xplan, s)
            if not pp.is_file() or pp.read_bytes() != op.progress_bytes(xplan, s):
                conflicts.append({"seq": s["seq"], "step_id": s["step_id"], "path": op.progress_path(xplan, s), "reason": "X 已完成，但這一步的完成紀錄缺失或不符"})
            elif row["status"] == "done": row["proof"] = "progress"
            if s["kind"] in op.AUDIT_KINDS and _sha(s["path"]) != s["expected_after"]:
                conflicts.append({"seq": s["seq"], "step_id": s["step_id"], "path": s["path"], "reason": "X 已完成，但稽核物不等於計畫值"})
        if _sha(final["path"]) != final["expected_after"]:
            conflicts.append({"seq": final["seq"], "step_id": "completed", "path": final["path"], "reason": "X 的 completed 紀錄內容不符"})
    # not_executed 的步驟：預定事件、完成紀錄必須不存在
    for s in xplan["steps"][:-1]:
        if cls.status.get(s["seq"]) == "not_executed" and (store.ROOT / op.progress_path(xplan, s)).exists():
            conflicts.append({"seq": s["seq"], "step_id": s["step_id"], "path": op.progress_path(xplan, s), "reason": "未執行的步驟卻有完成紀錄"})
    if status_x == "in_progress" and final_present: conflicts.append({"seq": final["seq"], "step_id": "completed", "path": final["path"], "reason": "X 未完成卻有 completed 紀錄"})
    ncc = [{"path": nc["path"], "ok": op._cur_sha(nc["path"]) == nc["content_sha256"]} for nc in xplan.get("no_change", [])]
    return {"x_status_at_creation": status_x, "tail_step": tail, "steps": steps_out, "conflicts": conflicts, "no_change_check": ncc}

BUSINESS_EXCLUDE = op.CONTROL_ACTIONS | {"operation_resume"}

def later_ops(x: str, r: str | None = None) -> list[dict]:
    regs = op.registrations(); xs = regs[x]["plan_seq"]; out = []
    for o, reg in sorted(regs.items(), key=lambda kv: kv[1]["plan_seq"]):
        if reg["plan_seq"] <= xs or o == r or reg["action"] in BUSINESS_EXCLUDE: continue
        plan = op.verify_registration(o, reg)                                    # 盤點時也核對登錄紀錄（附錄 A 4-11）
        out.append({"op_id": o, "plan_seq": reg["plan_seq"], "action": reg["action"], "targets": plan["canonical_request"].get("targets", {}),
                    "paths": [s["path"] for s in plan["steps"] if s["kind"] not in ("status_final",)]})
    return out

def _later_report(later: list[dict], manifest: dict) -> str:
    listed = {e["path"] for e in manifest["restore"] + manifest["remove"]} | {u["path"] for u in manifest["untouched"]}
    lines = ["後續操作報告（只能盤點經由執行器計畫的寫入；外部手動修改或未接上執行器的寫入不在內）："]
    for o in later:
        lose = [p for p in o["paths"] if "/revisions/" in p or p.startswith("clarifications/")]
        conflict = [p for p in o["paths"] if p in listed]
        lines.append(f"- {o['op_id'][:12]}… {o['action']} targets={json.dumps(o['targets'], ensure_ascii=False)}")
        lines.append(f"  會失去：{lose or '—'}；需要人工轉換：{[p for p in o['paths'] if p.startswith('clarifications/')] or '—'}；衝突：{conflict or '—'}")
    return "\n".join(lines)

AUDIT_VIEW = re.compile(r"runs/(_audit|RUN-[0-9]{8}-[0-9]{3,}/audit)\.log")

def _current_render(path: str, cur: str | None) -> bool:
    """audit.log 是由事件檔重建的衍生檢視：移轉之後的操作會重新 render。目前內容等於「依目前事件與 legacy 重新 render 的結果」→ 只是被正常更新過（附錄 A 5-13）。"""
    mk = op.marker()
    if cur is None or mk is None or not AUDIT_VIEW.fullmatch(path): return False
    try: return cur == store.sha256_bytes(op.render_log_bytes(path, [], mk))
    except OperationError: return False

def feasibility(manifest: dict, xplan: dict) -> tuple[list, list, list]:
    """T7 依目前內容：回傳 (R 的步驟候選 [(entry, kind)], R 的 no_change, 無法回復的路徑報告)。
    步驟候選的 planned_post_sha256 是 R 那一步的 expected_before（一般等於移轉後的值；audit.log 檢視可為目前的 render）。"""
    todo, nochange, bad = [], [], []
    for e in manifest["restore"]:
        cur = _sha(e["path"])
        if cur == e["planned_post_sha256"]: todo.append((e, "restore"))
        elif cur == e["pre_sha256"]: nochange.append({"path": e["path"], "kind": "business", "content_sha256": cur})
        elif _current_render(e["path"], cur): todo.append((dict(e, planned_post_sha256=cur), "restore"))
        else: bad.append({"path": e["path"], "category": "restore", "recorded": {"pre": e["pre_sha256"], "post": e["planned_post_sha256"]}, "current": cur})
    for e in manifest["remove"]:
        cur = _sha(e["path"])
        planned = e["planned_post_sha256"] if e["path"] != MARKER else next(s["expected_after"] for s in xplan["steps"] if s["path"] == MARKER)
        if cur is None: nochange.append({"path": e["path"], "kind": "business", "content_sha256": None})
        elif cur == planned: todo.append((dict(e, planned_post_sha256=planned), "remove"))
        elif _current_render(e["path"], cur): todo.append((dict(e, planned_post_sha256=cur), "remove"))
        else: bad.append({"path": e["path"], "category": "remove", "recorded": {"post": planned}, "current": cur})
    for u in manifest["untouched"]:
        cur = _sha(u["path"])
        if cur != u["pre_sha256"]: bad.append({"path": u["path"], "category": "untouched", "recorded": u["pre_sha256"], "current": cur})
    for nc in xplan.get("no_change", []):
        if nc["kind"] not in op.AUDIT_KINDS and _sha(nc["path"]) != nc["content_sha256"]:
            bad.append({"path": nc["path"], "category": "x_no_change", "recorded": nc["content_sha256"], "current": _sha(nc["path"])})
    return todo, nochange, bad

def _report(title: str, items: list[dict]) -> str:
    return title + "\n" + "\n".join(f"- {i.get('path')}［{i.get('category', i.get('reason', ''))}］記錄值 {i.get('recorded')}，目前值 {i.get('current')}" for i in items)

# ---------------------------------------------------------------- rollback：建立計畫（planner）
def plan_rollback(x: str, allow_later: bool):
    def planner(r: str, req: dict, state: str, clock: str):
        regs = op.registrations()
        # T2
        if x not in regs: raise Refused(f"T2：{x} 不存在")
        xplan = op.verify_registration(x, regs[x])
        if xplan["action"] != "migrate": raise Refused(f"T2：{x} 不是 migrate")
        xs = op.plan_state(x)
        if xs not in ("in_progress", "completed"): raise Refused(f"T2：{x} 已終結（{xs}）")
        for o, reg in regs.items():
            if reg["action"] == "migrate_rollback" and (op.load_plan(o) or {}).get("takeover_of") == x:
                raise Refused(f"T2：{x} 已被 rollback 計畫 {o} 接管{'；請續做它' if op.plan_state(o) == 'in_progress' else ''}")
        # T3
        others = [o for o in op.incomplete_plans() if o != x]
        if others: raise Refused(f"T3：存在其他未完成的計畫 {others}；請先續做那些計畫")
        # T4
        mk = op.marker()
        if xs == "completed" and (mk is None or mk.get("migrate_op_id") != x): raise Refused(f"T4：{x} 已完成，但移轉標記不存在或不屬於它")
        if xs == "in_progress" and mk is not None and mk.get("migrate_op_id") != x: raise Refused(f"T4：移轉標記屬於其他 op（{mk.get('migrate_op_id')}）")
        # T5
        xp = x_progress(xplan)
        if xp["conflicts"]: raise EvidenceConflict(_report("T5：證據衝突，不建立 rollback（沒有寫入任何檔案）：", xp["conflicts"]))
        manifest_done = any(s["step_id"] == "manifest" and s["status"] == "done" for s in xp["steps"])
        manifest = planned_manifest(xplan)
        if manifest_done:
            mb = load_manifest(x)
            if mb != manifest: raise EvidenceConflict("T5：移轉清單和計畫不符")
        # T6
        later = later_ops(x, r)
        if later and not allow_later: raise Refused("T6：回復點之後有後續操作，預設拒絕。\n" + _later_report(later, manifest))
        # T7
        todo, nochange, bad = feasibility(manifest, xplan)
        if bad: raise Refused(_report("T7：有無法回復的路徑，不建立 rollback（沒有寫入任何檔案、不標記 X、不刪除移轉標記）：", bad))
        # 建立 R 的步驟
        steps, blobs = [], {}
        def add(path, kind, before, after_bytes, group, sid):
            st = {"seq": len(steps) + 1, "step_id": sid, "path": path, "kind": kind, "group": group, "expected_before": before,
                  "expected_after": store.sha256_bytes(after_bytes) if after_bytes is not None else None, "blob": store.sha256_bytes(after_bytes) if after_bytes is not None else None}
            if after_bytes is not None: blobs[st["blob"]] = after_bytes
            steps.append(st)
        events = []
        def event(action, detail, group):
            ev = {"at": clock, "actor": "system", "action": action, "detail": detail, "op_id": r, "step": len(events) + 1, "run_id": None}
            events.append(ev); add(op._event_path(r, None, ev["step"]), "event", None, store.dump(ev), group, f"event{ev['step']}")
        if xs == "in_progress":
            add(op.status_path(x, "aborted_for_rollback"), "status", None, store.dump({"op_id": x, "status": "aborted_for_rollback", "by": r, "at": clock}), "takeover", "R1")
        not_exec = [s["step_id"] for s in xp["steps"] if s["status"] == "not_executed"]
        event("ROLLBACK_TAKEOVER", f"接管 {x}（{xs}）；done {sum(s['status'] == 'done' for s in xp['steps'])} 步；未執行的 X 步驟：已取消、不補寫：{not_exec}", "takeover")
        marker_entry = None
        for e, kind in todo:
            if e["path"] == MARKER: marker_entry = e; continue
            if kind == "restore":
                bp = e["backup_path"]
                if _sha(bp) != e["backup_sha256"] or e["backup_sha256"] != e["pre_sha256"]:
                    raise EvidenceConflict(f"T5：{e['path']} 的 backup 缺失或 hash 不符（{bp}）")
                add(e["path"], "business", e["planned_post_sha256"], store.read_bytes(bp), "restore", f"restore{len(steps) + 1}")
            else:
                add(e["path"], "business", e["planned_post_sha256"], None, "restore", f"remove{len(steps) + 1}")
        event("ROLLBACK_RESTORE", f"回復 {sum(1 for _, k in todo if k == 'restore')} 個、移除 {sum(1 for e, k in todo if k == 'remove' and e['path'] != MARKER)} 個清單路徑", "restore")
        if marker_entry is not None:
            add(MARKER, "business", marker_entry["planned_post_sha256"], None, "marker", "marker")
        if xs == "completed":
            add(op.status_path(x, "rolled_back"), "status", None, store.dump({"op_id": x, "status": "rolled_back", "by": r, "at": clock}), "terminal", "Rt1")
        done = store.dump({"op_id": r, "status": "completed", "at": clock})
        add(op.status_path(r, "completed"), "status_final", None, done, "terminal", "completed")
        plan = {"plan_schema": 1, "op_id": r, "action": "migrate_rollback", "scope": GLOBAL, "canonical_request": req, "request_hash": r,
                "admitted_state": state, "resume_states": op.resume_states_for("migrate_rollback", state), "clock": clock, "allocated_ids": [],
                "steps": steps, "no_change": nochange, "audit_events": events, "takeover_of": x, "x_status_at_creation": xs,
                "x_progress": xp, "later_ops_snapshot": later, "result": {"takeover_of": x, "steps": len(steps), "no_change": len(nochange)}}
        return plan, blobs
    return planner

def rollback(x: str, by: str, allow_later_ops: bool = False, new_request: bool = False):
    return op.run_operation("migrate_rollback", None, request=lambda: {"params": {"op": x, "allow_later_ops": bool(allow_later_ops), "by": by}},
                            new_request=new_request, planner=plan_rollback(x, allow_later_ops))

# ---------------------------------------------------------------- rollback：執行（群組與檢查 A、B）
def _groups(plan): return {g: [s for s in plan["steps"] if s.get("group") == g] for g in ("takeover", "restore", "marker", "terminal")}

def _check_common(plan: dict, xplan: dict, manifest: dict, label: str):
    bad = []
    for nc in plan["no_change"]:
        if _sha(nc["path"]) != nc["content_sha256"]: bad.append(f"R 的 no_change {nc['path']} 被改動")
    for nc in xplan.get("no_change", []):
        if nc["kind"] not in op.AUDIT_KINDS and _sha(nc["path"]) != nc["content_sha256"]: bad.append(f"X 的 no_change {nc['path']} 被改動")
    for u in manifest["untouched"]:
        if _sha(u["path"]) != u["pre_sha256"]: bad.append(f"untouched {u['path']} 被改動")
    try: op.verify_registration(plan["op_id"])
    except OperationError as e: bad.append(str(e))
    bad += x_evidence_issues(plan, xplan)
    xsteps = {s["seq"]: s for s in xplan["steps"]}
    for s in plan["x_progress"]["steps"]:
        if s["status"] == "not_executed" and s["seq"] in xsteps:
            xs = xsteps[s["seq"]]
            if xs["kind"] == "event" and (store.ROOT / xs["path"]).exists(): bad.append(f"X 未執行的事件 {xs['path']} 出現了")
            if xs["kind"] != "status_final" and (store.ROOT / op.progress_path(xplan, xs)).exists(): bad.append(f"X 未執行步驟的完成紀錄 {op.progress_path(xplan, xs)} 出現了")
    if not (store.ROOT / op.LOCK_PATH).exists(): bad.append("鎖檔不存在")
    if bad: raise EvidenceConflict(f"{label}停止，R 保持 in_progress：\n" + "\n".join(f"- {b}" for b in bad))

def x_evidence_issues(rplan: dict, xplan: dict) -> list[str]:
    """依 R 凍結的 x_progress 核對 X 已證實的證據（§13.5、§13.7）：done 的稽核物等於凍結值；proof=progress 的完成紀錄存在且相符；
    content_tail 的完成紀錄不得被補寫；completed_status 存在且相符。"""
    bad = []; xsteps = {s["seq"]: s for s in xplan["steps"]}
    for row in rplan["x_progress"]["steps"]:
        s = xsteps.get(row["seq"])
        if s is None or row["status"] != "done": continue
        if row["evidence"] and (row["kind"] in op.AUDIT_KINDS or row["kind"] == "status") and _sha(row["evidence"]["path"]) != row["evidence"]["sha256"]:
            bad.append(f"X 的稽核證據 {row['evidence']['path']} 缺失或被改動")
        if s["kind"] == "status_final": continue
        pp = store.ROOT / op.progress_path(xplan, s)
        if row["proof"] == "progress" and (not pp.is_file() or pp.read_bytes() != op.progress_bytes(xplan, s)):
            bad.append(f"X 已證實的完成紀錄 {op.progress_path(xplan, s)} 缺失或被改動")
        if row["proof"] == "content_tail" and pp.exists():
            bad.append(f"X 合法尾端的完成紀錄 {op.progress_path(xplan, s)} 不應存在（R 不替 X 補寫）")
    return bad

def plan_evidence_issues(plan: dict) -> list[str]:
    """已完成的計畫：每一步的輸出等於計畫值（刪除步驟則不存在）、每個非最終步驟的完成紀錄存在且位元組相符、completed 紀錄相符、登錄紀錄相符。"""
    bad = []
    try: op.verify_registration(plan["op_id"])
    except OperationError as e: bad.append(str(e))
    for s in plan["steps"]:
        if _sha(s["path"]) != s["expected_after"]: bad.append(f"{plan['op_id'][:12]}… 的 {s['path']} 不等於計畫值")
        if s["kind"] == "status_final": continue
        pp = store.ROOT / op.progress_path(plan, s)
        if not pp.is_file() or pp.read_bytes() != op.progress_bytes(plan, s): bad.append(f"{plan['op_id'][:12]}… 的完成紀錄 {op.progress_path(plan, s)} 缺失或不符")
    return bad

def _after(plan, s) -> bool:
    return _sha(s["path"]) == s["expected_after"] and (store.ROOT / op.progress_path(plan, s)).exists()

def check_a(plan: dict, xplan: dict, manifest: dict):
    g = _groups(plan); x = plan["takeover_of"]
    for s in g["takeover"] + g["restore"]:
        if not _after(plan, s): raise EvidenceConflict(f"檢查 A 停止：{s['path']} 不是回復後的內容或缺完成紀錄")
    if g["marker"]:
        m = g["marker"][0]; mk = op.marker()
        if _sha(MARKER) != m["expected_before"] or mk is None or mk.get("migrate_op_id") != x or (store.ROOT / op.progress_path(plan, m)).exists():
            raise EvidenceConflict(f"檢查 A 停止：移轉標記不是 R 計畫預期的內容或不屬於 {x}（不刪除）")
    elif store.exists(MARKER): raise EvidenceConflict("檢查 A 停止：移轉標記應不存在")
    for s in g["terminal"]:
        if (store.ROOT / s["path"]).exists(): raise EvidenceConflict(f"檢查 A 停止：終態紀錄 {s['path']} 已存在")
    _check_common(plan, xplan, manifest, "檢查 A ")

def check_b(plan: dict, xplan: dict, manifest: dict):
    g = _groups(plan)
    for s in g["takeover"] + g["restore"] + g["marker"]:
        if not _after(plan, s): raise EvidenceConflict(f"檢查 B 停止：{s['path']} 不是預期的內容或缺完成紀錄")
    if not g["marker"] and store.exists(MARKER): raise EvidenceConflict("檢查 B 停止：移轉標記應不存在")
    seen_missing = False
    for s in g["terminal"]:
        present = (store.ROOT / s["path"]).exists()
        if present and seen_missing: raise EvidenceConflict(f"檢查 B 停止：終態紀錄不符合前綴規則（{s['path']}）")
        if present and _sha(s["path"]) != s["expected_after"]: raise EvidenceConflict(f"檢查 B 停止：終態紀錄 {s['path']} 內容不符")
        seen_missing = seen_missing or not present
    _check_common(plan, xplan, manifest, "檢查 B ")

def execute_rollback(plan: dict):
    op._clean_tmp(plan)
    final = plan["steps"][-1]
    if (store.ROOT / final["path"]).is_file():
        if _sha(final["path"]) != final["expected_after"]: raise EvidenceConflict(f"{final['path']} 內容不符")
        return
    xplan = op.load_plan(plan["takeover_of"]); manifest = planned_manifest(xplan)
    cls = op.classify_steps(plan)
    if cls.conflicts or cls.external:
        raise EvidenceConflict(f"續做 {plan['op_id']} 停止（V5），沒有重寫任何檔案：\n" + "\n".join(f"- {c.get('path')}：{c['reason']}" for c in cls.conflicts + cls.external))
    g = _groups(plan)
    def run_step(s):
        st = cls.status[s["seq"]]
        if st == "done": return
        if st == "not_executed": op._write_step(plan, s)
        op._link_create(op.progress_path(plan, s), op.progress_bytes(plan, s), tag=plan["op_id"][:16])
        op.fault(f"after_progress:{s['seq']}")
    for s in g["takeover"] + g["restore"]: run_step(s)
    terminal_started = any(cls.status.get(s["seq"]) in ("done", "tail") for s in g["terminal"] if s is not final)
    if g["marker"]:
        m = g["marker"][0]
        if cls.status[m["seq"]] == "not_executed":
            op.fault("before_check_a"); check_a(plan, xplan, manifest); op.fault("after_check_a")
        run_step(m)
    elif not terminal_started:
        op.fault("before_check_a"); check_a(plan, xplan, manifest); op.fault("after_check_a")
    op.fault("before_check_b"); check_b(plan, xplan, manifest); op.fault("after_check_b")
    for s in g["terminal"]:
        if s is final: continue
        run_step(s)
    op.fault("before_completed")
    op._write_step(plan, final)

# ---------------------------------------------------------------- migrate verify（唯讀）
def verify(rolled_back: bool = False) -> list[str]:
    """唯讀（第 5 章 §12）。移轉後：X 的計畫逐步核對（含清單、backup、事件、完成紀錄、completed、登錄）與清單各類；
    回復後：R 的計畫逐步核對、X 依凍結的 x_progress 核對、清單各類回到移轉前、X 恰好一個終態。"""
    issues = []
    if not rolled_back:
        mk = op.marker()
        if mk is None: return ["移轉標記不存在"]
        x = mk["migrate_op_id"]; xplan = op.load_plan(x)
        if xplan is None: return [f"移轉標記指向的 {x} 沒有計畫"]
        if op.plan_state(x) != "completed": issues.append(f"{x} 不是 completed（{op.plan_state(x)}）")
        issues += plan_evidence_issues(xplan)
        manifest = planned_manifest(xplan)
        if mk.get("manifest_sha256") != xplan.get("manifest_sha256") or _sha(manifest_path(x)) != xplan.get("manifest_sha256"): issues.append("移轉清單檔或標記中的 manifest_sha256 和計畫不符")
        for e in manifest["restore"]:
            if _sha(e["path"]) != e["planned_post_sha256"]: issues.append(f"restore {e['path']} 不等於移轉後的值")
            if _sha(e["backup_path"]) != e["backup_sha256"]: issues.append(f"backup {e['backup_path']} 缺失或不符")
    else:
        regs = op.registrations()
        rs = [o for o, reg in sorted(regs.items(), key=lambda kv: kv[1]["plan_seq"]) if reg["action"] == "migrate_rollback"]
        if not rs: return ["沒有 rollback 計畫"]
        r = rs[-1]; plan = op.load_plan(r); x = plan["takeover_of"]; xplan = op.load_plan(x); manifest = planned_manifest(xplan)
        if op.plan_state(r) != "completed": issues.append(f"rollback {r} 不是 completed（{op.plan_state(r)}）")
        issues += plan_evidence_issues(plan)
        for e in manifest["restore"]:
            if _sha(e["path"]) != e["pre_sha256"]: issues.append(f"restore {e['path']} 不等於移轉前的值")
        for e in manifest["remove"]:
            if _sha(e["path"]) is not None: issues.append(f"remove {e['path']} 仍存在")
        issues += [f"證據衝突：{b}" for b in x_evidence_issues(plan, xplan)]
        xsteps = {s["seq"]: s for s in xplan["steps"]}
        for s in plan["x_progress"]["steps"]:
            xs = xsteps.get(s["seq"])
            if s["status"] == "not_executed" and xs is not None:
                if xs["kind"] == "event" and (store.ROOT / xs["path"]).exists(): issues.append(f"證據衝突：X 未執行的事件 {xs['path']} 出現了")
                if xs["kind"] == "status_final" and (store.ROOT / xs["path"]).exists(): issues.append(f"證據衝突：X 未完成卻有 {xs['path']}")
                if xs["kind"] != "status_final" and (store.ROOT / op.progress_path(xplan, xs)).exists(): issues.append(f"證據衝突：X 未執行步驟的完成紀錄 {op.progress_path(xplan, xs)} 出現了")
        terms = [t for t in ("rolled_back", "aborted_for_rollback") if (store.ROOT / op.status_path(x, t)).exists()]
        if len(terms) != 1: issues.append(f"X 的終態紀錄應恰好一個（目前 {terms}）")
        if op.marker() is not None: issues.append("移轉標記仍存在")
        if op.incomplete_plans(): issues.append(f"仍有未完成的計畫 {op.incomplete_plans()}")
    for u in manifest.get("untouched", []):
        if _sha(u["path"]) != u["pre_sha256"]: issues.append(f"untouched {u['path']} 被改動")
    if not (store.ROOT / op.LOCK_PATH).exists(): issues.append("鎖檔不存在")
    return issues
