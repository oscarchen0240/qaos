"""spec 版本的寫入指令與讀取規則（需求 A 第 2 章 FIX-01、FIX-02；附錄 A 2-1～2-11）。

- `spec import`：外部來源 `source`、同 SPEC 重複 hash 拒絕、跨 SPEC 重複 hash 警告、外部檔就地修改、換行正規化、title 空白警告。
- `spec reference add|remove|declare-empty`：只能由人宣告；每次追加一筆 `reference_declarations`、`decl_rev` 加一。
- `spec metadata upgrade`：只補 legacy 條目缺少的 `source`、`analysis_policy`；追加 `metadata_history`。
- 讀取預設值：缺 `references_status` 視為 `undeclared`，缺 `analysis_policy` 視為 `analyze`。
所有寫入都經過 executor（operation.py）。"""
import re, sys, pathlib
from . import store, schema, operation

class SpecError(ValueError):
    pass

# ---------------------------------------------------------------- 讀取
def spec_path(spec_id: str) -> pathlib.Path | None:
    d = store.spec_dir(spec_id)
    return d / "spec.yaml" if d else None

def find_entry(spec_id: str, version: str) -> tuple[pathlib.Path, dict, dict]:
    """回傳 (spec.yaml 路徑, spec, 版本條目)；不存在 → SpecError。"""
    p = spec_path(spec_id)
    if p is None: raise SpecError(f"Spec {spec_id} 不存在")
    spec = store.load(p)
    entry = next((v for v in spec["versions"] if v["spec_version"] == str(version)), None)
    if entry is None: raise SpecError(f"{spec_id}@{version} 不存在（有：{[v['spec_version'] for v in spec['versions']]}）")
    return p, spec, entry

def references_status(entry: dict) -> str:
    return entry.get("references_status", "undeclared")

def analysis_policy(entry: dict) -> str:
    return entry.get("analysis_policy", "analyze")

def decl_rev(entry: dict) -> int:
    return max((d["decl_rev"] for d in entry.get("reference_declarations") or []), default=0)

def verify_pin(spec_id: str, version: str, content_hash: str | None = None) -> dict:
    """SpecPin 驗證：版本存在，content_hash 等於 spec.yaml 登記值與實體檔 sha256（給了 content_hash 時也要相等）。回傳 SpecPin。"""
    p, _, entry = find_entry(spec_id, version)
    f = p.parent / entry["file"]
    if not store.exists(f): raise SpecError(f"{spec_id}@{version} 的實體檔 {entry['file']} 不存在")
    actual = store.sha256_file(f)
    if actual != entry["content_hash"]: raise SpecError(f"{spec_id}@{version} 的實體檔 sha256 和 spec.yaml 登記值不符")
    if content_hash is not None and content_hash != entry["content_hash"]: raise SpecError(f"{spec_id}@{version} 的 content_hash 和登記值不符")
    return {"spec_id": spec_id, "spec_version": str(version), "content_hash": entry["content_hash"]}

def parse_pin(text: str) -> tuple[str, str]:
    m = re.fullmatch(r"(SPEC-[A-Z0-9]+-[0-9]{3,})@([0-9]+\.[0-9]+)", text or "")
    if not m: raise SpecError(f"格式應為 <spec_id>@<版本>：{text!r}")
    return m.group(1), m.group(2)

def require_analyzable(spec_id: str, version: str, entry_label: str):
    """reference_only 的版本不能當任何 run 的分析目標（第 2 章 §3.4）。"""
    _, _, entry = find_entry(spec_id, version)
    if analysis_policy(entry) == "reference_only":
        raise SpecError(f"{spec_id}@{version} 是 reference_only（只當參考文件），不能作為 {entry_label}")

def normalize_title(text: str | None) -> str:
    """名稱正規化（第 2 章 §4.2）：全形轉半形、去除所有空白（含全形空白）、轉小寫。"""
    out = []
    for ch in text or "":
        c = ord(ch)
        if c == 0x3000: ch = " "
        elif 0xFF01 <= c <= 0xFF5E: ch = chr(c - 0xFEE0)
        out.append(ch)
    return re.sub(r"\s+", "", "".join(out)).lower()

def require_human(by: str):
    """「只能由人」的 actor 契約檢查（附錄 A 2-2）：不是身分驗證，只拒絕 system 與 agent-*。"""
    if not by or not by.strip() or by == "system" or by.startswith("agent-"):
        raise SpecError(f"這個指令只能由人執行（--by {by!r} 不接受 system 或 agent-*）")

def _save(p, spec):
    errs = schema.errors(spec, "spec/spec.schema.json")
    if errs: raise SpecError("spec.yaml 不符 schema：" + "; ".join(errs))
    store.save(p, spec)

def _op_id() -> str:
    return store.capturing().op_id

# ---------------------------------------------------------------- spec import
def _import_request(file, spec_id, version, product, area, **kw):
    data = pathlib.Path(file).read_bytes()
    pkg = kw.get("package_file")
    return {"targets": {"spec_pins": [f"{spec_id}@{version}"]}, "params": operation.normalize({"product": product, "area": area, **{k: v for k, v in kw.items() if k != "package_file"}}),
            "inputs": {"source_sha256": store.sha256_bytes(data), **({"package_sha256": store.sha256_bytes(pathlib.Path(pkg).read_bytes())} if pkg else {})}}

def _warn(msg: str):
    print(f"警告：{msg}", file=sys.stderr)

@operation.operation("spec_import", request=_import_request)
def spec_import(file, spec_id, version, product, area, title=None, area_title=None, source=None, change_summary=None, supersede=False, by="human",
                package=None, package_file=None, external_filename=None, external_version=None, external_effective_date=None, external_commit=None,
                analysis_policy_value=None):
    """Human 匯入 Spec 版本：複製 markdown 到 specs/<product>/<area>/<spec_id>/v<ver>.md，登記 hash 與外部來源。"""
    if analysis_policy_value not in (None, "analyze", "reference_only"): raise SpecError(f"--analysis-policy 只能是 analyze 或 reference_only：{analysis_policy_value!r}")
    src = pathlib.Path(file).resolve(); raw = src.read_bytes()
    text = raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")          # 換行正規化：content_hash 記錄存檔後的內容
    content_hash = store.sha256_text(text); source_sha = store.sha256_bytes(raw)
    d = f"specs/{product}/{area}/{spec_id}"
    areas = store.load(f"specs/{product}/areas.yaml") if store.exists(f"specs/{product}/areas.yaml") else {"product": product, "areas": {}}
    if area not in areas["areas"]: areas["areas"][area] = {"title": area_title or area}; store.save(f"specs/{product}/areas.yaml", areas)
    spec = store.load(f"{d}/spec.yaml") if store.exists(f"{d}/spec.yaml") else {"spec_id": spec_id, "product": product, "functional_area": area, "title": title or spec_id, "versions": []}
    if any(v["spec_version"] == version for v in spec["versions"]): raise SpecError(f"{spec_id} v{version} 已存在（Spec 版本不可覆蓋，請用新版本號）")
    # 規則 1、2：重複內容
    same = [v["spec_version"] for v in spec["versions"] if v["content_hash"] == content_hash]
    if same: raise SpecError(f"{spec_id} 已有內容相同的版本 v{same[0]}（content_hash {content_hash[:12]}…），不重複匯入")
    for p in store.glob("specs/*/*/*/spec.yaml"):
        other = store.load(p)
        if other["spec_id"] == spec_id: continue
        for v in other["versions"]:
            if v["content_hash"] == content_hash: _warn(f"{other['spec_id']}@{v['spec_version']} 的內容和本次匯入相同（content_hash {content_hash[:12]}…）")
    # 規則 3：外部檔就地修改（legacy 條目沒有 source，不參與比對）
    if external_filename:
        changed = [v["spec_version"] for v in spec["versions"] if (v.get("source") or {}).get("external_filename") == external_filename and v["content_hash"] != content_hash]
        if changed:
            print(f"提示：外部檔就地修改——{spec_id} 已以不同內容匯入過同名外部檔 {external_filename}（v{', v'.join(changed)}）", file=sys.stderr)
            if not (change_summary or "").strip(): raise SpecError("外部檔就地修改時 --change-summary 必填")
    # 規則 4：正規化
    if source_sha != content_hash: print(f"提示：匯入時做了換行正規化；content_hash {content_hash[:12]}… 記錄存檔後的內容，source_bytes_sha256 {source_sha[:12]}… 記錄原檔", file=sys.stderr)
    src_meta = {k: v for k, v in {"package_name": package, "package_sha256": store.sha256_bytes(pathlib.Path(package_file).read_bytes()) if package_file else None,
                "external_filename": external_filename, "external_version_label": external_version, "external_effective_date": external_effective_date,
                "external_commit": {"value": external_commit, "claimed": True} if external_commit else None, "source_bytes_sha256": source_sha}.items() if v is not None}
    fname = f"v{version}.md"; store.write_text(f"{d}/{fname}", text)
    for v in spec["versions"]:
        if v["status"] != "SUPERSEDED": v["status"] = "SUPERSEDED" if supersede else v["status"]
    spec["versions"].append({k: v for k, v in {"spec_version": version, "file": fname, "content_hash": content_hash, "source_uri": source or str(src),
                            "imported_by": by, "imported_at": store.now(), "status": "IMPORTED", "change_summary": change_summary, "source": src_meta,
                            "analysis_policy": analysis_policy_value}.items() if v is not None})
    _save(f"{d}/spec.yaml", spec); store.audit(None, by, "IMPORT_SPEC", f"{spec_id}@{version}")
    # 規則 6：title 正規化後為空 → 只警告（附錄 A 2-9）
    if not normalize_title(spec["title"]):
        _warn("title 正規化後為空，文件名稱比對不會使用這個 title")
        store.audit(None, by, "WARN_TITLE_EMPTY", f"{spec_id}@{version}")
    return f"{spec_id}@{version} imported → {d}/{fname}"

# ---------------------------------------------------------------- spec reference
def _declare(target: str, action: str, by: str, new_refs: list, status: str, reason: str | None):
    sid, ver = parse_pin(target)
    p, spec, entry = find_entry(sid, ver)
    verify_pin(sid, ver)
    rev = decl_rev(entry) + 1
    rec = {k: v for k, v in {"decl_rev": rev, "action": action, "references": new_refs, "references_status": status, "reason": reason,
                             "by": by, "at": store.now(), "op_id": _op_id()}.items() if v is not None}
    entry.setdefault("reference_declarations", []).append(rec)
    entry["references"] = new_refs; entry["references_status"] = status
    _save(p, spec)
    store.audit(None, by, "DECLARE_SPEC_REFERENCES", f"{sid}@{ver} decl_rev={rev} {action} {status}")
    return {"spec": f"{sid}@{ver}", "decl_rev": rev, "references_status": status, "references": new_refs}

@operation.operation("spec_reference_add")
def reference_add(target: str, ref: str, role: str, by: str, scope: str | None = None):
    require_human(by)
    if role not in ("normative", "informative"): raise SpecError(f"--role 只能是 normative 或 informative：{role!r}")
    sid, ver = parse_pin(target); rsid, rver = parse_pin(ref)
    if (sid, ver) == (rsid, rver): raise SpecError("不能宣告引用自己")
    _, _, entry = find_entry(sid, ver)
    pin = verify_pin(rsid, rver)
    cur = list(entry.get("references") or [])
    if any((r["spec_id"], r["spec_version"]) == (rsid, rver) for r in cur): raise SpecError(f"{sid}@{ver} 已宣告引用 {ref}")
    new = cur + [{**pin, "role": role, **({"scope": scope} if scope else {})}]
    return _declare(target, "add", by, new, "declared", None)

@operation.operation("spec_reference_remove")
def reference_remove(target: str, ref: str, by: str, reason: str | None = None):
    require_human(by)
    sid, ver = parse_pin(target); rsid, rver = parse_pin(ref)
    _, _, entry = find_entry(sid, ver)
    cur = list(entry.get("references") or [])
    new = [r for r in cur if (r["spec_id"], r["spec_version"]) != (rsid, rver)]
    if len(new) == len(cur): raise SpecError(f"{sid}@{ver} 沒有宣告引用 {ref}")
    if not new and not (reason or "").strip(): raise SpecError("移除最後一個引用時必須帶 --reason（狀態會成為 declared_empty）")
    return _declare(target, "remove", by, new, "declared" if new else "declared_empty", (reason or "").strip() or None)

@operation.operation("spec_reference_declare_empty")
def reference_declare_empty(target: str, reason: str, by: str):
    require_human(by)
    if not (reason or "").strip(): raise SpecError("declare-empty 必須附 --reason")
    sid, ver = parse_pin(target)
    _, _, entry = find_entry(sid, ver)
    if entry.get("references"): raise SpecError(f"{sid}@{ver} 目前有 {len(entry['references'])} 個引用；請先以 spec reference remove 移除")
    return _declare(target, "declare_empty", by, [], "declared_empty", reason.strip())

# ---------------------------------------------------------------- spec metadata upgrade
def _uses_as_target(spec_id: str, version: str) -> list[str]:
    """以該版本為目標或依據的物件（附錄 A 2-8）：run 的目標 spec 版本、需求模型（RM）、TC 版本的 spec pin。不含引用閉包。"""
    hits = []
    for p in store.glob("runs/*/run.yaml"):
        run = store.load(p); inp = run.get("input") or {}
        vers = {str(inp.get(k)) for k in ("spec_version", "from_version", "to_version") if inp.get(k)}
        if inp.get("spec_id") == spec_id and str(version) in vers: hits.append(run["run_id"])
        elif inp.get("manual_record_id") and store.exists(f"testcases/manual/{inp['manual_record_id']}.yaml"):
            h = store.load(f"testcases/manual/{inp['manual_record_id']}.yaml").get("spec_hint") or {}
            if h.get("spec_id") == spec_id and str(h.get("spec_version")) == str(version): hits.append(run["run_id"])
    if store.exists(store.requirements_path(spec_id, version)): hits.append(f"RM {spec_id}@{version}")
    for p in store.glob("testcases/versions/*/v*.yaml"):
        tv = store.load(p)
        if tv.get("spec_id") == spec_id and str(tv.get("spec_version")) == str(version): hits.append(f"{tv.get('testcase_id')} v{tv.get('version')}")
    return hits

def _upgrade_request(target, by, reason, **kw):
    orig = kw.pop("original_file", None); pkg = kw.pop("package_file", None)
    return {"targets": {"spec_pins": [target]}, "params": operation.normalize({"by": by, "reason": reason, **kw}),
            "inputs": {**({"original_sha256": store.sha256_bytes(pathlib.Path(orig).read_bytes())} if orig else {}),
                       **({"package_sha256": store.sha256_bytes(pathlib.Path(pkg).read_bytes())} if pkg else {})}}

@operation.operation("spec_metadata_upgrade", request=_upgrade_request)
def metadata_upgrade(target: str, by: str, reason: str, analysis_policy_value: str | None = None, original_file=None, note: str | None = None,
                     package=None, package_file=None, external_filename=None, external_version=None, external_effective_date=None, external_commit=None):
    """只補 legacy 條目缺少的欄位（第 2 章 §4.3）；已有值的欄位不可經此指令改寫。"""
    require_human(by)
    if not (reason or "").strip(): raise SpecError("metadata upgrade 必須附 --reason")
    sid, ver = parse_pin(target)
    p, spec, entry = find_entry(sid, ver)
    file_sha_before = store.sha256_file(p.parent / entry["file"])
    changes = {}
    src_given = any(x is not None for x in (original_file, package, package_file, external_filename, external_version, external_effective_date, external_commit))
    if src_given:
        if "source" in entry: raise SpecError(f"{target} 已有 source，不能經 metadata upgrade 改寫")
        if original_file is None: raise SpecError("補 source 時必須以 --original-file 提供原檔，由指令當場重算 source_bytes_sha256")
        src_sha = store.sha256_bytes(pathlib.Path(original_file).read_bytes())
        if src_sha != entry["content_hash"] and not (note or "").strip():
            raise SpecError("原檔 sha256 和 content_hash 不同，必須以 --note 說明差異（例如匯入時的換行正規化）")
        new_src = {k: v for k, v in {"package_name": package, "package_sha256": store.sha256_bytes(pathlib.Path(package_file).read_bytes()) if package_file else None,
                   "external_filename": external_filename, "external_version_label": external_version, "external_effective_date": external_effective_date,
                   "external_commit": {"value": external_commit, "claimed": True} if external_commit else None, "source_bytes_sha256": src_sha}.items() if v is not None}
        changes["source"] = {"old": None, "new": new_src}; entry["source"] = new_src
    if analysis_policy_value is not None:
        if analysis_policy_value not in ("analyze", "reference_only"): raise SpecError(f"--analysis-policy 只能是 analyze 或 reference_only：{analysis_policy_value!r}")
        if "analysis_policy" in entry: raise SpecError(f"{target} 已有 analysis_policy，不能經 metadata upgrade 改寫")
        if analysis_policy_value == "reference_only":
            used = _uses_as_target(sid, ver)
            if used: raise SpecError(f"{target} 已被當作目標或依據（{', '.join(used[:5])}），不能設為 reference_only")
        changes["analysis_policy"] = {"old": None, "new": analysis_policy_value}; entry["analysis_policy"] = analysis_policy_value
    if not changes: raise SpecError("沒有要補的欄位（metadata upgrade 只補 legacy 條目缺少的 source、analysis_policy）")
    entry.setdefault("metadata_history", []).append({k: v for k, v in {"at": store.now(), "by": by, "reason": reason.strip(), "note": (note or "").strip() or None,
                                                                       "op_id": _op_id(), "changes": changes}.items() if v is not None})
    _save(p, spec)
    if store.sha256_file(p.parent / entry["file"]) != file_sha_before: raise SpecError("內部錯誤：metadata upgrade 不能改動版本內容")
    store.audit(None, by, "UPGRADE_SPEC_METADATA", f"{target} {', '.join(changes)}")
    return {"spec": target, "changes": sorted(changes)}
