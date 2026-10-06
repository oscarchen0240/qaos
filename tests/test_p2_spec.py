"""P2：spec 引用宣告、參考型 spec、外部來源、spec import 規則與 metadata 升級（需求 A 第 2 章 FIX-01、FIX-02；附錄 A 2-1～2-11）。

每個案例使用獨立的暫存 root，以子程序執行 QAOS CLI（正式流程）。
legacy 條目（沒有新欄位、沒有 source）以「直接寫入舊格式的 spec.yaml 與 v<ver>.md」建立，模擬新程式部署前就存在的資料；
這是 legacy fixture，不是對 QAOS 業務狀態的手改。實體檔竄改案例另外標示。"""
import pathlib, yaml, pytest
from tests import p1_util as U

def write_md(tmp_path, name, text, crlf=False):
    p = tmp_path / name
    p.write_bytes(text.replace("\n", "\r\n").encode() if crlf else text.encode())
    return p

def imp(root, file, sid, ver, *extra, check=True):
    return U.q(root, "spec", "import", file, "--spec-id", sid, "--version", ver, "--product", "demo", "--area", "AUTH", "--by", "oscar", *extra, check=check)

def entry(root, sid, ver):
    spec = U.load(root, f"specs/demo/AUTH/{sid}/spec.yaml")
    return next(v for v in spec["versions"] if v["spec_version"] == ver)

def spec_bytes(root, sid):
    return (pathlib.Path(root) / f"specs/demo/AUTH/{sid}/spec.yaml").read_bytes()

def legacy_spec(root, sid="SPEC-LEG-001", ver="1.0", text="# 舊規格\n\n舊內容。\n"):
    """legacy fixture：舊程式匯入的 spec（版本條目沒有 references_status、analysis_policy、source 等新欄位）。"""
    import hashlib
    d = pathlib.Path(root) / f"specs/demo/AUTH/{sid}"; d.mkdir(parents=True)
    (d / f"v{ver}.md").write_text(text, encoding="utf-8")
    spec = {"spec_id": sid, "product": "demo", "functional_area": "AUTH", "title": "舊規格",
            "versions": [{"spec_version": ver, "file": f"v{ver}.md", "content_hash": hashlib.sha256(text.encode()).hexdigest(), "source_uri": "legacy.md",
                          "imported_by": "oscar", "imported_at": "2026-09-01T00:00:00Z", "status": "IMPORTED"}]}
    (d / "spec.yaml").write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
    areas = pathlib.Path(root) / "specs/demo/areas.yaml"
    if not areas.exists(): areas.write_text(yaml.safe_dump({"product": "demo", "areas": {"AUTH": {"title": "AUTH"}}}), encoding="utf-8")
    return sid, ver

def two_specs(root, tmp_path):
    imp(root, write_md(tmp_path, "a.md", "# A\n\n甲。\n"), "SPEC-A-001", "1.0")
    imp(root, write_md(tmp_path, "b.md", "# B\n\n乙。\n"), "SPEC-B-001", "1.0")

def runs(root):
    return sorted(p.name for p in (pathlib.Path(root) / "runs").glob("RUN-*")) if (pathlib.Path(root) / "runs").is_dir() else []

# ---------------------------------------------------------------- FIX-01 引用宣告
def test_ac_01_1_reference_to_missing_or_mismatched_version_is_refused(tmp_path):
    root = U.mkroot(); two_specs(root, tmp_path); before = spec_bytes(root, "SPEC-A-001")
    r = U.q(root, "spec", "reference", "add", "SPEC-A-001@1.0", "--ref", "SPEC-B-001@9.9", "--role", "normative", "--by", "oscar")
    assert r.returncode != 0 and "不存在" in r.stderr, r.stderr
    (pathlib.Path(root) / "specs/demo/AUTH/SPEC-B-001/v1.0.md").write_text("被改過\n", encoding="utf-8")         # 竄改反例：實體檔和登記值不符
    r = U.q(root, "spec", "reference", "add", "SPEC-A-001@1.0", "--ref", "SPEC-B-001@1.0", "--role", "normative", "--by", "oscar")
    assert r.returncode != 0 and "不符" in r.stderr, r.stderr
    assert spec_bytes(root, "SPEC-A-001") == before

def test_ac_01_2_legacy_spec_passes_schema_and_reads_as_undeclared():
    root = U.mkroot(); sid, ver = legacy_spec(root)
    code = f"""
from tools.qaos import schema, store, spec_ops
spec = store.load("specs/demo/AUTH/{sid}/spec.yaml"); e = spec["versions"][0]
print(schema.errors(spec, "spec/spec.schema.json"), spec_ops.references_status(e), spec_ops.analysis_policy(e), spec_ops.decl_rev(e))
"""
    assert U.py(root, code).stdout.strip() == "[] undeclared analyze 0"

def test_ac_01_2_existing_repo_specs_pass_new_schema():
    """主資料夾既有的 spec.yaml（唯讀）全部通過新 schema。"""
    import json
    repo = pathlib.Path("/Users/oscar/Desktop/qa-agent-os/specs")
    files = sorted(repo.glob("*/*/*/spec.yaml"))
    if not files: pytest.skip("主資料夾沒有 spec 資料")
    root = U.mkroot()
    code = f"""
import yaml, json
from tools.qaos import schema
bad = {{}}
for f in {json.dumps([str(f) for f in files])}:
    errs = schema.errors(yaml.safe_load(open(f, encoding="utf-8")), "spec/spec.schema.json")
    if errs: bad[f] = errs[:2]
print(json.dumps(bad, ensure_ascii=False))
"""
    assert U.py(root, code).stdout.strip() == "{}"

def test_ac_01_3_add_remove_append_declarations_and_keep_content(tmp_path):
    root = U.mkroot(); two_specs(root, tmp_path)
    md = (pathlib.Path(root) / "specs/demo/AUTH/SPEC-A-001/v1.0.md").read_bytes(); e0 = entry(root, "SPEC-A-001", "1.0")
    U.q(root, "spec", "reference", "add", "SPEC-A-001@1.0", "--ref", "SPEC-B-001@1.0", "--role", "normative", "--scope", "§2", "--by", "oscar", check=True)
    e1 = entry(root, "SPEC-A-001", "1.0"); d1 = e1["reference_declarations"][0]
    assert e1["references_status"] == "declared" and d1["decl_rev"] == 1 and d1["action"] == "add"
    assert e1["references"] == [{"spec_id": "SPEC-B-001", "spec_version": "1.0", "content_hash": entry(root, "SPEC-B-001", "1.0")["content_hash"], "role": "normative", "scope": "§2"}]
    U.q(root, "spec", "reference", "remove", "SPEC-A-001@1.0", "--ref", "SPEC-B-001@1.0", "--reason", "誤宣告", "--by", "oscar", check=True)
    e2 = entry(root, "SPEC-A-001", "1.0")
    assert [d["decl_rev"] for d in e2["reference_declarations"]] == [1, 2] and e2["reference_declarations"][0] == d1   # 舊紀錄不變
    assert e2["references"] == [] and e2["references_status"] == "declared_empty" and e2["reference_declarations"][1]["reason"] == "誤宣告"
    assert (e2["content_hash"], e2["file"]) == (e0["content_hash"], e0["file"])
    assert (pathlib.Path(root) / "specs/demo/AUTH/SPEC-A-001/v1.0.md").read_bytes() == md
    U.q(root, "spec", "reference", "add", "SPEC-A-001@1.0", "--ref", "SPEC-B-001@1.0", "--role", "informative", "--by", "oscar", check=True)
    e3 = entry(root, "SPEC-A-001", "1.0")
    assert e3["references_status"] == "declared" and [d["decl_rev"] for d in e3["reference_declarations"]] == [1, 2, 3]   # declared_empty 之後 add（附錄 A 2-4）

def test_reference_status_transitions_and_rules(tmp_path):
    """附錄 A 2-1～2-4：移除最後一個引用要 --reason；有引用時不能 declare-empty；不能重複宣告、不能引用自己；循環引用允許。"""
    root = U.mkroot(); two_specs(root, tmp_path)
    U.q(root, "spec", "reference", "add", "SPEC-A-001@1.0", "--ref", "SPEC-B-001@1.0", "--role", "normative", "--by", "oscar", check=True)
    before = spec_bytes(root, "SPEC-A-001")
    for cmd, msg in ((["remove", "SPEC-A-001@1.0", "--ref", "SPEC-B-001@1.0"], "--reason"),
                     (["declare-empty", "SPEC-A-001@1.0", "--reason", "x"], "先以 spec reference remove"),
                     (["add", "SPEC-A-001@1.0", "--ref", "SPEC-B-001@1.0", "--role", "normative", "--new-request"], "已宣告"),   # 新請求（同請求重送會回報已完成）
                     (["add", "SPEC-A-001@1.0", "--ref", "SPEC-A-001@1.0", "--role", "normative"], "自己"),
                     (["remove", "SPEC-A-001@1.0", "--ref", "SPEC-C-001@1.0", "--reason", "x"], "沒有宣告")):
        r = U.q(root, "spec", "reference", *cmd, "--by", "oscar"); assert r.returncode != 0 and msg in r.stderr, (cmd, r.stderr)
    assert spec_bytes(root, "SPEC-A-001") == before
    U.q(root, "spec", "reference", "add", "SPEC-B-001@1.0", "--ref", "SPEC-A-001@1.0", "--role", "informative", "--by", "oscar", check=True)   # 循環
    r = U.q(root, "spec", "reference", "declare-empty", "SPEC-B-001@1.0", "--reason", "x", "--by", "oscar"); assert r.returncode != 0

@pytest.mark.parametrize("by", ["system", "agent-spec-analyst"])
def test_reference_and_upgrade_only_by_human(by, tmp_path):
    """附錄 A 2-2：--by 是 system 或 agent-* → 拒絕（actor 契約檢查，不是身分驗證）。"""
    root = U.mkroot(); two_specs(root, tmp_path); sid, ver = legacy_spec(root)
    before = U.snapshot(root)
    for cmd in (["spec", "reference", "add", "SPEC-A-001@1.0", "--ref", "SPEC-B-001@1.0", "--role", "normative"],
                ["spec", "reference", "remove", "SPEC-A-001@1.0", "--ref", "SPEC-B-001@1.0", "--reason", "x"],
                ["spec", "reference", "declare-empty", "SPEC-A-001@1.0", "--reason", "x"],
                ["spec", "metadata", "upgrade", f"{sid}@{ver}", "--analysis-policy", "analyze", "--reason", "x"]):
        r = U.q(root, *cmd, "--by", by); assert r.returncode != 0 and "只能由人" in r.stderr, (cmd, r.stderr)
    assert U.diff(before, U.snapshot(root)) == {"added": [], "removed": [], "changed": []}

def test_ac_01_5_declare_empty_requires_reason(tmp_path):
    root = U.mkroot(); two_specs(root, tmp_path); before = spec_bytes(root, "SPEC-A-001")
    r = U.q(root, "spec", "reference", "declare-empty", "SPEC-A-001@1.0", "--by", "oscar"); assert r.returncode != 0 and "--reason" in r.stderr
    r = U.q(root, "spec", "reference", "declare-empty", "SPEC-A-001@1.0", "--reason", "  ", "--by", "oscar"); assert r.returncode != 0 and "reason" in r.stderr
    assert spec_bytes(root, "SPEC-A-001") == before
    U.q(root, "spec", "reference", "declare-empty", "SPEC-A-001@1.0", "--reason", "本規格不依賴其他文件", "--by", "oscar", check=True)
    e = entry(root, "SPEC-A-001", "1.0")
    assert e["references_status"] == "declared_empty" and e["reference_declarations"] == [{**e["reference_declarations"][0], "decl_rev": 1, "action": "declare_empty", "references": [], "reason": "本規格不依賴其他文件"}]

# ---------------------------------------------------------------- reference_only 的 7 個拒絕入口
def _refonly_root(tmp_path):
    root = U.mkroot()
    imp(root, write_md(tmp_path, "manual.md", "# 操作手冊\n\n手冊內容。\n"), "SPEC-MAN-001", "1.0", "--analysis-policy", "reference_only")
    imp(root, write_md(tmp_path, "an.md", "# 可分析\n\n內容。\n"), "SPEC-MAN-001", "2.0")              # 同一 SPEC 的 analyze 版本（from／to 的另一端）
    return root

def _manual(root, *spec):
    r = U.q(root, "manual", "new", "--title", "t", "--product", "demo", "--area", "AUTH", "--step", "s", "--observed", "o", "--outcome", "pass", *spec, "--by", "oscar", check=True)
    return r.stdout.split()[0]

ENTRIES = ["spec_to_testcase", "change_impact_from", "change_impact_to", "spec_to_bug", "testcase_revision", "manual_inputs", "manual_spec_hint"]

@pytest.mark.parametrize("entry_", ENTRIES)
def test_ac_01_4_reference_only_refused_at_each_entry(entry_, tmp_path):
    root = _refonly_root(tmp_path)
    R = ["--input", "spec_id=SPEC-MAN-001"]
    if entry_ == "spec_to_testcase": args = ["spec-to-testcase", *R, "--input", "spec_version=1.0"]
    elif entry_ == "change_impact_from": args = ["spec-change-impact", *R, "--input", "from_version=1.0", "--input", "to_version=2.0"]
    elif entry_ == "change_impact_to": args = ["spec-change-impact", *R, "--input", "from_version=2.0", "--input", "to_version=1.0"]
    elif entry_ == "spec_to_bug":
        evd = U.q(root, "evidence", "add", "--type", "log", "--inline", "x", "--by", "oscar", check=True).stdout.strip()
        args = ["spec-to-bug", *R, "--input", "spec_version=1.0", "--input", f'evidence_ids=["{evd}"]']
    elif entry_ == "testcase_revision":   # 正式流程中 TC 不可能釘在 reference_only 版本上；這裡驗 inputs 帶入的 spec（engine 另外也核對 TC 版本的 spec pin）
        args = ["testcase-revision", "--input", "testcase_id=TC-AUTH-001", "--input", "reason=r", *R, "--input", "spec_version=1.0"]
    elif entry_ == "manual_inputs": args = ["manual-test-to-regression", "--input", f"manual_record_id={_manual(root)}", *R, "--input", "spec_version=1.0"]
    else: args = ["manual-test-to-regression", "--input", f"manual_record_id={_manual(root, '--spec-id', 'SPEC-MAN-001', '--spec-version', '1.0')}"]
    before = U.snapshot(root)
    r = U.q(root, "run", "new", *args, "--by", "oscar"); assert r.returncode != 0 and "reference_only" in r.stderr, r.stderr
    assert runs(root) == [] and U.diff(before, U.snapshot(root)) == {"added": [], "removed": [], "changed": []}

def test_reference_only_can_be_referenced_but_analyze_version_runs(tmp_path):
    root = _refonly_root(tmp_path); imp(root, write_md(tmp_path, "t.md", "# 目標\n\n內容。\n"), "SPEC-T-001", "1.0")
    U.q(root, "spec", "reference", "add", "SPEC-T-001@1.0", "--ref", "SPEC-MAN-001@1.0", "--role", "informative", "--by", "oscar", check=True)
    U.q(root, "run", "new", "spec-to-testcase", "--input", "spec_id=SPEC-MAN-001", "--input", "spec_version=2.0", "--by", "oscar", check=True)

# ---------------------------------------------------------------- FIX-02 spec import
def test_ac_02_1_duplicate_content(tmp_path):
    root = U.mkroot(); f = write_md(tmp_path, "a.md", "# A\n\n甲。\n"); imp(root, f, "SPEC-A-001", "1.0")
    before = U.snapshot(root)
    r = imp(root, f, "SPEC-A-001", "1.1", check=False); assert r.returncode != 0 and "v1.0" in r.stderr, r.stderr   # (a) 同 SPEC → 拒絕並指出既有版本
    assert U.diff(before, U.snapshot(root)) == {"added": [], "removed": [], "changed": []}
    r = imp(root, f, "SPEC-B-001", "1.0"); assert "警告" in r.stderr and "SPEC-A-001@1.0" in r.stderr                 # (b) 不同 SPEC → 成功＋警告

def test_ac_02_2_external_file_modified_in_place(tmp_path):
    root = U.mkroot()
    imp(root, write_md(tmp_path, "a1.md", "# A\n\n第一版。\n"), "SPEC-A-001", "1.0", "--external-filename", "A_spec_v01.md")
    f2 = write_md(tmp_path, "a2.md", "# A\n\n就地改過。\n"); before = U.snapshot(root)
    r = imp(root, f2, "SPEC-A-001", "1.1", "--external-filename", "A_spec_v01.md", check=False)
    assert r.returncode != 0 and "外部檔就地修改" in r.stderr and "--change-summary" in r.stderr, r.stderr
    r = imp(root, f2, "SPEC-A-001", "1.1", "--external-filename", "A_spec_v01.md", "--change-summary", "   ", check=False); assert r.returncode != 0
    assert U.diff(before, U.snapshot(root)) == {"added": [], "removed": [], "changed": []}
    r = imp(root, f2, "SPEC-A-001", "1.1", "--external-filename", "A_spec_v01.md", "--change-summary", "PM 直接改了外部檔")
    assert "外部檔就地修改" in r.stderr and entry(root, "SPEC-A-001", "1.1")["source"]["external_filename"] == "A_spec_v01.md"

def test_ac_02_3_crlf_normalization_records_both_hashes(tmp_path):
    import hashlib
    root = U.mkroot(); f = write_md(tmp_path, "crlf.md", "# A\n\n第一行。\n第二行。\n", crlf=True)
    r = imp(root, f, "SPEC-A-001", "1.0"); e = entry(root, "SPEC-A-001", "1.0")
    assert e["source"]["source_bytes_sha256"] == hashlib.sha256(f.read_bytes()).hexdigest()
    assert e["content_hash"] == hashlib.sha256((pathlib.Path(root) / "specs/demo/AUTH/SPEC-A-001/v1.0.md").read_bytes()).hexdigest()
    assert e["content_hash"] != e["source"]["source_bytes_sha256"] and "正規化" in r.stderr
    r = imp(root, write_md(tmp_path, "lf.md", "# B\n"), "SPEC-B-001", "1.0"); assert "正規化" not in r.stderr        # 相同時不提示

def test_ac_02_4_legacy_entry_reads_and_is_not_name_compared(tmp_path):
    root = U.mkroot(); sid, ver = legacy_spec(root)
    U.q(root, "run", "new", "spec-to-testcase", "--input", f"spec_id={sid}", "--input", f"spec_version={ver}", "--by", "oscar", check=True)   # 讀取正常
    r = imp(root, write_md(tmp_path, "legacy.md", "# 新內容\n"), sid, "1.1", "--external-filename", "legacy.md")                       # legacy 的 source_uri 同名也不比對
    assert r.returncode == 0 and "就地修改" not in r.stderr
    assert "source" not in entry(root, sid, ver)                                                                                         # 不自動回填

def test_source_fields_recorded(tmp_path):
    root = U.mkroot(); pkg = write_md(tmp_path, "pkg.zip", "zip-bytes")
    imp(root, write_md(tmp_path, "a.md", "# A\n"), "SPEC-A-001", "1.0", "--package", "紅包開發包", "--package-file", pkg, "--external-filename", "A.md",
        "--external-version", "v0.6", "--external-effective-date", "2026-09-29", "--external-commit", "abc123")
    src = entry(root, "SPEC-A-001", "1.0")["source"]
    assert src["package_name"] == "紅包開發包" and src["package_sha256"] == U.sha(pkg) and src["external_commit"] == {"value": "abc123", "claimed": True}
    assert src["external_version_label"] == "v0.6" and src["external_effective_date"] == "2026-09-29"

def test_ac_10a_57_blank_title_warns(tmp_path):
    root = U.mkroot()
    r = imp(root, write_md(tmp_path, "a.md", "# A\n"), "SPEC-A-001", "1.0", "--title", "　 ")
    assert r.returncode == 0 and "title 正規化後為空" in r.stderr
    log = (pathlib.Path(root) / "runs/_audit.log").read_text(); assert "WARN_TITLE_EMPTY" in log
    r = imp(root, write_md(tmp_path, "b.md", "# B\n"), "SPEC-B-001", "1.0", "--title", "Ｂ 規格"); assert "title" not in r.stderr

def test_title_normalization():
    root = U.mkroot()
    code = """
from tools.qaos.spec_ops import normalize_title as n
print([n("　 "), n(None), n(""), n("ＡＢＣ　ｄｅｆ"), n(" A b\\tC ")])
"""
    assert U.py(root, code).stdout.strip() == "['', '', '', 'abcdef', 'abc']"

# ---------------------------------------------------------------- FIX-02 metadata upgrade
def test_ac_02_5_metadata_upgrade_on_legacy(tmp_path):
    root = U.mkroot(); sid, ver = legacy_spec(root)
    md = pathlib.Path(root) / f"specs/demo/AUTH/{sid}/v{ver}.md"; md_bytes = md.read_bytes(); ch = entry(root, sid, ver)["content_hash"]
    orig = write_md(tmp_path, "orig.md", "# 舊規格\n\n舊內容。\n")
    U.q(root, "spec", "metadata", "upgrade", f"{sid}@{ver}", "--original-file", orig, "--external-filename", "legacy_v1.md", "--reason", "補來源", "--by", "oscar", check=True)
    e = entry(root, sid, ver)
    assert md.read_bytes() == md_bytes and e["content_hash"] == ch and len(e["metadata_history"]) == 1
    h = e["metadata_history"][0]; assert h["reason"] == "補來源" and h["by"] == "oscar" and h["changes"]["source"]["old"] is None
    assert e["source"] == {"external_filename": "legacy_v1.md", "source_bytes_sha256": ch}
    U.q(root, "spec", "metadata", "upgrade", f"{sid}@{ver}", "--analysis-policy", "analyze", "--reason", "補政策", "--by", "oscar", check=True)
    assert len(entry(root, sid, ver)["metadata_history"]) == 2

def test_metadata_upgrade_only_fills_missing(tmp_path):
    root = U.mkroot(); sid, ver = legacy_spec(root)
    imp(root, write_md(tmp_path, "n.md", "# 新\n"), "SPEC-N-001", "1.0")
    crlf = write_md(tmp_path, "o.md", "# 舊規格\n\n舊內容。\n", crlf=True)
    before = U.snapshot(root)
    cases = ((["SPEC-N-001@1.0", "--original-file", crlf], "已有 source"),                              # 新條目已有 source
             ([f"{sid}@{ver}", "--external-filename", "x.md"], "--original-file"),                         # 補 source 但沒給原檔
             ([f"{sid}@{ver}", "--original-file", crlf], "--note"),                                        # 原檔 hash 和 content_hash 不同、沒說明
             ([f"{sid}@{ver}"], "沒有要補的欄位"))
    for args, msg in cases:
        r = U.q(root, "spec", "metadata", "upgrade", *args, "--reason", "x", "--by", "oscar"); assert r.returncode != 0 and msg in r.stderr, (args, r.stderr)
    assert U.diff(before, U.snapshot(root)) == {"added": [], "removed": [], "changed": []}
    U.q(root, "spec", "metadata", "upgrade", f"{sid}@{ver}", "--original-file", crlf, "--note", "原檔是 CRLF", "--reason", "x", "--by", "oscar", check=True)
    assert entry(root, sid, ver)["metadata_history"][0]["note"] == "原檔是 CRLF"
    r = U.q(root, "spec", "metadata", "upgrade", f"{sid}@{ver}", "--original-file", crlf, "--note", "n", "--reason", "x", "--by", "oscar")
    assert r.returncode != 0 and "已有 source" in r.stderr

def test_ac_02_6_reference_only_refused_when_used_by_run(tmp_path):
    root = U.mkroot(); sid, ver = legacy_spec(root)
    U.q(root, "run", "new", "spec-to-testcase", "--input", f"spec_id={sid}", "--input", f"spec_version={ver}", "--by", "oscar", check=True)
    before = U.snapshot(root)
    r = U.q(root, "spec", "metadata", "upgrade", f"{sid}@{ver}", "--analysis-policy", "reference_only", "--reason", "x", "--by", "oscar")
    assert r.returncode != 0 and "RUN-" in r.stderr and "reference_only" in r.stderr, r.stderr
    assert U.diff(before, U.snapshot(root)) == {"added": [], "removed": [], "changed": []}

def test_ac_02_6_referenced_in_closure_only_is_allowed(tmp_path):
    """附錄 A 2-8：只出現在其他版本的引用閉包中，不算目標或依據。"""
    root = U.mkroot(); sid, ver = legacy_spec(root); imp(root, write_md(tmp_path, "t.md", "# T\n"), "SPEC-T-001", "1.0")
    U.q(root, "spec", "reference", "add", "SPEC-T-001@1.0", "--ref", f"{sid}@{ver}", "--role", "normative", "--by", "oscar", check=True)
    U.q(root, "spec", "metadata", "upgrade", f"{sid}@{ver}", "--analysis-policy", "reference_only", "--reason", "手冊", "--by", "oscar", check=True)

def test_ac_02_7_after_upgrade_to_reference_only_run_new_is_refused(tmp_path):
    root = U.mkroot(); sid, ver = legacy_spec(root)
    U.q(root, "spec", "metadata", "upgrade", f"{sid}@{ver}", "--analysis-policy", "reference_only", "--reason", "手冊", "--by", "oscar", check=True)
    r = U.q(root, "run", "new", "spec-to-testcase", "--input", f"spec_id={sid}", "--input", f"spec_version={ver}", "--by", "oscar")
    assert r.returncode != 0 and "reference_only" in r.stderr and runs(root) == []

# ---------------------------------------------------------------- 寫入指令經過 executor
def test_reference_add_is_an_operation_and_idempotent(tmp_path):
    root = U.mkroot(); two_specs(root, tmp_path)
    args = ["spec", "reference", "add", "SPEC-A-001@1.0", "--ref", "SPEC-B-001@1.0", "--role", "normative", "--by", "oscar"]
    assert U.q(root, *args, fault="after_output:1").returncode == 86
    op = U.incomplete(root)[0]["op_id"]; assert U.plan_of(root, op)["action"] == "spec_reference_add"
    U.q(root, *args, check=True)                                                                  # 同請求重送 → 續做
    r = U.q(root, *args, check=True); assert "先前已完成" in r.stderr                              # 完成後重送 → 回報已完成
    e = entry(root, "SPEC-A-001", "1.0"); assert len(e["reference_declarations"]) == 1 and e["reference_declarations"][0]["op_id"] == op
