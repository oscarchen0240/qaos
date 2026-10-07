#!/usr/bin/env python3
"""P6 AC-A-B1-4「舊資料唯讀複本移轉」的可重複預演腳本（不是 pytest 測試；檔名不以 test_ 開頭，不會被自動收集）。

用法（從程式目錄執行；程式目錄 = 本檔所在 repo 的根目錄）：
    python3 tests/p6_rehearsal.py --src <唯讀資料來源目錄> --work <工作目錄（不存在或空）> \
        --mode acknowledge-idle|cancel-run|pre-cancel [--real-data-checks ack|cancel] --report <報告.json>

- 來源目錄只讀取（複製到工作目錄）；所有 QAOS 指令以 QAOS_ROOT=<工作目錄> 執行，程式取自本檔所在的 repo。
- 依序：（pre-cancel：S_pre 先 run cancel）→ maintenance start →（AC-09-46：不指定處理方式 → 拒絕、沒有寫入）→ migrate → migrate verify
  → AC-A-B1-4 逐項斷言 → migrate rollback → migrate verify --rolled-back → 相同請求重送被拒（AC-09-63①）→ migrate --new-request
  → migrate verify → 重新移轉的 AC-A-B1-4 重點斷言 → maintenance end →（--real-data-checks：S_post 上的真實資料驗收）。
- 結果寫成 JSON 報告；任何斷言失敗不會中止後續步驟（報告中逐項列出），最後以非零結束碼表示有失敗。
- 不做 M1 的故障演練（FP-M2、FP-M3、FP-R0、FP-W、FP-P1）。"""
import argparse, datetime, hashlib, json, os, pathlib, shutil, stat, subprocess, sys, time
import yaml

CODE = pathlib.Path(__file__).resolve().parents[1]
BY = "p6-rehearsal@example.com"
RUN_IDLE = "RUN-20260914-001"          # RUNNING（manual-test-to-regression，DAILYREPORT 0.1）
RUN_WAIT = "RUN-20261002-001"          # WAITING_HUMAN（spec-change-impact SITELIST 0.4→0.6，APR-0192 PENDING）
EXPECT_TC = {"SPEC-DAILYREPORT-001": 96, "SPEC-PLATFORMRULE-001": 44, "SPEC-SITELIST-001": 57}
DEF_LAYER = ("schemas", "agents", "workflows", "permissions", "tools", "tests", "admin-ui", "docs", "bin")

# ---------------------------------------------------------------- 共用
def sha_file(p: pathlib.Path) -> str: return hashlib.sha256(p.read_bytes()).hexdigest()

def snapshot(root: pathlib.Path) -> dict:
    out = {}
    for p in root.rglob("*"):
        if p.is_file() and not p.is_symlink(): out[p.relative_to(root).as_posix()] = sha_file(p)
    return out

def diff(before: dict, after: dict) -> dict:
    return {"added": sorted(set(after) - set(before)), "removed": sorted(set(before) - set(after)),
            "changed": sorted(k for k in set(before) & set(after) if before[k] != after[k])}

def load(root, rel):
    return yaml.safe_load((pathlib.Path(root) / rel).read_text(encoding="utf-8"))

class Report:
    def __init__(self, args):
        self.data = {"mode": args.mode, "src": str(args.src), "work": str(args.work), "code": str(CODE), "started_at": now(), "steps": [], "checks": [], "facts": {}}
        self.failed = 0
    def step(self, name, r: subprocess.CompletedProcess, dur: float, expect_rc=0):
        ok = (r.returncode == expect_rc) if expect_rc is not None else True
        self.data["steps"].append({"step": name, "cmd": " ".join(map(str, r.args[3:] if r.args[:3] == [sys.executable, "-m", "tools.qaos"] else ["python", "-c", "…"])),
                                   "rc": r.returncode, "expected_rc": expect_rc, "ok": ok, "seconds": round(dur, 2),
                                   "stdout_tail": r.stdout[-1500:], "stderr_tail": r.stderr[-1500:]})
        if not ok: self.failed += 1
        return ok
    def check(self, ac, name, ok, detail=None):
        self.data["checks"].append({"ac": ac, "check": name, "result": "PASS" if ok else "FAIL", "detail": detail})
        if not ok: self.failed += 1
        return ok
    def fact(self, k, v): self.data["facts"][k] = v

def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")

def env_for(work):
    env = dict(os.environ, QAOS_ROOT=str(work), PYTHONPATH=str(CODE), PYTHONDONTWRITEBYTECODE="1")
    for k in ("QAOS_FAULT", "QAOS_PAUSE"): env.pop(k, None)
    return env

def q(rep, work, name, *args, expect_rc=0):
    t = time.time()
    r = subprocess.run([sys.executable, "-m", "tools.qaos", *map(str, args)], cwd=CODE, env=env_for(work), capture_output=True, text=True, timeout=1800)
    rep.step(name, r, time.time() - t, expect_rc); return r

def py(work, code: str, timeout=1800):
    """在子程序（QAOS_ROOT=work）執行程式片段；最後一行輸出 JSON。只做唯讀的函式層查詢，或標明的正式 API 呼叫。"""
    r = subprocess.run([sys.executable, "-c", code], cwd=CODE, env=env_for(work), capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0: raise RuntimeError(f"python 片段失敗（{r.returncode}）：\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}")
    return json.loads(r.stdout.strip().splitlines()[-1])

# ---------------------------------------------------------------- 唯讀盤點
def inventory(root: pathlib.Path) -> dict:
    runs = {p.parent.name: load(root, p.relative_to(root)) for p in sorted(root.glob("runs/*/run.yaml"))}
    aprs = [load(root, p.relative_to(root)) for p in sorted(root.glob("approvals/APR-*.yaml"))]
    clrs = [load(root, p.relative_to(root)) for p in sorted(root.glob("clarifications/*/*/CLR-*.yaml"))]
    tcs = {}
    for p in root.glob("testcases/versions/*/v*.yaml"):
        v = load(root, p.relative_to(root))
        if v.get("status") in ("ACTIVE", "PENDING_APPROVAL"): tcs.setdefault(v["spec_id"], {}).setdefault(str(v["spec_version"]), 0); tcs[v["spec_id"]][str(v["spec_version"])] += 1
    st = {}
    for d in runs.values(): st[d["status"]] = st.get(d["status"], 0) + 1
    return {"runs_by_status": st, "running": sorted(r for r, d in runs.items() if d["status"] == "RUNNING"),
            "waiting_human": sorted(r for r, d in runs.items() if d["status"] == "WAITING_HUMAN"),
            "pending_apr": sorted((a["approval_id"], a["run_id"]) for a in aprs if a.get("status") == "PENDING"),
            "tc_active_or_pending_by_spec_version": tcs, "tc_total": sum(n for s in tcs.values() for n in s.values()),
            "clr_by_status": {s: sum(1 for c in clrs if c.get("status") == s) for s in sorted({c.get("status") for c in clrs})},
            "clr_with_answer": sum(1 for c in clrs if c.get("answer")), "clr_with_answer_revisions": sum(1 for c in clrs if c.get("answer_revisions")),
            "workflows": {w: sum(1 for d in runs.values() if d["workflow_id"] == w) for w in sorted({d["workflow_id"] for d in runs.values()})},
            "runs_without_audit_log": sorted(r for r in runs if not (root / f"runs/{r}/audit.log").exists()),
            "global_audit_log": (root / "runs/_audit.log").exists(),
            "clr_without_md": sorted(c["clarification_id"] for c in clrs if not any(root.glob(f"clarifications/*/*/{c['clarification_id']}.md"))),
            "requirement_models": sorted(f"{p.parent.parent.name}@{p.parent.name[1:]}" for p in root.glob("artifacts/requirements/*/*/requirements.yaml"))}

# ---------------------------------------------------------------- schema 驗證（函式層，唯讀）
SCHEMA_CODE = r"""
import json, re
from tools.qaos import schema, store
root = store.ROOT; DEF = %r
def pick(rel):
    n = rel.rsplit("/", 1)[-1]
    if rel.startswith("locks/") or "/audit.d/" in rel or rel.startswith("runs/_audit.d/"): return None
    if rel.startswith("operations/"):
        return "workflow/operation-plan.schema.json" if re.fullmatch(r"operations/[^/]+/[0-9a-f]{64}\.yaml", rel) else None
    if rel == "artifacts/requirements/_migration.yaml": return None
    if rel.startswith(("artifacts/requirements/_bindings/", "testcases/_bindings/")): return "spec/binding.schema.json"
    if "/revisions/" in rel:
        if n == "R000.yaml": return "spec/requirements-file.schema.json"
        if re.fullmatch(r"R\d{3}\.yaml", n): return "spec/requirements-revision.schema.json"
        return None
    if rel.startswith("runs/"):
        if n == "run.yaml": return "workflow/workflow-run.schema.json"
        if "/dispatch/" in rel: return "workflow/dispatch-packet.schema.json"
        return None
    if rel.startswith("clarifications/"): return "spec/clarification.schema.json" if re.fullmatch(r"CLR-.*\.yaml", n) else None
    return schema.infer(rel)
out = {"checked": 0, "by_schema": {}, "failures": [], "no_schema": 0}
for p in sorted(root.rglob("*.yaml")):
    rel = p.relative_to(root).as_posix()
    if rel.split("/")[0] in DEF or p.name.startswith(".qaos-tmp"): continue
    s = pick(rel)
    if s is None: out["no_schema"] += 1; continue
    obj = store.load(p); errs = schema.errors(obj, s)
    out["checked"] += 1; out["by_schema"][s] = out["by_schema"].get(s, 0) + 1
    if errs: out["failures"].append({"path": rel, "schema": s, "errors": errs[:3]})
print(json.dumps(out, ensure_ascii=False))
"""

def schema_check(work):
    return py(work, SCHEMA_CODE % (DEF_LAYER,))

# ---------------------------------------------------------------- _skip（函式層，唯讀）
SKIP_CODE = r"""
import json
from tools.qaos import engine, store
wf = engine.workflow("spec-to-testcase"); t1 = next(t for t in wf["tasks"] if t["id"] == "T1")
out = {}
for p in sorted(store.glob("artifacts/requirements/*/*/requirements.yaml")):
    sid, ver = p.parent.parent.name, p.parent.name[1:]
    skip, warn = engine._skip_decision(wf, t1, {"spec_id": sid, "spec_version": ver})
    out[f"{sid}@{ver}"] = {"skip": skip, "warning": warn}
print(json.dumps(out, ensure_ascii=False))
"""

# ---------------------------------------------------------------- AC-A-B1-4 斷言
def assert_migrated(rep, src: pathlib.Path, work: pathlib.Path, src_snap: dict, mode: str, label: str, full=True, pre_audit: dict | None = None, base_failures=None):
    ac = "AC-A-B1-4"; mk = load(work, "artifacts/requirements/_migration.yaml"); x = mk["migrate_op_id"]
    rep.fact(f"{label}.migrate_op_id", x)
    manifest = load(work, f"operations/_global/{x}/manifest.yaml")
    restore = {e["path"]: e for e in manifest["restore"]}; remove = {e["path"]: e for e in manifest["remove"]}; untouched = {e["path"]: e for e in manifest["untouched"]}
    rep.fact(f"{label}.manifest_counts", {k: len(manifest[k]) for k in ("restore", "remove", "retain_audit", "planned_audit", "shared_control", "untouched")})
    rep.fact(f"{label}.marker", {"mode_per_run": mk.get("mode_per_run"), "exceptions": mk.get("exceptions"), "runs": len(mk.get("runs") or []),
                                 "logs_frozen": sum(1 for v in mk["logs"].values() if v.get("legacy") == "frozen"), "logs_absent": sorted(k for k, v in mk["logs"].items() if v.get("legacy") == "absent")})
    # 1. schema
    if full:
        sc = schema_check(work); rep.fact(f"{label}.schema", {k: sc[k] for k in ("checked", "by_schema", "no_schema")})
        dd = diff(src_snap, snapshot(work)); touched = set(dd["added"]) | set(dd["changed"])
        new_bad = [f for f in sc["failures"] if f["path"] in touched and not f["path"].endswith("/revisions/R000.yaml")]
        r000_bad = [f for f in sc["failures"] if f["path"].endswith("/revisions/R000.yaml")]
        pre = {f["path"] for f in (base_failures or [])}
        rep.check(ac, f"[{label}] 移轉新增或修改的檔案 schema 全部 PASS（R000 是原檔逐位元複本，另列）", not new_bad, new_bad[:20])
        rep.check(ac, f"[{label}] R000 的 schema 結果與原 requirements.yaml 相同（逐位元複本，不新增失敗）",
                  all(f["path"].replace("/revisions/R000.yaml", "/requirements.yaml") in pre for f in r000_bad), [f["path"] for f in r000_bad])
        rep.check(ac, f"[{label}] 全部業務資料 schema PASS（嚴格；{sc['checked']} 檔）", not sc["failures"],
                  [{"path": f["path"], "pre_existing": f["path"] in pre or f["path"].replace("/revisions/R000.yaml", "/requirements.yaml") in pre, "error": f["errors"][0][:160]} for f in sc["failures"]])
    # 2. R000 = 原 requirements.yaml；檢視不變；meta
    bad = []; rms = sorted(p.relative_to(work).as_posix() for p in work.glob("artifacts/requirements/*/*/requirements.yaml"))
    for view in rms:
        d = view.rsplit("/", 1)[0]
        if src_snap.get(view) is None: continue
        if sha_file(work / view) != src_snap[view]: bad.append(f"{view} 被修改")
        r0 = work / d / "revisions/R000.yaml"
        if not r0.exists() or sha_file(r0) != src_snap[view]: bad.append(f"{d}/revisions/R000.yaml 不等於原檔")
        meta = load(work, f"{d}/revisions/R000.meta.yaml")
        if not (meta["target_decl_rev"] == 0 and meta["reference_pins"] == [] and meta["revision_sha256"] == src_snap[view] and meta["created_by_op"] == x and meta["legacy"] is True):
            bad.append(f"{d}/revisions/R000.meta.yaml 內容不符：{meta}")
    rep.check(ac, f"[{label}] R000 的 hash 等於原 requirements.yaml、檢視不變、R000.meta（{len(rms)} 個需求模型）", not bad, bad)
    # 3. _skip
    if full:
        sk = py(work, SKIP_CODE); rep.fact(f"{label}.skip", sk)
        rep.check(ac, f"[{label}] _skip：SITELIST v0.6 為 false", sk.get("SPEC-SITELIST-001@0.6", {}).get("skip") is False, sk.get("SPEC-SITELIST-001@0.6"))
        reqs_non_active = {}
        for view in rms:
            st = {r.get("status") for r in (load(work, view).get("requirements") or [])}
            reqs_non_active[f"{view.split('/')[2]}@{view.split('/')[3][1:]}"] = sorted(s for s in st if s != "ACTIVE")
        mism = {k: v for k, v in sk.items() if v["skip"] != (not reqs_non_active[k])}
        rep.check("AC-09-88", f"[{label}] _skip 與 §7 優先序一致（全部 ACTIVE → 跳過並帶 legacy 警告；有非 ACTIVE → 不跳過）", not mism and all(v["warning"] for v in sk.values() if v["skip"]),
                  {"mismatch": mism, "non_active": {k: v for k, v in reqs_non_active.items() if v}})
    # 4. RUN-20261002-001 的 sidecar
    sc = load(work, f"artifacts/requirements/_bindings/{RUN_WAIT}.yaml")
    def r000(sid, ver): return {"spec_id": sid, "spec_version": ver, "revision": "R000", "sha256": sha_file(work / f"artifacts/requirements/{sid}/v{ver}/revisions/R000.yaml")}
    ok = sc.get("from_requirement_model_revision") == r000("SPEC-SITELIST-001", "0.4") and sc.get("requirement_model_revision") == r000("SPEC-SITELIST-001", "0.6") and sc.get("legacy_binding") is False
    rep.check(ac, f"[{label}] {RUN_WAIT} 的 sidecar：from=SITELIST 0.4 R000、to=SITELIST 0.6 R000；run.yaml 不變", ok and sha_file(work / f"runs/{RUN_WAIT}/run.yaml") == src_snap[f"runs/{RUN_WAIT}/run.yaml"], sc)
    # 5. RUN-20260914-001 的處理方式
    run_rel = f"runs/{RUN_IDLE}/run.yaml"; run = load(work, run_rel); sc = load(work, f"artifacts/requirements/_bindings/{RUN_IDLE}.yaml")
    pin_ok = sc.get("requirement_model_revision") == r000("SPEC-DAILYREPORT-001", "0.1") and sc.get("legacy_binding") is True
    aprs_ok = all(sha_file(work / f"approvals/{a}.yaml") == src_snap[f"approvals/{a}.yaml"] for a in ("APR-0006", "APR-0007"))
    if mode == "acknowledge-idle":
        ok = (run["status"] == "RUNNING" and sha_file(work / run_rel) == src_snap[run_rel] and run_rel in untouched and run_rel not in restore
              and mk["mode_per_run"] == {RUN_IDLE: "acknowledge_idle"})
    elif mode == "cancel-run":
        evs = sorted((work / f"runs/{RUN_IDLE}/audit.d").glob(f"{x}-*.yaml")); acts = [load(work, e.relative_to(work))["action"] for e in evs]
        ok = (run["status"] == "CANCELLED" and run_rel in restore and restore[run_rel]["pre_sha256"] == src_snap[run_rel] and "CANCEL_RUN" in acts
              and "CANCEL_APPROVAL" not in acts and mk["mode_per_run"] == {RUN_IDLE: "cancel_run"})
        rep.fact(f"{label}.cancel_events", acts)
    else:
        ok = run["status"] == "CANCELLED" and mk["mode_per_run"] == {} and run_rel in untouched
    rep.check(ac, f"[{label}] {RUN_IDLE} 處理方式 {mode}：run.yaml／清單分類／標記正確；sidecar 綁 DAILYREPORT 0.1 R000（legacy_binding）；APR-0006、0007 不變",
              ok and pin_ok and aprs_ok, {"status": run["status"], "sidecar": sc, "in_restore": run_rel in restore, "in_untouched": run_rel in untouched, "mode_per_run": mk["mode_per_run"]})
    # 6. TC sidecar
    counts, bad, total = {}, [], 0
    for p in work.glob("testcases/versions/*/v*.yaml"):
        v = load(work, p.relative_to(work))
        if v.get("status") not in ("ACTIVE", "PENDING_APPROVAL"): continue
        total += 1; sp = work / f"testcases/_bindings/{v['testcase_id']}-v{v['version']}.yaml"
        if not sp.exists(): bad.append(f"{v['testcase_id']}-v{v['version']} 沒有 sidecar"); continue
        s = load(work, sp.relative_to(work))
        if s["requirement_model_revision"] != r000(v["spec_id"], str(v["spec_version"])) or s.get("legacy_binding") is not True: bad.append(f"{sp.name} 綁定不符")
        counts.setdefault(v["spec_id"], {}).setdefault(str(v["spec_version"]), 0); counts[v["spec_id"]][str(v["spec_version"])] += 1
    n_sc = len(list(work.glob("testcases/_bindings/*.yaml")))
    per = {k: sum(counts.get(k, {}).values()) for k in EXPECT_TC}
    rep.fact(f"{label}.tc_sidecars", {"total_sidecars": n_sc, "active_or_pending_versions": total, "by_spec_version": counts})
    rep.check(ac, f"[{label}] TC sidecar：DAILYREPORT／PLATFORMRULE／SITELIST = {per}（規格 96、44、57）；每張綁自己 spec_version 的 R000；總數 {n_sc}",
              per == EXPECT_TC and not bad and n_sc == total, bad[:20])
    # 7. CLR rev 0
    bad, n = [], 0
    for p in sorted(work.glob("clarifications/*/*/CLR-*.yaml")):
        rel = p.relative_to(work).as_posix(); c = load(work, rel); s = load(src, rel)
        if not s.get("answer"):
            if sha_file(p) != src_snap[rel]: bad.append(f"{rel} 沒有答案卻被修改")
            continue
        n += 1; revs = c.get("answer_revisions") or []
        b = revs[0]["basis"] if revs else None
        if not (len(revs) == 1 and revs[0]["rev"] == 0 and revs[0]["sha256"] == hashlib.sha256(s["answer"].encode()).hexdigest() and revs[0]["answer"] == s["answer"]
                and c["status"] == s["status"] and b["target"]["spec_id"] == s["spec_id"] and str(b["target"]["spec_version"]) == str(s["spec_version"])
                and b["target_decl_rev"] == 0 and b["closure"] == [] and rel in restore):
            bad.append(f"{rel} 的 rev 0 不符")
        if {k: v for k, v in c.items() if k != "answer_revisions"} != s: bad.append(f"{rel} 除 answer_revisions 外有其他欄位被改")
    rep.check(ac, f"[{label}] CLR rev 0：{n} 張有答案的 CLR 都有 rev 0（hash＝原答案、legacy basis、狀態不變）；沒有例外", not bad and not mk.get("exceptions"), bad[:20])
    rep.check("附錄A 5-12", f"[{label}] CLR-CASHOUT-001（spec_version 已更正為 0.1）正常建立 rev 0，不觸發 clr_rev0_skipped",
              bool(load(work, "clarifications/ba-admin/CASHOUT/CLR-CASHOUT-001.yaml").get("answer_revisions")) and not mk.get("exceptions"), mk.get("exceptions"))
    # 8. audit.legacy.log 逐位元等於原 audit.log；新 audit.log 開頭等於原檔
    bad, n = [], 0; n_restore = n_nochange = 0
    xplan = load(work, f"operations/_global/{x}.yaml"); nochange = {e["path"]: e for e in xplan.get("no_change", [])}
    for lg in sorted(k for k in src_snap if k.endswith("audit.log") and k.startswith("runs/")):
        n += 1; leg = work / lg.replace("audit.log", "audit.legacy.log")
        if not leg.exists() or sha_file(leg) != src_snap[lg]: bad.append(f"{leg.relative_to(work)} 不等於原 {lg}"); continue
        if not (work / lg).read_bytes().startswith((src / lg).read_bytes()): bad.append(f"{lg} 的開頭不等於移轉前的原檔")
        if mk["logs"].get(lg) != {"legacy": "frozen", "sha256": src_snap[lg]}: bad.append(f"標記中 {lg} 的 legacy 狀態不符")
        if lg in restore and restore[lg]["pre_sha256"] == src_snap[lg]: n_restore += 1
        elif lg in nochange and nochange[lg]["content_sha256"] == src_snap[lg] == sha_file(work / lg): n_nochange += 1
        else: bad.append(f"{lg} 既不在 restore（pre＝原檔），也不是內容不變的 no_change")
    rep.fact(f"{label}.audit_log_classes", {"restore": n_restore, "no_change": n_nochange})
    rep.check(ac, f"[{label}] audit.legacy.log 逐位元等於原 audit.log（{n} 份）；第一次 render 後 audit.log 開頭等於原檔；標記記為 frozen；"
              f"有變動的 audit.log 在 restore（{n_restore}），render 結果與原檔相同者為 no_change（{n_nochange}）", not bad, bad[:20])
    # 9. untouched（清單）與移轉不該碰的檔案
    bad = [u for u, e in untouched.items() if src_snap.get(u) is not None and sha_file(work / u) != e["pre_sha256"]]
    bad += [u for u, e in untouched.items() if src_snap.get(u) is not None and e["pre_sha256"] != src_snap[u] and not (mode == "pre-cancel" and u.startswith(("runs/", "approvals/")))]
    d = diff(src_snap, snapshot(work))
    allowed_changed = set(restore) | ({f"runs/{RUN_IDLE}/run.yaml"} if mode == "pre-cancel" else set())
    unexpected = [c for c in d["changed"] if c not in allowed_changed and c != "locks/qaos-operation.owner"]
    rep.check(ac, f"[{label}] untouched 全部吻合（{len(untouched)} 檔）；被修改的檔案都在 restore 清單；沒有檔案被刪除",
              not bad and not unexpected and not d["removed"], {"bad_untouched": bad[:20], "unexpected_changed": unexpected[:20], "removed": d["removed"][:20]})
    rep.fact(f"{label}.diff_vs_src", {"added": len(d["added"]), "changed": len(d["changed"]), "removed": len(d["removed"])})
    # 10. run sidecar 的分佈
    by_wf = {}
    for p in work.glob("runs/*/run.yaml"):
        r = load(work, p.relative_to(work)); has = (work / f"artifacts/requirements/_bindings/{r['run_id']}.yaml").exists()
        by_wf.setdefault(r["workflow_id"], {"runs": 0, "sidecars": 0}); by_wf[r["workflow_id"]]["runs"] += 1; by_wf[r["workflow_id"]]["sidecars"] += has
    rep.fact(f"{label}.run_sidecars_by_workflow", by_wf)
    return x, manifest

def assert_rolled_back(rep, work: pathlib.Path, src_snap: dict, pre_snap: dict, x: str, label: str):
    d = diff(pre_snap, snapshot(work))
    added_ok = all(p.startswith(("operations/", "locks/", "runs/_audit.d/")) or (p.startswith("runs/RUN-") and "/audit.d/" in p) for p in d["added"])
    changed = [c for c in d["changed"] if c != "locks/qaos-operation.owner"]
    sts = sorted(p.name for p in (work / "operations/_global/status.d").glob(f"{x}-*.yaml"))
    rep.check("AC-09-55/56", f"[{label}] rollback 後：restore 回到 pre、remove 不存在、沒有其他檔案被改或刪；只新增稽核／控制檔；X 的終態為 completed＋rolled_back",
              not changed and not d["removed"] and added_ok and sts == [f"{x}-completed.yaml", f"{x}-rolled_back.yaml"] and not (work / "artifacts/requirements/_migration.yaml").exists(),
              {"changed": changed[:20], "removed": d["removed"][:20], "added_not_allowed": [p for p in d["added"] if not (p.startswith(("operations/", "locks/", "runs/_audit.d/")) or "/audit.d/" in p)][:20], "x_status": sts})

# ---------------------------------------------------------------- S_post 的真實資料驗收（--real-data-checks）
def real_data_checks(rep, src, work, kind):
    """在完成移轉、maintenance end 之後（S_post）執行。kind=ack：AC-09-3／20、11、24、31、A-B1-7、08-4、08-16／32、6-35；kind=cancel：AC-09-17、32。"""
    if kind == "ack": _real_ack(rep, src, work)
    else: _real_cancel(rep, src, work)

def _real_ack(rep, src, work):
    # AC-09-31、AC-A-B1-7：DAILYREPORT 96 條分兩組（函式層：記憶體中的 run 與 CIR，g_impact 讀真實 TC 與 sidecar）
    code = r"""
import json, copy
from tools.qaos import gates, rm
S = "SPEC-DAILYREPORT-001"
cand, errs = gates._cia_candidates(S)
p01, p02 = rm.pin_of(S, "0.1", "R000"), rm.pin_of(S, "0.2", "R000")
A = sorted(t for t in cand if cand[t] == p01); B = sorted(t for t in cand if cand[t] == p02)
r01, r02 = rm.requirements_of(p01), rm.requirements_of(p02)
def diff(frm): return [{"requirement_id": r, "change": "unchanged"} for r in sorted(set(frm) | set(r02))]
groups = [{"from_pin": p01, "testcase_ids": A, "requirement_diff": diff(r01)}, {"from_pin": p02, "testcase_ids": B, "requirement_diff": diff(r02)}]
impact = [{"testcase_id": t, "active_version": 1, "impact": "unaffected", "reason": "-", "affected_requirement_ids": [], "pin_group_index": 0 if t in A else 1} for t in A + B]
cir = {"change_impact_id": "CI-P6", "spec_id": S, "from_version": "0.1", "to_version": "0.2", "from_rm_revision": p01, "to_rm_revision": p02,
       "requirement_diff": diff(r01), "pin_groups": groups, "testcase_impact": impact, "summary": {}, "completeness": {"all_active_requirements_judged": True, "all_referencing_testcases_judged": True}}
run = {"run_id": "RUN-20261008-999", "requirement_model_revision": p02, "from_requirement_model_revision": p01}
ok = gates.g_impact(run, None, {"ChangeImpactReport": {"artifact_id": "ART-CIR-P6", "payload": cir}})
bad = copy.deepcopy(cir); bad["pin_groups"] = bad["pin_groups"][1:]; bad["testcase_impact"] = [i for i in bad["testcase_impact"] if i["testcase_id"] in B]
for i in bad["testcase_impact"]: i["pin_group_index"] = 0
only02 = gates.g_impact(run, None, {"ChangeImpactReport": {"artifact_id": "ART-CIR-P6", "payload": bad}})
print(json.dumps({"candidates": len(cand), "errs": errs, "g01": len(A), "g02": len(B), "pass_issues": ok, "only02_issues": [i[:120] for i in only02]}, ensure_ascii=False))
"""
    r = py(work, code); rep.fact("AC-09-31.result", r)
    rep.check("AC-09-31／AC-A-B1-7", "DAILYREPORT 現況 96 條 ACTIVE TC 分兩組（0.1 R000 48、0.2 R000 48，皆 legacy sidecar）→ g_impact PASS（函式層；to 端以 0.2 R000 代替未匯入的 0.3）",
              r["candidates"] == 96 and r["g01"] == 48 and r["g02"] == 48 and r["pass_issues"] == [] and not r["errs"], r)
    rep.check("AC-09-31", "只判 0.2 的 48 條 → FAIL（G2、G5）", any(i.startswith("G2") for i in r["only02_issues"]) and any(i.startswith("G5") for i in r["only02_issues"]), r["only02_issues"])
    # AC-08-4：CLR-CASHFLOW-005 rev 0 的 clarification 型 SourceRef 本身驗證（函式層）；X16 對舊格式 CLR 的結果
    code = r"""
import json
from tools.qaos import sources, clarification as clr
c = clr.load("CLR-CASHFLOW-005"); r0 = c["answer_revisions"][0]
q = r0["answer"].strip().splitlines()[0][:40]
ref = {"type": "clarification", "clarification_id": "CLR-CASHFLOW-005", "answer_rev": 0, "answer_sha256": r0["sha256"], "quote": q}
e1, w1 = sources.validate(ref)
e2, _ = sources.validate(dict(ref, answer_sha256="0" * 64))
e3, _ = sources.validate(dict(ref, quote="這段文字不在答案裡"))
scope = {"spec_id": c["spec_id"], "requirement_id": c["requirement_id"], "subject": "x", "role_scope": ["*"], "params": {}}
x16 = sources.x16(ref, scope, r0["basis_hash"], at=(c["requirement_id"], "Q1"))
print(json.dumps({"status": c["status"], "rev0_basis": r0["basis"], "valid": e1, "warnings": w1, "bad_sha": e2, "bad_quote": e3, "x16_legacy_scope": x16, "self_scope": sources.self_scope(c)}, ensure_ascii=False))
"""
    r = py(work, code); rep.fact("AC-08-4.result", r)
    rep.check("AC-08-4", "CLR-CASHFLOW-005（APPLIED，移轉後有 rev 0）的 clarification 型 SourceRef 本身驗證 PASS；sha 或 quote 不符 → 錯誤（函式層，未產生 Draft、未跑 G-SPEC）",
              r["status"] == "APPLIED" and r["valid"] == [] and r["bad_sha"] and r["bad_quote"], r)
    # AC-08-16／32 的可驗部分：CLR-DAILYREPORT-010 rev 0 的 legacy basis
    code = r"""
import json
from tools.qaos import sources, clarification as clr, store
c = clr.load("CLR-DAILYREPORT-010"); r0 = c["answer_revisions"][0]
vers = [v["spec_version"] for v in store.load("specs/ba-admin/DAILYREPORT/SPEC-DAILYREPORT-001/spec.yaml")["versions"]]
print(json.dumps({"status": c["status"], "requirement_id": c["requirement_id"], "basis": r0["basis"], "basis_hash_ok": sources.basis_hash(r0["basis"]) == r0["basis_hash"], "imported_versions": vers}, ensure_ascii=False))
"""
    r = py(work, code); rep.fact("AC-08-16_32.result", r)
    b = r["basis"]
    rep.check("AC-08-16／32（部分）", "CLR-DAILYREPORT-010 rev 0 的 basis 是 DAILYREPORT 0.1（legacy、target_decl_rev 0、閉包空），basis_hash 可重算；0.3 未匯入，applicability 與 X16 部分不能用快照驗",
              b["target"]["spec_id"] == "SPEC-DAILYREPORT-001" and str(b["target"]["spec_version"]) == "0.1" and b["target_decl_rev"] == 0 and b["closure"] == [] and r["basis_hash_ok"], r)
    # 附錄 A 6-35：現存 ANSWERED 的舊格式 CLR（只列出）
    lst = []
    for p in sorted(work.glob("clarifications/*/*/CLR-*.yaml")):
        c = load(work, p.relative_to(work))
        if not all(k in c for k in ("subject", "role_scope", "params")):
            lst.append({"id": c["clarification_id"], "status": c["status"], "spec": f"{c['spec_id']}@{c['spec_version']}", "requirement_id": c.get("requirement_id"),
                        "resolution": c.get("resolution"), "rev0": bool(c.get("answer_revisions"))})
    rep.fact("6-35.legacy_clrs", lst)
    rep.fact("6-35.answered_legacy", [c for c in lst if c["status"] == "ANSWERED"])
    # AC-09-11：SITELIST v0.6 的新 run 不跳過 T1；對照 DAILYREPORT 0.2 跳過
    r = q(rep, work, "AC-09-11 run new spec-to-testcase SITELIST 0.6", "run", "new", "spec-to-testcase", "--input", "spec_id=SPEC-SITELIST-001", "--input", "spec_version=0.6", "--by", BY)
    rid = r.stdout.split()[0] if r.returncode == 0 else None
    t1 = next(t for t in load(work, f"runs/{rid}/run.yaml")["tasks"] if t["task_id"] == "T1") if rid else {}
    rep.check("AC-09-11", "SITELIST v0.6（022、023 為 DRAFT 的 legacy RM）的新 spec-to-testcase run：T1 不跳過", rid is not None and t1.get("status") == "READY", {"run": rid, "T1": t1.get("status")})
    r = q(rep, work, "AC-09-11 對照 run new spec-to-testcase DAILYREPORT 0.2", "run", "new", "spec-to-testcase", "--input", "spec_id=SPEC-DAILYREPORT-001", "--input", "spec_version=0.2", "--by", BY)
    rid2 = r.stdout.split()[0] if r.returncode == 0 else None
    run2 = load(work, f"runs/{rid2}/run.yaml") if rid2 else {}
    t1b = next((t for t in run2.get("tasks", []) if t["task_id"] == "T1"), {})
    rep.check("AC-09-11（對照）", "DAILYREPORT 0.2（全部 ACTIVE、legacy R000）：T1 跳過，run 綁 0.2 R000，audit 有 legacy 警告",
              t1b.get("status") == "DONE" and t1b.get("iteration") == 0 and not t1b.get("output_artifact_ids") and (run2.get("requirement_model_revision") or {}).get("revision") == "R000"
              and all(k in (work / f"runs/{rid2}/audit.log").read_text(encoding="utf-8") for k in ("WARN_LEGACY_SKIP", "SKIP_TASK")),
              {"run": rid2, "T1": t1b.get("status"), "pin": run2.get("requirement_model_revision")})
    # 觀察：ARCADE 0.7 的 R000 有 1 條 RETIRED 需求 → _skip false；無 T0 流程的 run new 是否也被擋（§4.3「最新 revision 有非 ACTIVE 的需求」）
    tc = next(load(work, p.relative_to(work))["testcase_id"] for p in sorted(work.glob("testcases/registry/TC-ARCADE-*.yaml")) if load(work, p.relative_to(work)).get("status") == "ACTIVE")
    r = q(rep, work, f"觀察 run new testcase-revision {tc}（ARCADE 0.7）", "run", "new", "testcase-revision", "--input", f"testcase_id={tc}", "--input", "spec_id=SPEC-ARCADE-001", "--input", "spec_version=0.7",
          "--input", "reason=P6 預演探查", "--by", BY, expect_rc=None)
    rep.fact("observe.arcade_testcase_revision", {"tc": tc, "rc": r.returncode, "stdout": r.stdout[-300:], "stderr": r.stderr[-500:]})
    # AC-09-24：regression-generation 不產生 sidecar（快照中沒有既有的 regression-generation run；只能驗移轉後新 run）
    r = q(rep, work, "AC-09-24 run new regression-generation", "run", "new", "regression-generation", "--input", 'target_suites=["smoke"]', "--input", "scope=all", "--input", "trigger=manual", "--by", BY, expect_rc=None)
    rid3 = r.stdout.split()[0] if r.returncode == 0 else None
    rep.check("AC-09-24（部分）", "移轉後新建的 regression-generation run 不綁 revision、沒有 sidecar（快照沒有既有的 regression-generation run）",
              rid3 is not None and not (work / f"artifacts/requirements/_bindings/{rid3}.yaml").exists() and "requirement_model_revision" not in load(work, f"runs/{rid3}/run.yaml"),
              {"run": rid3, "rc": r.returncode, "stderr": r.stderr[-300:]})
    # AC-09-3／20：RUN-20261002-001 複本續做依 sidecar
    q(rep, work, "AC-09-3 declare-empty SITELIST 0.6", "spec", "reference", "declare-empty", "SPEC-SITELIST-001@0.6", "--reason", "P6 預演：製造 R001", "--by", BY)
    q(rep, work, "AC-09-3 accept-declaration → R001", "req", "accept-declaration", "SPEC-SITELIST-001@0.6", "--rev", "R000", "--reason", "P6 預演：製造 R001", "--by", BY)
    r001 = (work / "artifacts/requirements/SPEC-SITELIST-001/v0.6/revisions/R001.yaml").exists()
    clrs = [i["id"] for i in load(work, "approvals/APR-0192.yaml")["impact"] if i["entity_type"] == "Clarification"]
    before = {c: load(work, next(work.glob(f"clarifications/*/*/{c}.yaml")).relative_to(work))["status"] for c in clrs}
    for c in clrs:
        if before[c] in ("OPEN", "ASKED"):
            q(rep, work, f"AC-09-3 answer {c}（預演用答案，非 PM 回答）", "clarification", "answer", c, "--answer", "P6 預演用答案：非 PM 回答，只為了讓 APR-0192 的複本可以核准", "--answered-by", "p6-rehearsal",
              "--resolution", "requirement_clarified", "--by", BY)
    r = q(rep, work, "AC-09-3 approve APR-0192（複本）", "approve", "APR-0192", "--decision", "approve", "--by", BY, expect_rc=None)
    run = load(work, f"runs/{RUN_WAIT}/run.yaml"); t0 = next(t for t in run["tasks"] if t["task_id"] == "T0")
    rd = q(rep, work, "AC-09-3 dispatch RUN-20261002-001 T0", "dispatch", RUN_WAIT, "T0", expect_rc=None)
    run = load(work, f"runs/{RUN_WAIT}/run.yaml"); t0 = next(t for t in run["tasks"] if t["task_id"] == "T0")
    pk = load(work, t0["dispatch_packets"][-1]["path"]) if t0.get("dispatch_packets") else {}
    pins = pk.get("rm_pins") or {}
    rep.fact("AC-09-3.result", {"R001_created": r001, "clr_before": before, "approve_rc": r.returncode, "approve_err": r.stderr[-400:], "T0": {"status": t0["status"], "iteration": t0.get("iteration")},
                                "dispatch_rc": rd.returncode, "dispatch_err": rd.stderr[-400:], "rm_pins": pins, "run_has_pin_fields": [k for k in run if "revision" in k]})
    rep.check("AC-09-3／20", f"{RUN_WAIT} 複本：另有 SITELIST 0.6 R001 之後核准 APR-0192 → T0 重開（iteration+1）→ 派發包的前版 RM 是 sidecar 的 R000（不是 R001），from 是 0.4 R000",
              r001 and r.returncode == 0 and t0["status"] in ("READY", "RUNNING") and (pins.get("target") or {}).get("revision") == "R000" and (pins.get("target") or {}).get("spec_version") == "0.6"
              and (pins.get("from") or {}).get("revision") == "R000" and (pins.get("from") or {}).get("spec_version") == "0.4", {"T0": t0.get("status"), "rm_pins": pins})

def _real_cancel(rep, src, work):
    # AC-09-17、32：run cancel RUN-20261002-001（APR-0192 PENDING）
    sc_rel = f"artifacts/requirements/_bindings/{RUN_WAIT}.yaml"; sc_before = sha_file(work / sc_rel)
    q(rep, work, "AC-09-17 run cancel RUN-20261002-001", "run", "cancel", RUN_WAIT, "--by", BY)
    snap1 = snapshot(work)
    q(rep, work, "AC-09-32 run cancel 重送（同一請求）", "run", "cancel", RUN_WAIT, "--by", BY)
    d = diff(snap1, snapshot(work)); d["changed"] = [c for c in d["changed"] if c != "locks/qaos-operation.owner"]
    run = load(work, f"runs/{RUN_WAIT}/run.yaml"); apr = load(work, "approvals/APR-0192.yaml")
    evs = [load(work, p.relative_to(work)) for p in sorted((work / f"runs/{RUN_WAIT}/audit.d").glob("*.yaml"))]
    n_apr_ev = sum(1 for e in evs if e["action"] == "CANCEL_APPROVAL"); n_run_ev = sum(1 for e in evs if e["action"] == "CANCEL_RUN")
    pend = [p.stem for p in work.glob("approvals/APR-*.yaml") if (lambda a: a.get("run_id") == RUN_WAIT and a.get("status") == "PENDING")(load(work, p.relative_to(work)))]
    rep.check("AC-09-17", f"{RUN_WAIT} → CANCELLED；它所有 PENDING 核准單（快照中只有 APR-0192）→ CANCELLED；sidecar 保留", run["status"] == "CANCELLED" and apr["status"] == "CANCELLED" and not pend and sha_file(work / sc_rel) == sc_before,
              {"run": run["status"], "APR-0192": apr["status"], "pending_left": pend})
    rep.check("AC-09-32", "run cancel 重送：核准單只轉換一次、audit 不重複（重送沒有新增或修改任何檔案）", n_apr_ev == 1 and n_run_ev == 1 and not d["added"] and not d["changed"] and not d["removed"],
              {"CANCEL_APPROVAL": n_apr_ev, "CANCEL_RUN": n_run_ev, "resend_diff": d})
    # 「之後的新 run 不會綁到 0.6」：快照沒有 SITELIST 0.7；以 0.6 原檔加一行標記做成合成的 0.7（只存在於這份工作複本）
    v06 = load(work, "specs/ba-admin/SITELIST/SPEC-SITELIST-001/spec.yaml")
    e06 = next(v for v in v06["versions"] if v["spec_version"] == "0.6")
    srcfile = work / "specs/ba-admin/SITELIST/SPEC-SITELIST-001" / e06["file"]
    syn = work.parent / f"{work.name}-synthetic-SITELIST-0.7.md"
    syn.write_text(srcfile.read_text(encoding="utf-8") + "\n\n<!-- P6 預演合成版本 0.7：只用來驗證新 run 的綁定，不是真實文件 -->\n", encoding="utf-8")
    q(rep, work, "AC-09-17 spec import 合成 SITELIST 0.7", "spec", "import", syn, "--spec-id", "SPEC-SITELIST-001", "--version", "0.7", "--product", "ba-admin", "--area", "SITELIST", "--by", BY)
    r = q(rep, work, "AC-09-17 run new spec-change-impact 0.4→0.7", "run", "new", "spec-change-impact", "--input", "spec_id=SPEC-SITELIST-001", "--input", "from_version=0.4", "--input", "to_version=0.7", "--by", BY)
    rid = r.stdout.split()[0] if r.returncode == 0 else None
    q(rep, work, "AC-09-17 dispatch 新 run T0", "dispatch", rid, "T0", expect_rc=None) if rid else None
    run = load(work, f"runs/{rid}/run.yaml") if rid else {}
    t0 = next((t for t in run.get("tasks", []) if t["task_id"] == "T0"), {})
    pk = load(work, t0["dispatch_packets"][-1]["path"]) if t0.get("dispatch_packets") else {}
    blob = json.dumps({"run": run, "packet": pk}, ensure_ascii=False, default=str)
    pins = [run.get("from_requirement_model_revision"), run.get("requirement_model_revision")] + [v for v in (pk.get("rm_pins") or {}).values() if isinstance(v, dict)]
    pins += (pk.get("rm_pins") or {}).get("pin_groups") or []
    bound_06 = [p for p in pins if isinstance(p, dict) and (p.get("spec_version") == "0.6" or (p.get("from_pin") or {}).get("spec_version") == "0.6")]
    rep.fact("AC-09-17.new_run", {"run": rid, "from": run.get("from_requirement_model_revision"), "to": run.get("requirement_model_revision"), "T0": t0.get("status"), "packet_rm_pins": pk.get("rm_pins")})
    rep.check("AC-09-17", "取消之後的新 run（0.4→0.7，0.7 為合成檔）：from 綁 0.4 R000，run 與 T0 派發包都沒有綁到 0.6 的任何 revision",
              rid is not None and (run.get("from_requirement_model_revision") or {}).get("revision") == "R000" and (run.get("from_requirement_model_revision") or {}).get("spec_version") == "0.4" and not bound_06,
              {"bound_06": bound_06})

# ---------------------------------------------------------------- AC-A-B1-7：同一個 root 依序驗收（--mode ac-b1-7）
DR = "SPEC-DAILYREPORT-001"
R1_CHANGES = {"REQ-DAILYREPORT-013": "P6 預演：重新分析後的 REQ-013 敘述（第 1 輪）"}
R2_CHANGES = {**R1_CHANGES, "REQ-DAILYREPORT-012": "P6 預演：重新分析後的 REQ-012 敘述（第 2 輪）"}

def flow(work, body: str):
    """在子程序以 tests/p6_acb17_flow 的正式流程 helper 執行；body 的最後一行印出 JSON。"""
    return py(work, "import json\nfrom tests import p6_acb17_flow as F\n" + body)

def ac_b1_7(rep, src, work):
    """移轉（acknowledge-idle）、maintenance end 之後，在同一份工作複本依序：
    ① 第 1 輪同版本 CIA（0.2 R000→R001，declaration_changed）：96 張候選分兩組（0.1 R000、0.2 R000 各 48，legacy sidecar）→ G-IMPACT PASS，
       REQ-013 改變 → 3 張 affected，正式走完 T2～T5 → APPLIED；
    ② 第 2 輪（R001→R002，再一次 declaration_changed）：AC-09-28、29——三組（0.1 R000、0.2 R000、0.2 R001），R000 組的 diff 涵蓋 R001 的變更；
       先送只判 from 端那組的反例 → FAIL（G2、G5），再送正確 CIR → PASS → T2～T5 → APPLIED；
    ③ 第 3 輪（R002→R003）的 T1：AC-09-35～41 各一份錯誤 CIR（另加 G7、G8）各自 FAIL 在對應檢查，FAIL 後 T1 回 READY；最後正確 CIR → NO_IMPACT → COMPLETED。"""
    AC = "AC-A-B1-7"
    # ⓪ 起點：96 張 legacy sidecar R000
    r = flow(work, r"""
from tools.qaos import rm, gates, store
cand, errs = gates._cia_candidates(F.SPEC)
p01, p02 = rm.pin_of(F.SPEC, "0.1", "R000"), rm.pin_of(F.SPEC, "0.2", "R000")
leg = {t: store.load(rm.tc_sidecar_path(t, v)).get("legacy_binding") if store.exists(rm.tc_sidecar_path(t, v)) else None for t, v, _ in F.active()}
inver = [t for t, v, d in F.active() if d.get("requirement_model_revision")]
print(json.dumps({"candidates": len(cand), "errs": errs, "g01": sum(1 for t in cand if cand[t] == p01), "g02": sum(1 for t in cand if cand[t] == p02),
                  "legacy_sidecar": sum(1 for x in leg.values() if x is True), "pin_in_version_file": inver}))""")
    rep.fact("B1-7.start", r)
    rep.check(AC, "⓪ 移轉後起點：DAILYREPORT 候選 96 張＝0.1 R000 48＋0.2 R000 48，全部以 legacy sidecar 綁定（版本檔沒有 pin）",
              r["candidates"] == 96 and r["g01"] == 48 and r["g02"] == 48 and r["legacy_sidecar"] == 96 and not r["pin_in_version_file"] and not r["errs"], r)
    # ① 第 1 輪
    q(rep, work, "B1-7 ① spec reference declare-empty DAILYREPORT 0.2（製造 declaration_changed）", "spec", "reference", "declare-empty", f"{DR}@0.2", "--reason", "P6 AC-A-B1-7 預演：移轉後補宣告", "--by", BY)
    r = flow(work, f"from tools.qaos import rm\nprint(json.dumps(rm.outdated(rm.pin_of(F.SPEC, '0.2', 'R000'))))")
    rep.check(AC, "① 0.2 R000 判定為 declaration_changed（同版本 CIA 的觸發條件，第 5 章 §8）", r["declaration_changed"] is True, r)
    r1 = flow(work, f"print(json.dumps(F.full_round('R000', {R1_CHANGES!r}, 1)))"); rep.fact("B1-7.round1", r1)
    st = {s["stop"]: s for s in r1["stops"]}; g = {x["from_pin"]: x for x in r1["groups"]}
    rep.check(AC, f"① run new（{r1['run_id']}）：from 綁 0.2 R000、T0 READY", st["run new"]["from_pin"] == "0.2 R000" and st["run new"]["T0"] == "READY", st["run new"])
    rep.check(AC, "① T0 G-SPEC PASS → run 的 to 綁 0.2 R001、T1 READY", st["T0 G-SPEC"]["gate"] == "PASS" and st["T0 G-SPEC"]["to_pin"] == "0.2 R001" and st["T0 G-SPEC"]["T1"] == "READY", st["T0 G-SPEC"])
    rep.check(AC, "① T1 CIR：96 張候選分兩組（0.1 R000 48、0.2 R000 48）→ G-IMPACT PASS；派發包帶兩端與兩組 pin",
              sorted(g) == ["0.1 R000", "0.2 R000"] and g["0.1 R000"]["n"] == 48 and g["0.2 R000"]["n"] == 48 and st["T1 G-IMPACT"]["gate"] == "PASS" and not st["T1 G-IMPACT"]["issues"]
              and r1["packet_T1"] == {"from": "0.2 R000", "target": "0.2 R001", "pin_groups": ["0.1 R000", "0.2 R000"]},
              {"groups": [{k: v for k, v in x.items() if k != "testcase_ids"} for x in r1["groups"]], "gate": st["T1 G-IMPACT"], "packet": r1["packet_T1"]})
    rep.check(AC, "① 0.2 R000 組的 diff 只有 REQ-013 改變；affected＝引用 REQ-013 的 3 張（TC-040、105 在 0.2，TC-041 在 0.1）；change_impact TEST_UPDATE_REQUIRED、T2 READY",
              g["0.2 R000"]["diff_changed"] == ["REQ-DAILYREPORT-013"] and sorted(r1["affected"]) == ["TC-DAILYREPORT-040", "TC-DAILYREPORT-041", "TC-DAILYREPORT-105"]
              and st["T1 G-IMPACT"]["change_impact"] == "TEST_UPDATE_REQUIRED" and st["T1 G-IMPACT"]["T2"] == "READY", {"affected": r1["affected"], "ci": st["T1 G-IMPACT"]["change_impact"]})
    _round_tail(rep, r1, "①", "0.2 R001")
    # ② 第 2 輪（AC-09-28、29）
    ref = work.parent / f"{work.name}-synthetic-DAILYREPORTREF-1.0.md"
    ref.write_text("# 場館日結報表補充參考（P6 預演合成檔，不是真實文件）\n\n## 說明\n\n只用來在工作複本製造第二次 declaration_changed。\n", encoding="utf-8")
    q(rep, work, "B1-7 ② spec import 合成參考 SPEC-DAILYREPORTREF-001@1.0", "spec", "import", ref, "--spec-id", "SPEC-DAILYREPORTREF-001", "--version", "1.0", "--product", "ba-admin", "--area", "DAILYREPORT", "--by", BY)
    q(rep, work, "B1-7 ② spec reference add（informative）→ declaration_changed", "spec", "reference", "add", f"{DR}@0.2", "--ref", "SPEC-DAILYREPORTREF-001@1.0", "--role", "informative", "--by", BY)
    r2 = flow(work, f"print(json.dumps(F.full_round('R001', {R2_CHANGES!r}, 2, negative_only_from_group=True)))"); rep.fact("B1-7.round2", r2)
    st = {s["stop"]: s for s in r2["stops"]}; g = {x["from_pin"]: x for x in r2["groups"]}
    rep.check("AC-09-28", f"② run new（{r2['run_id']}）：from 是第 1 輪產生的 0.2 R001；T0 PASS → to 0.2 R002",
              st["run new"]["from_pin"] == "0.2 R001" and st["T0 G-SPEC"]["gate"] == "PASS" and st["T0 G-SPEC"]["to_pin"] == "0.2 R002", [st["run new"], st["T0 G-SPEC"]])
    ob = r2["only_from_group"]
    if r2.get("aborted"):
        rep.check("AC-09-28", "② 反例：只判 run 的 from 端那組 → G-IMPACT FAIL（G2、G5）", False, ob); return
    rep.check("AC-09-28", "② 反例：只判 run 的 from 端那組（0.2 R001，3 張），缺少 TC-B（R000）的判定 → G-IMPACT FAIL（G2、G5）；T1 回 READY、change_impact 不前進",
              ob["result"] == "FAIL" and any(i.startswith("G2") for i in ob["issues"]) and any(i.startswith("G5") for i in ob["issues"]) and ob["T1_after"]["status"] == "READY"
              and ob["ci_after"] not in ("TEST_UPDATE_REQUIRED", "NO_IMPACT", "IMPACTED"), ob)
    rep.check("AC-09-28／30", "② 正確 CIR：三組（0.1 R000 47、0.2 R000 46、0.2 R001 3，共 96）——legacy sidecar 與版本檔 pin 混合 → G-IMPACT PASS；派發包帶三組",
              sorted(g) == ["0.1 R000", "0.2 R000", "0.2 R001"] and (g["0.1 R000"]["n"], g["0.2 R000"]["n"], g["0.2 R001"]["n"]) == (47, 46, 3)
              and sorted(g["0.2 R001"]["testcase_ids"]) == ["TC-DAILYREPORT-040", "TC-DAILYREPORT-041", "TC-DAILYREPORT-105"] and st["T1 G-IMPACT"]["gate"] == "PASS"
              and r2["packet_T1"] == {"from": "0.2 R001", "target": "0.2 R002", "pin_groups": ["0.1 R000", "0.2 R000", "0.2 R001"]},
              {"groups": [{k: v for k, v in x.items() if k != "testcase_ids"} for x in r2["groups"]], "gate": st["T1 G-IMPACT"], "packet": r2["packet_T1"]})
    rep.check("AC-09-29", "② TC-B（0.2 R000）那組的 requirement_diff 是 R000→R002：含第 1 輪的 REQ-013 與本輪的 REQ-012；R001 組只有 REQ-012",
              g["0.2 R000"]["diff_changed"] == ["REQ-DAILYREPORT-012", "REQ-DAILYREPORT-013"] and g["0.2 R001"]["diff_changed"] == ["REQ-DAILYREPORT-012"]
              and g["0.2 R000"]["diff_n"] == g["0.2 R001"]["diff_n"] == 26, {k: g[k]["diff_changed"] for k in g if k != "0.1 R000"})
    rep.check("AC-09-28", "② 本輪影響 TC-B：affected＝引用 REQ-012 的 TC-038、039（0.1 R000 組，第 1 輪時 unaffected）",
              sorted(r2["affected"]) == ["TC-DAILYREPORT-038", "TC-DAILYREPORT-039"], r2["affected"])
    _round_tail(rep, r2, "②", "0.2 R002")
    rep.check("AC-09-28", "② 結束後 pin 分佈：0.1 R000 45、0.2 R000 46、0.2 R001 3、0.2 R002 2（共 96）",
              r2["final"]["pins_by_group"] == {"0.1 R000": 45, "0.2 R000": 46, "0.2 R001": 3, "0.2 R002": 2}, r2["final"]["pins_by_group"])
    # ③ 反例（AC-09-35～41；另加 G7、G8）
    ref2 = work.parent / f"{work.name}-synthetic-DAILYREPORTREF-2.0.md"
    ref2.write_text("# 場館日結報表補充參考二（P6 預演合成檔，不是真實文件）\n\n## 說明\n\n只用來在工作複本製造第三次 declaration_changed。\n", encoding="utf-8")
    q(rep, work, "B1-7 ③ spec import 合成參考 SPEC-DAILYREPORTREF-002@1.0", "spec", "import", ref2, "--spec-id", "SPEC-DAILYREPORTREF-002", "--version", "1.0", "--product", "ba-admin", "--area", "DAILYREPORT", "--by", BY)
    q(rep, work, "B1-7 ③ spec reference add（informative）→ declaration_changed", "spec", "reference", "add", f"{DR}@0.2", "--ref", "SPEC-DAILYREPORTREF-002@1.0", "--role", "informative", "--by", BY)
    r3 = flow(work, "print(json.dumps(F.negatives_round('R002')))"); rep.fact("B1-7.round3", r3)
    rep.check(AC, f"③ run new（{r3['run_id']}）：from 0.2 R002；T0 PASS → to 0.2 R003（內容同 R002）；A＝{r3['A']}（{r3['A_pin']}）、B＝{r3['B']}（{r3['B_pin']}）、TC-Z＝{r3['Z']}",
              r3["T0"] == "PASS" and r3["from_pin"] == "0.2 R002" and r3["to_pin"] == "0.2 R003" and r3["A_pin"] == "0.2 R001" and r3["B_pin"] == "0.2 R000"
              and sum(x["n"] for x in r3["groups"]) == 96 and len(r3["groups"]) == 4, {k: r3[k] for k in ("T0", "from_pin", "to_pin", "A", "B", "Z")})
    for c in r3["cases"]:
        rep.check(c["case"].split(" ")[0] if c["case"].startswith("AC-") else "G7／G8（附加）", f"③ {c['case']} → G-IMPACT FAIL 在 {c['expect']}；FAIL 後 T1 回 READY、iteration 不變、run 仍 RUNNING",
                  c["result"] == "FAIL" and c["expect"] in c["codes"] and c["T1_after"]["status"] == "READY" and c["T1_after"]["iteration"] == c["T1_before"]["iteration"] and c["run_status"] == "RUNNING"
                  and c["change_impact"] not in ("TEST_UPDATE_REQUIRED", "NO_IMPACT", "IMPACTED"),
                  {k: c[k] for k in ("run_id", "result", "codes", "issues", "error", "T1_after", "change_impact", "run_status")})
    rep.fact("B1-7.round3.recovery_runs", r3["recovery_runs"])
    gd = r3["good"]
    rep.check(AC, "③ 全部反例都在同一個 run 的 T1 提交（沒有任何反例逃脫而需要重開 run）", not r3["recovery_runs"], r3["recovery_runs"])
    rep.check(AC, "③ 反例之後同一個 T1 提交正確 CIR → G-IMPACT PASS → 全部 unaffected → NO_IMPACT、T6 DONE、run COMPLETED（反例沒有留下影響）",
              gd["result"] == "PASS" and not gd["affected"] and gd["change_impact"] == "NO_IMPACT" and gd["status"] == "COMPLETED" and gd["tasks"]["T6"]["status"] == "DONE", gd)

def _round_tail(rep, r, tag, new_pin):
    st = {s["stop"]: s for s in r["stops"]}; f = r["final"]
    for k in ("T2 G-DESIGN", "T3 G-TVAL", "T3RR G-RISK", "T4 G-COMPARE"):
        rep.check("AC-A-B1-7", f"{tag} {k} PASS", st[k]["gate"] == "PASS", st[k])
    rep.check("AC-A-B1-7", f"{tag} T4 之後 run WAITING_HUMAN、核准單 {r['approval']} 為 APPLY_CHANGE；T4 派發包帶與 T1 相同的兩端與 pin_groups",
              st["T4 G-COMPARE"]["run_status"] == "WAITING_HUMAN" and st["T4 G-COMPARE"]["approval_type"] == "APPLY_CHANGE" and r["packet_T4"] == r["packet_T1"], [st["T4 G-COMPARE"], r["packet_T4"]])
    rep.check("AC-A-B1-7", f"{tag} T5 approve → APPLIED、run COMPLETED、T6 DONE", f["status"] == "COMPLETED" and f["change_impact"] == "APPLIED" and f["tasks"]["T6"]["status"] == "DONE", {k: f[k] for k in ("status", "change_impact")})
    bad = {t: x for t, x in f["affected_after"].items() if not (x["version"] == x["old_version"] + 1 and x["pin"] == new_pin and x["pin_in_version_file"] == new_pin)}
    rep.check("AC-A-B1-7", f"{tag} affected 的 TC 升版、新版本檔綁 {new_pin}；unaffected 的 TC 版本不變、sidecar 逐位元不變、沒有新增 sidecar；候選仍 96",
              not bad and not f["unaffected_version_changed"] and not f["sidecars_changed"] and not f["sidecars_added"] and f["candidates"] == 96,
              {"affected_after": f["affected_after"], "bad": bad, "unaffected_version_changed": f["unaffected_version_changed"], "sidecars_changed": f["sidecars_changed"], "sidecars_added": f["sidecars_added"]})

def main_ac_b1_7(a, src, work):
    rep = Report(a); t_all = time.time()
    rep.fact("code_commit", a.code_commit or subprocess.run(["git", "-C", str(CODE), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip() or "(非 git 目錄)")
    rep.fact("code_files_sha256", {p: sha_file(CODE / p) for p in ("tests/p6_rehearsal.py", "tests/p6_acb17_flow.py", "tools/qaos/gates.py", "tools/qaos/engine.py")})
    src_snap = snapshot(src); rep.fact("src_files", len(src_snap)); rep.fact("src_tree_sha256", hashlib.sha256(json.dumps(src_snap, sort_keys=True).encode()).hexdigest())
    shutil.copytree(src, work, symlinks=True, dirs_exist_ok=True)
    for p in [work, *work.rglob("*")]:
        if not p.is_symlink(): p.chmod(p.stat().st_mode | stat.S_IWUSR)
    q(rep, work, "maintenance start", "maintenance", "start", "--by", BY)
    q(rep, work, f"migrate --acknowledge-idle {RUN_IDLE}", "migrate", "--by", BY, "--acknowledge-idle", RUN_IDLE)
    q(rep, work, "migrate verify", "migrate", "verify")
    q(rep, work, "maintenance end", "maintenance", "end", "--by", BY)
    try: ac_b1_7(rep, src, work)
    except Exception as e: rep.check("AC-A-B1-7", "AC-A-B1-7 依序驗收執行", False, repr(e)[-3000:])
    rep.check("來源", "來源目錄執行前後逐檔 sha256 相同", snapshot(src) == src_snap, None)
    rep.data["finished_at"] = now(); rep.data["seconds"] = round(time.time() - t_all, 1); rep.data["failed"] = rep.failed
    a.report.write_text(json.dumps(rep.data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    for s in rep.data["steps"]: print(f"{'OK ' if s['ok'] else 'NG '} rc={s['rc']:<3} {s['seconds']:>7}s  {s['step']}")
    for c in rep.data["checks"]: print(f"{c['result']}  {c['ac']}  {c['check']}")
    print(f"失敗 {rep.failed} 項；報告：{a.report}")
    sys.exit(1 if rep.failed else 0)

# ---------------------------------------------------------------- 主流程
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--src", required=True, type=pathlib.Path); ap.add_argument("--work", required=True, type=pathlib.Path)
    ap.add_argument("--mode", required=True, choices=["acknowledge-idle", "cancel-run", "pre-cancel", "ac-b1-7"]); ap.add_argument("--real-data-checks", choices=["ack", "cancel"])
    ap.add_argument("--code-commit", help="程式不是 git 目錄（例如 git archive 匯出）時，記在報告中的程式版本")
    ap.add_argument("--report", required=True, type=pathlib.Path); a = ap.parse_args()
    src, work = a.src.resolve(), a.work.resolve()
    if work == src or src in work.parents or work in src.parents: sys.exit("工作目錄不能和來源目錄重疊")
    if work.exists() and any(work.iterdir()): sys.exit(f"工作目錄必須不存在或是空的：{work}")
    if a.mode == "ac-b1-7":
        if a.real_data_checks: sys.exit("--mode ac-b1-7 不和 --real-data-checks 併用")
        return main_ac_b1_7(a, src, work)
    rep = Report(a); t_all = time.time()
    rep.fact("code_commit", subprocess.run(["git", "-C", str(CODE), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip() or "(非 git 目錄)")
    src_snap = snapshot(src)
    rep.fact("src_files", len(src_snap)); rep.fact("inventory", inventory(src))
    # 複製（來源唯讀；複本改成可寫）
    t = time.time(); shutil.copytree(src, work, symlinks=True, dirs_exist_ok=True)
    for p in [work, *work.rglob("*")]:
        if not p.is_symlink(): p.chmod(p.stat().st_mode | stat.S_IWUSR)
    rep.fact("copy_seconds", round(time.time() - t, 2))
    base = schema_check(work); rep.fact("baseline_schema", {"checked": base["checked"], "failures": [{"path": f["path"], "error": f["errors"][0][:160]} for f in base["failures"]]})
    flags = []
    if a.mode == "pre-cancel":
        audit_before = sha_file(work / f"runs/{RUN_IDLE}/audit.log")
        q(rep, work, "S_pre run cancel RUN-20260914-001", "run", "cancel", RUN_IDLE, "--by", BY)
        evs = sorted((work / f"runs/{RUN_IDLE}/audit.d").glob("*.yaml"))
        rep.check("AC-09-45", "S_pre 先 run cancel：run 為 CANCELLED、只寫事件檔、audit.log 不變（標記寫入前不 render）",
                  load(work, f"runs/{RUN_IDLE}/run.yaml")["status"] == "CANCELLED" and sha_file(work / f"runs/{RUN_IDLE}/audit.log") == audit_before and len(evs) >= 1,
                  {"events": [e.name for e in evs]})
    else:
        flags = ["--acknowledge-idle" if a.mode == "acknowledge-idle" else "--cancel-run", RUN_IDLE]
    pre_snap = snapshot(work)
    q(rep, work, "maintenance start", "maintenance", "start", "--by", BY)
    if a.mode != "pre-cancel":
        s1 = snapshot(work)
        r = q(rep, work, "AC-09-46 migrate（不指定處理方式）", "migrate", "--by", BY, expect_rc=1)
        d = diff(s1, snapshot(work)); d["changed"] = [c for c in d["changed"] if c != "locks/qaos-operation.owner"]
        rep.check("AC-09-46", "RUNNING 的 run 沒有指定處理方式 → 拒絕，沒有任何寫入（連計畫都不寫）", r.returncode != 0 and RUN_IDLE in r.stderr and not d["added"] and not d["changed"] and not d["removed"], {"stderr": r.stderr[-300:], "diff": d})
    pre_migrate = snapshot(work)
    q(rep, work, f"migrate {' '.join(flags)}".strip(), "migrate", "--by", BY, *flags)
    q(rep, work, "migrate verify", "migrate", "verify")
    try: x, manifest = assert_migrated(rep, src, work, src_snap, a.mode, "X", base_failures=base["failures"])
    except Exception as e: rep.check("AC-A-B1-4", "X 的斷言執行", False, repr(e)); x = load(work, "artifacts/requirements/_migration.yaml")["migrate_op_id"] if (work / "artifacts/requirements/_migration.yaml").exists() else None
    if x:
        q(rep, work, "migrate rollback", "migrate", "rollback", "--op", x, "--by", BY)
        q(rep, work, "migrate verify --rolled-back", "migrate", "verify", "--rolled-back")
        assert_rolled_back(rep, work, src_snap, pre_migrate, x, "R")
        r = q(rep, work, "AC-09-63① 相同請求重送 migrate（不加 --new-request）", "migrate", "--by", BY, *flags, expect_rc=1)
        rep.check("AC-09-63", "rollback 後以相同參數重送 migrate → 拒絕並提示 --new-request", r.returncode != 0 and "--new-request" in r.stderr, r.stderr[-300:])
        q(rep, work, "migrate --new-request", "migrate", "--by", BY, *flags, "--new-request")
        q(rep, work, "migrate verify（Y）", "migrate", "verify")
        try:
            y, my = assert_migrated(rep, src, work, src_snap, a.mode, "Y", full=False)
            rep.check("AC-09-63", "重新移轉產生新 op Y（≠ X）；Y 的清單不含 X 的稽核物", y != x and not any(x in e["path"] for k in ("restore", "remove") for e in my[k]), {"x": x, "y": y})
        except Exception as e: rep.check("AC-A-B1-4", "Y 的斷言執行", False, repr(e))
    q(rep, work, "maintenance end", "maintenance", "end", "--by", BY)
    if a.real_data_checks:
        try: real_data_checks(rep, src, work, a.real_data_checks)
        except Exception as e: rep.check("真實資料", "真實資料驗收執行", False, repr(e))
    rep.data["finished_at"] = now(); rep.data["seconds"] = round(time.time() - t_all, 1); rep.data["failed"] = rep.failed
    a.report.write_text(json.dumps(rep.data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    for s in rep.data["steps"]: print(f"{'OK ' if s['ok'] else 'NG '} rc={s['rc']:<3} {s['seconds']:>7}s  {s['step']}")
    for c in rep.data["checks"]: print(f"{c['result']}  {c['ac']}  {c['check']}")
    print(f"失敗 {rep.failed} 項；報告：{a.report}")
    sys.exit(1 if rep.failed else 0)

if __name__ == "__main__": main()
