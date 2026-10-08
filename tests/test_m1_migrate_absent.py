"""移轉時「原本不存在」的檔案與 regression-generation run（需求 A 第 5 章 §11～§13、附錄 A 5-x；AC-09-24、66、67）。

資料來源：
- legacy 資料由需求 A 之前的程式碼（base 2e01d4b，tests/p3_legacy.py 以 git archive 匯出）以它自己的正式流程產生（舊程式碼 2e01d4b 在 root 上執行時，root 的定義層——schemas／agents／workflows／permissions——是新程式的版本，沿用 p3_legacy 的作法；2e01d4b 到目前的定義層差異對這些流程只有說明文字、version 字串與新增欄位，task graph、risk_review 與 applies_to_areas 都沒有變。cross_version 測試的舊 CIR 需要舊 schema，所以那裡改用舊定義層）：
  沿用 p3_legacy.OLD_FLOW（完成的 spec-to-testcase run、RUNNING 的 spec-to-testcase run、已回答／未回答的 CLR、4 個 ACTIVE TC），
  再接上本檔的 REG_EXTRA：在**舊程式**中以 `engine.new_run("regression-generation", ...)` 建立一個 RUNNING 的 regression-generation run（T1 待提交）。
- 舊程式本身不會產生「沒有 audit.log 的 run」與「沒有 .md render 的 CLR」：AC-09-66、67 的 fixture 在 legacy root（S_pre、移轉之前）
  以檔案操作移除該檔，模擬原本就沒有 render 的資料（各測試的 docstring 另行標明）。
- 新程式的動作一律走正式 CLI（maintenance start、migrate --acknowledge-idle、migrate verify、migrate rollback --op X、migrate verify --rolled-back、
  maintenance end）與正式 API（engine.submit／evaluate_gate／approve）。"""
import hashlib, json, os, pathlib, shutil, subprocess, sys, tempfile
from tests import p1_util as U, p3_legacy as L

MARKER = "artifacts/requirements/_migration.yaml"

REG_EXTRA = r'''
REG = engine.new_run("regression-generation", {"target_suites": ["full_regression"], "scope": "all", "trigger": "manual"}, BY)["run_id"]
'''

_TPL = {}

def legacy_with_reg():
    """S_pre 的 root：p3_legacy.OLD_FLOW ＋ 舊程式建立的 RUNNING regression-generation run。範本只產生一次，每次回傳一份複本。"""
    if not _TPL:
        root = U.mkroot(migrated=False); old = L.old_checkout()
        code = L.OLD_FLOW.replace('print(json.dumps({"done"', REG_EXTRA + '\nprint(json.dumps({"reg": REG, "done"')
        env = {**os.environ, "QAOS_ROOT": str(root), "PYTHONDONTWRITEBYTECODE": "1"}
        r = subprocess.run([sys.executable, "-c", code], cwd=old, env=env, capture_output=True, text=True, timeout=300)
        if r.returncode != 0: raise AssertionError(f"舊程式的 legacy 流程失敗：\n{r.stdout}\n{r.stderr}")
        _TPL.update(root=root, info=json.loads(r.stdout.strip().splitlines()[-1]))
    dst = pathlib.Path(tempfile.mkdtemp(prefix="qaos-m1-absent-")) / "root"
    shutil.copytree(_TPL["root"], dst)
    return dst, dict(_TPL["info"])

def P(root, rel=""): return pathlib.Path(root) / rel
def ok(r): assert r.returncode == 0, r.stdout + r.stderr; return r
def x_of(root): return U.load(root, MARKER)["migrate_op_id"]
def manifest(root): return U.load(root, f"operations/_global/{x_of(root)}/manifest.yaml")
def running_ack(info): return ["--acknowledge-idle", info["running"], "--acknowledge-idle", info["reg"]]

def migrate_ack(root, info):
    """正式流程：maintenance start → migrate（兩個 RUNNING 的 run 都 acknowledge-idle）→ migrate verify。"""
    L.migrate(root, *running_ack(info), check=True)
    ok(U.q(root, "migrate", "verify"))

def rollback(root):
    x = x_of(root)
    ok(U.q(root, "migrate", "rollback", "--op", x, "--by", "m"))
    ok(U.q(root, "migrate", "verify", "--rolled-back"))
    return x

# ======================================================================== AC-09-66
def test_ac_09_66_run_without_audit_log_is_remove_and_absent():
    """AC-09-66：某個 run 原本沒有 audit.log → 移轉（render 新建）→ rollback。
    預期：該 audit.log 屬於清單的 remove（不在 restore），標記中 legacy 狀態記為 absent；移轉後存在、回復後不存在；
    其他 run 與全域 log 仍是 frozen／restore，回復後位元組等於移轉前。

    fixture 建構：legacy root 由舊程式正式流程產生後，在 S_pre（移轉前）以檔案操作移除完成 run 的 runs/<done>/audit.log，
    模擬原本就沒有 render 的資料。"""
    root, info = legacy_with_reg(); lg = f"runs/{info['done']}/audit.log"
    P(root, lg).unlink()                                                              # fixture 建構：以檔案操作移除（見 docstring）
    others = {p.relative_to(root).as_posix(): p.read_bytes() for p in [*P(root).glob("runs/*/audit.log"), P(root, "runs/_audit.log")] if p.is_file()}
    assert lg not in others and f"runs/{info['running']}/audit.log" in others and "runs/_audit.log" in others
    before = U.snapshot(root)

    migrate_ack(root, info)
    assert P(root, lg).is_file()                                                      # render 新建
    assert not P(root, lg.replace("audit.log", "audit.legacy.log")).exists()           # 沒有 legacy 可凍結
    mk = U.load(root, MARKER); m = manifest(root)
    assert mk["logs"][lg] == {"legacy": "absent"}
    remove = {e["path"]: e for e in m["remove"]}; restore = {e["path"]: e for e in m["restore"]}
    assert lg in remove and lg not in restore and remove[lg]["category"] == "run"
    assert remove[lg]["planned_post_sha256"] == U.sha(P(root, lg))
    nochange = {n["path"] for n in U.plan_of(root, x_of(root))["no_change"]}
    for o, b in others.items():                                                        # 其他 log 照常：frozen；有變更（render 追加事件）者為 restore，render 結果等於原位元組者為計畫的 no_change
        assert mk["logs"][o] == {"legacy": "frozen", "sha256": hashlib.sha256(b).hexdigest()}
        assert o not in remove
        if o in restore: assert restore[o]["pre_sha256"] == hashlib.sha256(b).hexdigest() and P(root, o).read_bytes().startswith(b)
        else: assert o in nochange and P(root, o).read_bytes() == b
        assert P(root, o.replace("audit.log", "audit.legacy.log")).read_bytes() == b
    assert "runs/_audit.log" in restore                                                # 全域 log 有 MIGRATE 事件：必為 restore

    rollback(root)
    assert not P(root, lg).exists()                                                    # remove → 回復後不存在
    for o, b in others.items(): assert P(root, o).read_bytes() == b                    # restore → 回到移轉前
    d = U.diff(before, U.snapshot(root))
    assert d["changed"] == [] and d["removed"] == [] and lg not in d["added"], d
    assert not P(root, MARKER).exists()

# ======================================================================== AC-09-67
def test_ac_09_67_clr_without_md_render_is_remove():
    """AC-09-67：CLR 原本沒有 .md render → 移轉時產生（CLR rev 0 寫入時一併 render）→ rollback。
    預期：該 .md 屬於清單的 remove（不在 restore）；移轉後存在、回復後不存在；CLR 的 yaml 本身是 restore，回復後位元組等於移轉前。

    fixture 建構：legacy root 由舊程式正式流程產生後，在 S_pre（移轉前）以檔案操作移除已回答 CLR 的
    clarifications/demo/AUTH/<CLR>.md，模擬原本就沒有 render 的資料。"""
    root, info = legacy_with_reg()
    md = f"clarifications/demo/AUTH/{info['clr']}.md"; cy = f"clarifications/demo/AUTH/{info['clr']}.yaml"
    assert P(root, md).is_file(); P(root, md).unlink()                                 # fixture 建構：以檔案操作移除（見 docstring）
    cy_pre = P(root, cy).read_bytes(); before = U.snapshot(root)

    migrate_ack(root, info)
    assert P(root, md).is_file()                                                       # 移轉時產生
    m = manifest(root)
    remove = {e["path"]: e for e in m["remove"]}; restore = {e["path"]: e for e in m["restore"]}
    assert md in remove and md not in restore and remove[md]["category"] == "clarification"
    assert remove[md]["planned_post_sha256"] == U.sha(P(root, md))
    assert cy in restore and restore[cy]["pre_sha256"] == hashlib.sha256(cy_pre).hexdigest()

    rollback(root)
    assert not P(root, md).exists()                                                    # remove → 回復後不存在
    assert P(root, cy).read_bytes() == cy_pre
    d = U.diff(before, U.snapshot(root))
    assert d["changed"] == [] and d["removed"] == [] and md not in d["added"], d

# ======================================================================== AC-09-24
ADVANCE = r'''
import json, sys
from tools.qaos import engine, store
from tests import helpers as H
RID = sys.argv[1]
active = []
for p in sorted((store.ROOT / "testcases" / "registry").glob("TC-*.yaml")):
    d = store.load(p)
    if d["status"] == "ACTIVE": active.append(d["testcase_id"])
prop = {"suite_id": "SUITE-FULL", "suite_type": "full_regression", "base_suite_version": None, "trigger": "manual",
        "proposed_memberships": [{"testcase_id": t, "pinned_version": "active", "justification": "high risk", "risk_tag": "auth"} for t in active],
        "diff": {"add": [{"testcase_id": t, "reason": "new"} for t in active], "remove": [], "repin": []},
        "selection_criteria": "all active", "summary": {"total": len(active), "added": len(active), "removed": 0, "repinned": 0}}
def proj():
    run = engine.load_run(RID)
    return {"status": run["status"], "current_task_id": run.get("current_task_id"), "tasks": [[t["task_id"], t["status"]] for t in run["tasks"]],
            "rm_pin_keys": sorted(k for k in run if "requirement_model_revision" in k)}
out = {"active": active, "before": proj()}
_, p = H.write_artifact(RID, "T1", "agent-regression-curator", "RegressionProposal", prop, [{"entity_type": "TestCase", "id": t} for t in active], {"type": "Registry", "ids": []}, "regression")
okk, issues = engine.submit(RID, "T1", str(p)); out["submit"] = [okk, issues]; out["after_submit"] = proj()
g = engine.evaluate_gate(RID, "T1"); out["gate"] = {"result": g["result"], "issues": g.get("issues") or []}; out["after_gate"] = proj()
apr_id = engine.load_run(RID)["waiting_on_approval_id"]
apr = store.load(store.ROOT / "approvals" / f"{apr_id}.yaml")
out["approval"] = {"type": apr.get("type"), "status": apr.get("status")}
engine.approve(apr_id, "approve", "oscar@example.com")
apr = store.load(store.ROOT / "approvals" / f"{apr_id}.yaml"); out["approval_after"] = apr.get("status")
out["after_approve"] = proj()
s = store.load("testsuites/full-regression/SUITE-FULL.yaml")
out["suite"] = {"status": s["status"], "version": s["version"], "members": sorted([m["testcase_id"], str(m["pinned_version"])] for m in s["memberships"]),
                "added_by_this_apr": all(m["added_by_approval"] == apr_id for m in s["memberships"])}
print(json.dumps(out, ensure_ascii=False))
'''

def advance_old(root, rid) -> dict:
    """以舊程式（2e01d4b）的正式 API 推進 regression-generation run。"""
    env = {**os.environ, "QAOS_ROOT": str(root), "PYTHONDONTWRITEBYTECODE": "1"}
    r = subprocess.run([sys.executable, "-c", ADVANCE, rid], cwd=L.old_checkout(), env=env, capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, f"舊程式推進失敗：\n{r.stdout}\n{r.stderr}"
    return json.loads(r.stdout.strip().splitlines()[-1])

def advance_new(root, rid) -> dict:
    """以新程式的正式 API 推進 regression-generation run。"""
    r = subprocess.run([sys.executable, "-c", ADVANCE, rid], cwd=U.REPO, env=U.env_for(root), capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, f"新程式推進失敗：\n{r.stdout}\n{r.stderr}"
    return json.loads(r.stdout.strip().splitlines()[-1])

def test_ac_09_24_legacy_regression_generation_run_unchanged():
    """AC-09-24：移轉前就存在的 regression-generation run（舊程式正式流程建立，RUNNING、T1 待提交）。
    預期：不產生 sidecar（artifacts/requirements/_bindings/<run>.yaml 不存在、不在清單 remove）；run.yaml 列在清單 untouched 且 sha 不變；
    移轉前後行為不變。

    「行為不變」的比較範圍：同一份 legacy root 複製兩份——
      A：不移轉，以舊程式碼（2e01d4b；root 的定義層同上，是新程式的版本）的正式 API 推進；
      B：以新程式 maintenance start → migrate --acknowledge-idle（兩個 RUNNING run）→ verify → maintenance end 後，以新程式的正式 API 推進；
    兩邊執行相同步驟：T1 regression curator 提交 RegressionProposal（full_regression、全部 ACTIVE TC）→ engine.submit → evaluate_gate（G-REG）
    → 取 run 的 waiting_on_approval_id → approve。比較每一步後的 run 狀態、current_task_id、各 task 狀態、submit 結果、G-REG 結果與 issues、
    approval 類型與決定前後狀態、套件結果（status、version、membership 的 testcase_id／pinned_version）。另驗兩邊的 run 都沒有任何
    requirement_model_revision 類欄位（不綁 revision）。不比較 artifact／approval id、時間戳、派發包等新程式新增的記錄欄位。
    fixture 建構：全部由舊程式正式流程產生，沒有任何檔案操作。"""
    root_b, info = legacy_with_reg(); rid = info["reg"]
    root_a = pathlib.Path(tempfile.mkdtemp(prefix="qaos-m1-absent-old-")) / "root"; shutil.copytree(root_b, root_a)
    run_rel = f"runs/{rid}/run.yaml"; sc_rel = f"artifacts/requirements/_bindings/{rid}.yaml"
    pre = U.load(root_b, run_rel); assert pre["workflow_id"] == "regression-generation" and pre["status"] == "RUNNING"
    run_sha = U.sha(P(root_b, run_rel))

    # B：新程式移轉
    migrate_ack(root_b, info)
    assert not P(root_b, sc_rel).exists()
    m = manifest(root_b)
    assert sc_rel not in {e["path"] for e in m["remove"] + m["restore"]}
    assert {"path": run_rel, "pre_sha256": run_sha} in m["untouched"]
    assert run_rel not in {e["path"] for e in m["remove"] + m["restore"]}
    assert U.sha(P(root_b, run_rel)) == run_sha
    mk = U.load(root_b, MARKER); assert rid in mk["runs"] and mk["mode_per_run"][rid] == "acknowledge_idle"
    assert U.load(root_b, f"artifacts/requirements/_bindings/{info['done']}.yaml")["requirement_model_revision"]["revision"] == "R000"   # 對照：spec-to-testcase 有 sidecar
    ok(U.q(root_b, "maintenance", "end", "--by", "m"))
    assert U.sha(P(root_b, run_rel)) == run_sha

    # 行為比較
    a = advance_old(root_a, rid); b = advance_new(root_b, rid)
    assert a == b, f"舊程式（不移轉）：{json.dumps(a, ensure_ascii=False)}\n新程式（移轉後）：{json.dumps(b, ensure_ascii=False)}"
    # 結果符合 workflow 定義（regression-generation：T1 → G-REG → UPDATE_SUITE_MEMBERSHIP → suite ACTIVE → COMPLETED）
    assert b["submit"] == [True, []] and b["gate"] == {"result": "PASS", "issues": []}
    assert b["approval"] == {"type": "UPDATE_SUITE_MEMBERSHIP", "status": "PENDING"} and b["after_gate"]["status"] == "WAITING_HUMAN"
    assert b["after_approve"]["status"] == "COMPLETED" and b["suite"]["status"] == "ACTIVE" and b["suite"]["version"] == 1
    assert len(b["active"]) >= 1 and len(b["suite"]["members"]) == len(b["active"]) and b["suite"]["added_by_this_apr"]
    assert all(s["rm_pin_keys"] == [] for s in (b["before"], b["after_submit"], b["after_gate"], b["after_approve"]))
    assert not P(root_b, sc_rel).exists()                                              # 推進後仍沒有 sidecar
    # 明確例外（函式層）：上面的 run 的 input 沒有 spec_id，通用分支本來就不產生 sidecar；這裡以帶 spec_id／spec_version 的 run 呼叫
    # migrate._run_sidecar，確認 regression-generation 的明確例外仍回傳 None（對照：同樣 input 的 spec-to-testcase 會產生 sidecar）
    r = U.py(root_b, "import json\nfrom tools.qaos import migrate as M\n"
             "inp = {'spec_id': 'SPEC-AUTH-001', 'spec_version': '1.0'}\n"
             "print(json.dumps([M._run_sidecar({'run_id': 'RUN-X', 'workflow_id': w, 'input': inp}, 'x') is None for w in ('regression-generation', 'spec-to-testcase')]))")
    assert json.loads(r.stdout.strip().splitlines()[-1]) == [True, False]
