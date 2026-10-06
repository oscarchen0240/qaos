"""P2：有型別來源（SourceRef）、閉包與 basis、covers、X16、effective_basis；CLR 決策點欄位、答案修訂、applicability、
evidence_addenda、metadata 升級（需求 A 第 3 章 FIX-06、FIX-08；AC-06、AC-08 中可以獨立驗證的部分）。

- spec、CLR 都以正式流程建立（spec import、clarification new／answer／apply；決策點欄位以入口 D：腳本呼叫 clarification.new()）。
- 核准單的 decision.resolutions[] 要到 P4 才由正式流程寫入，所以 approval 型 SourceRef 只在記憶體中組出核准單、做函式層的單元測試（不寫檔）。
- legacy CLR（舊程式留下、沒有 answer_revisions）以直接寫入舊格式檔案建立，模擬部署前就存在的資料；這是 legacy fixture。"""
import json, hashlib, pathlib, textwrap, yaml, pytest
from tests import p1_util as U

SPEC_A = "# 認證規格\n\n## 密碼規則\n\n密碼長度至少 **8** 碼，\n必須包含數字。\n\n> 登入失敗三次鎖定帳號。\n"

def mk(tmp_path, *, refs=True):
    """A（目標）normative 引用 B，B normative 引用 C（深度 2），A informative 引用 I；D 和 A 無關。"""
    root = U.mkroot()
    for sid, text in (("SPEC-A-001", SPEC_A), ("SPEC-B-001", "# B\n\n乙規則。\n"), ("SPEC-C-001", "# C\n\n丙規則。\n"), ("SPEC-I-001", "# I\n\n參考。\n"), ("SPEC-D-001", "# D\n\n無關。\n")):
        f = tmp_path / f"{sid}.md"; f.write_text(text, encoding="utf-8")
        U.q(root, "spec", "import", f, "--spec-id", sid, "--version", "1.0", "--product", "demo", "--area", "AUTH", "--by", "oscar", check=True)
    if refs:
        for t, r, role in (("SPEC-A-001", "SPEC-B-001", "normative"), ("SPEC-B-001", "SPEC-C-001", "normative"), ("SPEC-A-001", "SPEC-I-001", "informative")):
            U.q(root, "spec", "reference", "add", f"{t}@1.0", "--ref", f"{r}@1.0", "--role", role, "--by", "oscar", check=True)
    return root

def run(root, body: str):
    """在子程序執行，最後一行 print 的 JSON 為結果。"""
    code = "import json\nfrom tools.qaos import sources, spec_ops, clarification, store\n" + textwrap.dedent(body)
    return json.loads(U.py(root, code).stdout.strip().splitlines()[-1])

def pin(root, sid, ver="1.0"):
    spec = U.load(root, f"specs/demo/AUTH/{sid}/spec.yaml")
    return {"spec_id": sid, "spec_version": ver, "content_hash": next(v for v in spec["versions"] if v["spec_version"] == ver)["content_hash"]}

def spec_ref(root, sid, quote, location="§密碼規則"):
    return {"type": "spec", **pin(root, sid), "location": location, "quote": quote}

def validate(root, ref, target=("SPEC-A-001", "1.0"), at=None):
    return run(root, f"print(json.dumps(sources.validate({ref!r}, target={target!r}, at={at!r})))")

def new_clr(root, sid="SPEC-A-001", ver="1.0", **decision):
    """入口 D：腳本呼叫 clarification.new()。"""
    return run(root, f"""
c = clarification.new("demo", "AUTH", "{sid}", "{ver}", "密碼長度的下限是幾碼？", "oscar", requirement_id="REQ-AUTH-001", new_request=True, **{decision!r})
print(json.dumps(c["clarification_id"]))""")

def answer(root, cid, text, resolution="requirement_clarified", check=True):
    return U.q(root, "clarification", "answer", cid, "--answer", text, "--answered-by", "pm", "--resolution", resolution, "--by", "oscar", "--new-request", check=check)

def clr(root, cid):
    return U.load(root, f"clarifications/demo/AUTH/{cid}.yaml")

def cref(root, cid, rev, quote):
    r = clr(root, cid)["answer_revisions"][rev]
    return {"type": "clarification", "clarification_id": cid, "answer_rev": rev, "answer_sha256": r["sha256"], "quote": quote}

SCOPE_KW = dict(question_id="Q01", topic="boundary_value", subject="password.min_length", role_scope=["*"], params={})
D_SCOPE = {"spec_id": "SPEC-A-001", "requirement_id": "REQ-AUTH-001", "subject": "password.min_length", "role_scope": ["*"], "params": {}}

def basis_hash(root, sid="SPEC-A-001", ver="1.0"):
    return run(root, f'print(json.dumps(sources.basis_hash(sources.basis("{sid}", "{ver}"))))')

def x16(root, ref, scope=D_SCOPE, bh=None, loader="None"):
    bh = bh or basis_hash(root)
    return run(root, f"print(json.dumps(sources.x16({ref!r}, {scope!r}, {bh!r}, loader={loader})))")

# ---------------------------------------------------------------- 閉包與 basis（附錄 A 1-1）
def test_reading_closure_and_basis(tmp_path):
    root = mk(tmp_path)
    out = run(root, """
nodes = sources.reading_closure("SPEC-A-001", "1.0"); b = sources.basis("SPEC-A-001", "1.0")
print(json.dumps({"nodes": [[n["spec_id"], n["role"], n["depth"], n["decl_rev"]] for n in nodes], "basis": b}))""")
    assert out["nodes"] == [["SPEC-B-001", "normative", 1, 1], ["SPEC-C-001", "normative", 2, 0], ["SPEC-I-001", "informative", 1, 0]]
    b = out["basis"]
    assert b["target"] == pin(root, "SPEC-A-001") and b["target_decl_rev"] == 2                       # A 自己有兩次宣告
    assert [n["spec_id"] for n in b["closure"]] == ["SPEC-B-001", "SPEC-C-001"]                        # basis 只取 normative 遞移，不含 informative
    assert b["closure"][0] == {**pin(root, "SPEC-B-001"), "decl_rev": 1}

def test_basis_hash_changes_with_declarations_only(tmp_path):
    """AC-08-28 的前提：同一版本只改宣告（閉包節點或目標自己的 decl_rev），basis_hash 就改變；內容不變。"""
    root = mk(tmp_path); h0 = basis_hash(root)
    U.q(root, "spec", "reference", "declare-empty", "SPEC-C-001@1.0", "--reason", "C 不引用其他文件", "--by", "oscar", check=True)   # 閉包節點 C 的 decl_rev 0 → 1
    h1 = basis_hash(root); assert h1 != h0
    U.q(root, "spec", "reference", "add", "SPEC-A-001@1.0", "--ref", "SPEC-D-001@1.0", "--role", "informative", "--by", "oscar", check=True)  # 目標自己的 decl_rev
    h2 = basis_hash(root); assert h2 not in (h0, h1)
    assert basis_hash(root) == h2                                                                       # 沒有變動 → 相同

def test_closure_cycle_and_limit(tmp_path):
    root = mk(tmp_path)
    U.q(root, "spec", "reference", "add", "SPEC-C-001@1.0", "--ref", "SPEC-A-001@1.0", "--role", "normative", "--by", "oscar", check=True)   # A→B→C→A
    out = run(root, 'print(json.dumps([n["spec_id"] for n in sources.reading_closure("SPEC-A-001", "1.0")]))')
    assert out == ["SPEC-B-001", "SPEC-C-001", "SPEC-I-001"]                                           # 循環以已訪集合終止
    many = tmp_path / "many"; many.mkdir()
    out = run(root, f"""
import pathlib
for i in range(51):
    f = pathlib.Path({str(many)!r}) / f"{{i}}.md"; f.write_text(f"# N{{i}}\\n", encoding="utf-8")
    spec_ops.spec_import(str(f), f"SPEC-N-{{i:03d}}", "1.0", "demo", "AUTH", by="oscar")
    spec_ops.reference_add("SPEC-D-001@1.0" if i == 0 else f"SPEC-N-{{i - 1:03d}}@1.0", f"SPEC-N-{{i:03d}}@1.0", "normative", "oscar")
try: sources.reading_closure("SPEC-D-001", "1.0"); print(json.dumps("ok"))
except sources.SourceError as e: print(json.dumps(str(e)))""")
    assert "超過 50" in out

# ---------------------------------------------------------------- spec 型（§6.1、§6.2）
def test_ac_08_1_quote_normalization(tmp_path):
    root = mk(tmp_path, refs=False)
    assert validate(root, spec_ref(root, "SPEC-A-001", "密碼長度至少 **8** 碼，")) == [[], []]                 # 逐字
    assert validate(root, spec_ref(root, "SPEC-A-001", "密碼長度至少 8   碼， 必須包含數字。")) == [[], []]       # 只差 ** 與空白（含跨行）
    assert validate(root, spec_ref(root, "SPEC-A-001", "登入失敗三次鎖定帳號。"))[0] == []                      # 行首引用符號
    errs, _ = validate(root, spec_ref(root, "SPEC-A-001", "密碼長度至少 9 碼")); assert errs and "quote 不在" in errs[0]   # 其他差異
    errs, _ = validate(root, spec_ref(root, "SPEC-A-001", "密碼長度至少八碼")); assert errs

def test_ac_08_2_new_quote_must_be_present(tmp_path):
    root = mk(tmp_path, refs=False)
    for q in ("", None):
        r = spec_ref(root, "SPEC-A-001", q)
        if q is None: del r["quote"]
        errs, _ = validate(root, r); assert errs and "quote" in errs[0]
    r = spec_ref(root, "SPEC-A-001", "必須包含數字。", location=""); errs, _ = validate(root, r); assert errs and "location" in errs[0]

def test_ac_08_3_spec_outside_closure_fails(tmp_path):
    root = mk(tmp_path)
    assert validate(root, spec_ref(root, "SPEC-C-001", "丙規則。", "§C"))[0] == []                      # normative 深度 2
    assert validate(root, spec_ref(root, "SPEC-I-001", "參考。", "§I"))[0] == []                        # 直接 informative
    errs, _ = validate(root, spec_ref(root, "SPEC-D-001", "無關。", "§D")); assert errs and "不在它的引用閉包內" in errs[0]

def test_spec_ref_pin_mismatch_fails(tmp_path):
    root = mk(tmp_path, refs=False)
    r = {**spec_ref(root, "SPEC-A-001", "必須包含數字。"), "content_hash": "0" * 64}
    errs, _ = validate(root, r); assert errs and "content_hash" in errs[0]

def test_ac_08_8_missing_heading_only_warns(tmp_path):
    root = mk(tmp_path, refs=False)
    errs, warns = validate(root, spec_ref(root, "SPEC-A-001", "必須包含數字。", location="§帳號規則 第 5 行"))
    assert errs == [] and warns and "只警告" in warns[0]

def test_ac_08_7_clarification_text_disguised_as_spec_fails(tmp_path):
    root = mk(tmp_path, refs=False); cid = new_clr(root); answer(root, cid, "密碼至少 10 碼（PM 決議）")
    errs, _ = validate(root, spec_ref(root, "SPEC-A-001", "密碼至少 10 碼（PM 決議）")); assert errs and "quote 不在" in errs[0]

# ---------------------------------------------------------------- clarification 型（§6.1、§7）
def test_ac_08_5_unanswered_clr_cannot_be_referenced(tmp_path):
    root = mk(tmp_path, refs=False); cid = new_clr(root)
    r = {"type": "clarification", "clarification_id": cid, "answer_rev": 0, "answer_sha256": "0" * 64, "quote": "x"}
    errs, _ = validate(root, r); assert errs and "沒有答案修訂" in errs[0]
    U.q(root, "clarification", "ask", cid, "--to", "pm", "--by", "oscar", check=True)
    errs, _ = validate(root, r); assert errs and "ASKED" in errs[0]

def test_clarification_ref_checks_pinned_rev(tmp_path):
    """AC-08-10 的函式層：依釘選的 rev 驗證；之後有新答案，舊 rev 仍 PASS。另驗 hash、quote、resolution、WITHDRAWN（附錄 A 1-15、3-17）。"""
    root = mk(tmp_path, refs=False); cid = new_clr(root); answer(root, cid, "下限是 8 碼。")
    r0 = cref(root, cid, 0, "下限是 8 碼")
    answer(root, cid, "下限改為 10 碼。")
    c = clr(root, cid); assert [r["rev"] for r in c["answer_revisions"]] == [0, 1] and c["answer"] == "下限改為 10 碼。"
    assert validate(root, r0)[0] == []                                                                    # 歷史有效
    assert validate(root, {**r0, "quote": "下限改為 10 碼"})[0]                                           # quote 對照釘選的 rev，不對照目前答案
    assert validate(root, {**r0, "answer_sha256": "0" * 64})[0]
    cid2 = new_clr(root); answer(root, cid2, "維持現狀。", resolution="no_change")
    errs, _ = validate(root, cref(root, cid2, 0, "維持現狀")); assert errs and "resolution" in errs[0]
    cid3 = new_clr(root); U.q(root, "clarification", "withdraw", cid3, "--by", "oscar", check=True)
    errs, _ = validate(root, {"type": "clarification", "clarification_id": cid3, "answer_rev": 0, "answer_sha256": "0" * 64, "quote": "x"}); assert "撤回" in errs[0]

def test_answer_revisions_are_append_only_and_record_basis(tmp_path):
    root = mk(tmp_path); cid = new_clr(root); answer(root, cid, "下限是 8 碼。")
    r0 = clr(root, cid)["answer_revisions"][0]
    assert r0["sha256"] == hashlib.sha256("下限是 8 碼。".encode()).hexdigest() and r0["basis_hash"] == basis_hash(root)
    assert r0["basis"]["target"] == pin(root, "SPEC-A-001") and r0["op_id"]
    answer(root, cid, "下限改為 10 碼。")
    assert clr(root, cid)["answer_revisions"][0] == r0                                                     # 舊修訂位元不變

def legacy_clr(root, cid="CLR-AUTH-900", status="ANSWERED", answer_text="密碼下限 8 碼。", **extra):
    """legacy fixture：舊程式回答過的 CLR（沒有 answer_revisions、沒有決策點欄位）。"""
    c = {"clarification_id": cid, "product": "demo", "functional_area": "AUTH", "spec_id": "SPEC-A-001", "spec_version": "1.0", "requirement_id": "REQ-AUTH-001",
         "question": "密碼下限是幾碼？", "context": "", "options": [], "raised_by": "oscar", "raised_at": "2026-09-01T00:00:00Z", "status": status,
         "answer": answer_text, "answered_by": "pm", "answered_at": "2026-09-02T00:00:00Z", "resolution": "requirement_clarified",
         "history": [{"at": "2026-09-01T00:00:00Z", "from_status": None, "to_status": "OPEN", "by": "oscar", "trigger": "new"},
                     {"at": "2026-09-02T00:00:00Z", "from_status": "OPEN", "to_status": status, "by": "oscar", "trigger": "answered"}], **extra}
    p = pathlib.Path(root) / f"clarifications/demo/AUTH/{cid}.yaml"; p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(c, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return cid

def test_ac_08_14_legacy_answer_becomes_rev0(tmp_path):
    root = mk(tmp_path, refs=False); cid = legacy_clr(root)
    answer(root, cid, "密碼下限改為 10 碼。")
    revs = clr(root, cid)["answer_revisions"]
    assert [r["rev"] for r in revs] == [0, 1] and revs[0]["sha256"] == hashlib.sha256("密碼下限 8 碼。".encode()).hexdigest()
    assert revs[0]["basis"] == {"target": pin(root, "SPEC-A-001"), "target_decl_rev": 0, "closure": []} and revs[0]["answered_at"] == "2026-09-02T00:00:00Z"

def test_answer_requires_registered_spec(tmp_path):
    root = mk(tmp_path, refs=False)
    cid = run(root, 'c = clarification.new("demo", "AUTH", "SPEC-Z-001", "1.0", "不存在的規格？", "oscar"); print(json.dumps(c["clarification_id"]))')
    before = U.snapshot(root)
    r = answer(root, cid, "x", check=False); assert r.returncode != 0 and "basis" in r.stderr
    assert U.diff(before, U.snapshot(root)) == {"added": [], "removed": [], "changed": []}

# ---------------------------------------------------------------- covers（AC-08-20～23、35～37）
COVERS = [  # (A 的 role_scope, A 的 params, D 的 role_scope, D 的 params, 預期)
    (["operator"], {}, ["admin", "site_manager"], {}, False),                                            # AC-08-20
    (["*"], {"target_scope": "own_venue"}, ["admin"], {"target_scope": "out_of_scope"}, False),          # AC-08-21
    (["admin"], {}, ["admin", "site_manager"], {}, False),                                               # AC-08-22
    (["admin", "site_manager"], {}, ["admin"], {"target_scope": "out_of_scope"}, True),                  # AC-08-23
    (["admin", "site_manager"], {}, ["admin", "site_manager"], {}, True),                                # AC-08-24 的 scope
    (["*"], {}, ["*"], {}, True),                                                                        # AC-08-26 的 scope
    (["admin"], {}, ["*"], {}, False),                                                                   # D 為 * 時 A 也必須是 *
    (["*"], {"mode": "cash"}, ["*"], {}, False),                                                         # AC-08-35
    (["*"], {}, ["*"], {"mode": "cash"}, True),                                                          # AC-08-36
    (["*"], {"mode": ["cash", "credit"]}, ["*"], {"mode": ["cash"]}, True),                              # AC-08-37
    (["*"], {"mode": ["cash"]}, ["*"], {"mode": ["cash", "credit"]}, False),                             # AC-08-37
]

def test_covers_table():
    root = U.mkroot()
    base = {"spec_id": "SPEC-A-001", "requirement_id": "REQ-AUTH-001", "subject": "s"}
    cases = [[{**base, "role_scope": ar, "params": ap}, {**base, "role_scope": dr, "params": dp}] for ar, ap, dr, dp, _ in COVERS]
    cases += [[{**base, "role_scope": ["*"], "params": {}}, {**base, "subject": "t", "role_scope": ["*"], "params": {}}],                         # subject 不同
              [{**base, "role_scope": ["*"], "params": {}}, {**base, "requirement_id": "REQ-AUTH-002", "role_scope": ["*"], "params": {}}]]     # 需求不同
    out = run(root, f"print(json.dumps([sources.covers(a, d) for a, d in {cases!r}]))")
    assert out == [c[-1] for c in COVERS] + [False, False]

# ---------------------------------------------------------------- X16（§9.3；AC-08-6、17、26～31、38）
def scoped_clr(root, **over):
    kw = {**SCOPE_KW, **over}; cid = new_clr(root, **kw); answer(root, cid, "下限是 8 碼。"); return cid

def test_ac_08_30_same_basis_and_covering_scope_passes(tmp_path):
    root = mk(tmp_path); cid = scoped_clr(root)
    assert x16(root, cref(root, cid, 0, "下限是 8 碼")) == []

def test_ac_08_6_scope_not_covering_fails(tmp_path):
    root = mk(tmp_path); cid = scoped_clr(root, role_scope=["operator"])
    errs = x16(root, cref(root, cid, 0, "下限是 8 碼"), {**D_SCOPE, "role_scope": ["admin", "site_manager"]})
    assert errs and "不涵蓋" in errs[0]

def test_ac_08_27_28_basis_changed_fails_and_29_applicability_fixes(tmp_path):
    root = mk(tmp_path); cid = scoped_clr(root); ref = cref(root, cid, 0, "下限是 8 碼")
    # 28：同一版本只改宣告（閉包中 C 的 decl_rev）→ basis_hash 改變 → FAIL；沒有開新 CLR
    U.q(root, "spec", "reference", "declare-empty", "SPEC-C-001@1.0", "--reason", "x", "--by", "oscar", check=True)
    errs = x16(root, ref); assert errs and "basis_hash 不同" in errs[0]
    # 27：新版本（v1.1）的決策點，basis 不同 → FAIL
    f = tmp_path / "a11.md"; f.write_text(SPEC_A + "\n新增條款。\n", encoding="utf-8")
    U.q(root, "spec", "import", f, "--spec-id", "SPEC-A-001", "--version", "1.1", "--product", "demo", "--area", "AUTH", "--by", "oscar", check=True)
    h11 = basis_hash(root, "SPEC-A-001", "1.1"); assert x16(root, ref, bh=h11)
    # 29：人以 applicability add 確認 v1.1 的 basis → PASS
    base = ["clarification", "applicability", "add", cid, "--answer-rev", "0", "--requirement", "REQ-AUTH-001", "--subject", "password.min_length",
            "--role-scope", "*", "--params", "{}", "--target", "SPEC-A-001@1.1", "--rationale", "v1.1 沒有改密碼規則", "--by", "oscar"]
    r = U.q(root, *base); assert r.returncode != 0 and h11 in r.stderr and "未寫入" in r.stderr                  # 先顯示 basis_hash，未確認不寫
    assert "applicability" not in clr(root, cid)
    U.q(root, *base, "--confirm-basis", h11, check=True)
    ap = clr(root, cid)["applicability"][0]
    assert ap["basis_hash"] == h11 and ap["scope"] == {**D_SCOPE} and ap["sha256"] == run(root, f"r = {ap!r}; r.pop('sha256'); print(json.dumps(sources.chash(r)))")
    assert x16(root, ref, bh=h11) == []
    # 31：之後 v1.1 的宣告又改變（H3）→ 舊的人工紀錄不適用 → FAIL
    U.q(root, "spec", "reference", "declare-empty", "SPEC-A-001@1.1", "--reason", "x", "--by", "oscar", check=True)
    assert x16(root, ref, bh=basis_hash(root, "SPEC-A-001", "1.1"))

def test_ac_08_17_and_38_legacy_clr_needs_applicability(tmp_path):
    """legacy CLR：沒有答案範圍、rev 0 的 basis 閉包為空。(a) 沒有 applicability → SourceRef 本身 PASS，但 X16 FAIL；(b) 有相符的 applicability → PASS（AC-08-16、24、32 的合成版本）。"""
    root = mk(tmp_path); cid = legacy_clr(root)
    answer(root, cid, "密碼下限 8 碼（重申）。")                                                    # 新版 answer() 先把既有答案存成 rev 0
    ref = cref(root, cid, 0, "密碼下限 8 碼")
    assert validate(root, ref)[0] == []                                                                 # SourceRef 本身 PASS
    errs = x16(root, ref); assert errs and "basis_hash 不同" in errs[0]                                 # 目前 basis（有宣告）≠ legacy basis
    h = basis_hash(root)
    U.q(root, "clarification", "applicability", "add", cid, "--answer-rev", "0", "--requirement", "REQ-AUTH-001", "--subject", "password.min_length",
        "--role-scope", "*", "--params", "{}", "--target", "SPEC-A-001@1.0", "--rationale", "人核對過本次 basis", "--by", "oscar", "--confirm-basis", h, check=True)
    assert x16(root, ref) == []
    assert x16(root, ref, {**D_SCOPE, "subject": "password.max_length"})                               # 範圍不涵蓋的決策點仍 FAIL

@pytest.mark.parametrize("by", ["system", "agent-test-designer"])
def test_ac_08_18_applicability_only_by_human(by, tmp_path):
    root = mk(tmp_path, refs=False); cid = scoped_clr(root); before = U.snapshot(root)
    r = U.q(root, "clarification", "applicability", "add", cid, "--answer-rev", "0", "--requirement", "REQ-AUTH-001", "--subject", "password.min_length",
            "--role-scope", "*", "--params", "{}", "--target", "SPEC-A-001@1.0", "--rationale", "x", "--by", by)
    assert r.returncode != 0 and "只能由人" in r.stderr and U.diff(before, U.snapshot(root)) == {"added": [], "removed": [], "changed": []}

def test_ac_08_25_applicability_requires_every_dimension(tmp_path):
    root = mk(tmp_path, refs=False); cid = scoped_clr(root)
    full = {"--answer-rev": "0", "--requirement": "REQ-AUTH-001", "--subject": "password.min_length", "--role-scope": "*", "--params": "{}", "--target": "SPEC-A-001@1.0", "--rationale": "x"}
    for missing in ("--role-scope", "--params", "--subject", "--requirement"):
        args = [x for k, v in full.items() if k != missing for x in (k, v)]
        r = U.q(root, "clarification", "applicability", "add", cid, *args, "--by", "oscar"); assert r.returncode != 0 and missing in r.stderr
    for bad in (["--role-scope", "*", "--role-scope", "admin"], ["--params", '{"Mode": "cash"}']):                # * 不得和具名角色混用；鍵只能 [a-z0-9_]
        args = [x for k, v in full.items() if k not in bad[::2] for x in (k, v)] + bad
        r = U.q(root, "clarification", "applicability", "add", cid, *args, "--by", "oscar"); assert r.returncode != 0 and "不合法" in r.stderr, (bad, r.stderr)
    assert "applicability" not in clr(root, cid)

# ---------------------------------------------------------------- approval 型（記憶體中的核准單；正式寫入在 P4）
MEM_LOADER = """
class Mem(sources.StoreLoader):
    def __init__(self, apr): self.apr = apr
    def approval(self, i): return self.apr.get(i)
"""

def approval(decision="approve", type_="RESOLVE_AMBIGUITY", source=None, req="REQ-AUTH-001", q="Q01", rationale="採用 8 碼的解讀。"):
    d = {"decision": decision, "decided_by": "oscar", "decided_at": "2026-10-07T00:00:00Z",
         "resolutions": [{"requirement_id": req, "question_id": q, "outcome": "select_interpretation", "source": source, "rationale": rationale}]}
    return {"approval_id": "APR-0900", "type": type_, "status": "DECIDED", "decision": d}

def aref(root, apr, quote="採用 8 碼", idx=0):
    h = run(root, f"print(json.dumps(sources.chash({apr['decision']!r})))")
    return {"type": "approval", "approval_id": apr["approval_id"], "decision_sha256": h, "resolution_index": idx, "quote": quote}

def mem(root, body, apr):
    return run(root, MEM_LOADER + f"L = Mem({{'APR-0900': {apr!r}}})\n" + body)

def test_approval_ref_validation(tmp_path):
    """AC-08-9、12、13、34 與 X15 的函式層。"""
    root = mk(tmp_path, refs=False); at = ("REQ-AUTH-001", "Q01")
    ok = approval(); assert mem(root, f"print(json.dumps(sources.validate({aref(root, ok)!r}, at={at!r}, loader=L)))", ok) == [[], []]
    cases = {"ACTIVATE": approval(type_="ACTIVATE_TESTCASE"), "reject": approval(decision="reject"),
             "nested": approval(source={"type": "approval", "approval_id": "APR-0901", "decision_sha256": "0" * 64, "resolution_index": 0, "quote": "x"})}
    for name, apr in cases.items():
        errs, _ = mem(root, f"print(json.dumps(sources.validate({aref(root, apr)!r}, at={at!r}, loader=L)))", apr); assert errs, name
    assert "RESOLVE_AMBIGUITY" in mem(root, f"print(json.dumps(sources.validate({aref(root, cases['ACTIVATE'])!r}, at={at!r}, loader=L)))", cases["ACTIVATE"])[0][0]
    errs, _ = mem(root, f"print(json.dumps(sources.validate({aref(root, ok)!r}, at=('REQ-AUTH-002', 'Q01'), loader=L)))", ok); assert "不符" in errs[0]      # AC-08-12、13
    errs, _ = mem(root, f"print(json.dumps(sources.validate({{**{aref(root, ok)!r}, 'decision_sha256': '0' * 64}}, at={at!r}, loader=L)))", ok); assert "decision_sha256" in errs[0]
    errs, _ = mem(root, f"print(json.dumps(sources.validate({aref(root, ok, quote='採用 10 碼')!r}, at={at!r}, loader=L)))", ok); assert "rationale" in errs[0]

def test_ac_08_33_approval_wrapper_recurses_x16_and_effective_basis(tmp_path):
    root = mk(tmp_path); cid = scoped_clr(root, role_scope=["operator"]); inner = cref(root, cid, 0, "下限是 8 碼")
    apr = approval(source=inner); ref = aref(root, apr); at = ("REQ-AUTH-001", "Q01")
    out = mem(root, f"""
D = {D_SCOPE!r}; bh = sources.basis_hash(sources.basis("SPEC-A-001", "1.0"))
print(json.dumps({{"outer": sources.validate({ref!r}, at={at!r}, loader=L)[0], "x16": sources.x16({ref!r}, D, bh, loader=L, at={at!r}),
                  "eb": sources.effective_basis({ref!r}, at={at!r}, loader=L), "direct": sources.effective_basis({inner!r})}}))""", apr)
    assert out["outer"] == [] and out["x16"] and "經 APR-0900" in out["x16"][0]                         # 外層合法不代表內層通過
    assert out["eb"] == out["direct"] == ["clarification", cid, 0, inner["answer_sha256"]]             # approval 包裝與直接引用解析到同一個 effective_basis
    own = approval(); out = mem(root, f"print(json.dumps(sources.effective_basis({aref(root, own)!r}, at={at!r}, loader=L)))", own)
    assert out[0] == "approval"                                                                        # 核准者自行裁決：不是任何 CLR
    sref = spec_ref(root, "SPEC-A-001", "必須包含數字。")
    assert run(root, f"print(json.dumps(sources.effective_basis({sref!r})))")[0] == "spec"

# ---------------------------------------------------------------- CLR 欄位（AC-06）
def test_ac_06_2_known_rule_quote_not_in_source_refuses(tmp_path):
    root = mk(tmp_path, refs=False); before = U.snapshot(root)
    bad = spec_ref(root, "SPEC-A-001", "密碼長度至少 12 碼")
    r = U.py(root, f"""
from tools.qaos import clarification
try: clarification.new("demo", "AUTH", "SPEC-A-001", "1.0", "密碼長度的下限是幾碼？", "agent-spec-analyst", requirement_id="REQ-AUTH-001", known_rules=[{bad!r}], **{SCOPE_KW!r}); print("accepted")
except clarification.ClarificationError as e: print("refused", e)""")
    assert r.stdout.startswith("refused") and "quote 不在" in r.stdout
    assert U.diff(before, U.snapshot(root)) == {"added": [], "removed": [], "changed": []}
    good = spec_ref(root, "SPEC-A-001", "必須包含數字。")
    cid = new_clr(root, known_rules=[good], **SCOPE_KW); assert clr(root, cid)["known_rules"] == [good]

def test_ac_06_3_document_request_needs_cited_at_only(tmp_path):
    root = mk(tmp_path, refs=False); p = pin(root, "SPEC-A-001")
    ok = {"references_status": "undeclared", "missing_sources": [{"cited_at": {**p, "line": 3, "text": "見操作手冊"}, "name": "操作手冊"}]}
    cid = new_clr(root, kind="document_request", coverage=ok, **SCOPE_KW)
    c = clr(root, cid); assert c["document_items"] == [{"item_id": "D01", "cited_at": ok["missing_sources"][0]["cited_at"], "name": "操作手冊", "status": "open"}]
    before = U.snapshot(root)
    for cov in ({"missing_sources": [{"name": "操作手冊"}]}, {"missing_sources": []}):
        r = U.py(root, f"""
from tools.qaos import clarification
try: clarification.new("demo", "AUTH", "SPEC-A-001", "1.0", "缺操作手冊？", "oscar", requirement_id="REQ-AUTH-001", kind="document_request", coverage={cov!r}, **{SCOPE_KW!r}); print("accepted")
except clarification.ClarificationError as e: print("refused", e)""")
        assert r.stdout.startswith("refused"), r.stdout
    assert U.diff(before, U.snapshot(root)) == {"added": [], "removed": [], "changed": []}

def test_ac_06_4_legacy_clr_schema_and_render(tmp_path):
    root = mk(tmp_path, refs=False); cid = legacy_clr(root)
    out = run(root, f"""
from tools.qaos import schema
c = clarification.load("{cid}"); print(json.dumps([schema.errors(c, "spec/clarification.schema.json"), clarification._render(c)]))""")
    assert out[0] == [] and not any(h in out[1] for h in ("## 已查文件", "## 已確定的部分", "## 還需決定的事", "## 衝突兩邊"))
    good = spec_ref(root, "SPEC-A-001", "必須包含數字。")
    cid2 = new_clr(root, known_rules=[good], decision_needed="下限是 8 還是 10？", coverage={"consulted": [pin(root, "SPEC-A-001")]}, **SCOPE_KW)
    md = (pathlib.Path(root) / f"clarifications/demo/AUTH/{cid2}.md").read_text()
    assert "## 已查文件" in md and "## 已確定的部分" in md and "必須包含數字" in md and "## 還需決定的事" in md and "## 衝突兩邊" not in md

def test_ac_06_5_clarification_metadata_upgrade(tmp_path):
    root = mk(tmp_path, refs=False); cid = legacy_clr(root); before = clr(root, cid)
    U.q(root, "clarification", "metadata", "upgrade", cid, "--kind", "spec_question", "--question-id", "Q01", "--subject", "password.min_length",
        "--role-scope", "*", "--params", "{}", "--reason", "補答案範圍", "--by", "oscar", check=True)
    after = clr(root, cid)
    assert (after["kind"], after["question_id"], after["subject"], after["role_scope"], after["params"]) == ("spec_question", "Q01", "password.min_length", ["*"], {})
    assert {k: after.get(k) for k in ("answer", "answer_revisions", "status", "resolution")} == {k: before.get(k) for k in ("answer", "answer_revisions", "status", "resolution")}
    assert len(after["history"]) == len(before["history"]) + 1 and after["history"][-1]["trigger"] == "metadata_upgrade"
    snap = U.snapshot(root)
    r = U.q(root, "clarification", "metadata", "upgrade", cid, "--subject", "password.max_length", "--reason", "x", "--by", "oscar")   # 改寫既有欄位
    assert r.returncode != 0 and "不能經 metadata upgrade 改寫" in r.stderr
    r = U.q(root, "clarification", "metadata", "upgrade", cid, "--question-id", "Q02", "--reason", "x", "--by", "agent-spec-analyst")
    assert r.returncode != 0 and U.diff(snap, U.snapshot(root)) == {"added": [], "removed": [], "changed": []}

def test_ac_08_19_applied_clr_accepts_addenda_but_not_new_answer(tmp_path):
    root = mk(tmp_path, refs=False); cid = scoped_clr(root)
    U.q(root, "clarification", "apply", cid, "--impact-reviewed", "無受影響 TC", "--by", "oscar", check=True)
    before = clr(root, cid); assert before["status"] == "APPLIED"
    src = {"type": "document", "file_name": "PM回覆.pdf", "sha256": "a" * 64, "location": "第 2 段"}
    U.q(root, "clarification", "addenda", "add", cid, "--source", json.dumps(src), "--note", "PM 重申同一決議", "--by", "oscar", check=True)
    after = clr(root, cid)
    assert len(after["evidence_addenda"]) == 1 and after["evidence_addenda"][0]["source"] == src
    assert (after["status"], after["answer_revisions"], after["answer"]) == (before["status"], before["answer_revisions"], before["answer"])
    snap = U.snapshot(root)
    r = answer(root, cid, "改成 10 碼", check=False); assert r.returncode != 0 and "APPLIED" in r.stderr
    assert U.diff(snap, U.snapshot(root)) == {"added": [], "removed": [], "changed": []}

@pytest.mark.parametrize("entry", ["resend", "resume"])
def test_ac_07_29_applicability_add_abort_and_resume(entry, tmp_path):
    """AC-07-29：applicability_add 在寫入 CLR 之後中止 → 兩種入口都續做完成；只有一筆紀錄。"""
    root = mk(tmp_path); cid = scoped_clr(root); h = basis_hash(root)
    args = ["clarification", "applicability", "add", cid, "--answer-rev", "0", "--requirement", "REQ-AUTH-001", "--subject", "password.min_length",
            "--role-scope", "*", "--params", "{}", "--target", "SPEC-A-001@1.0", "--rationale", "x", "--by", "oscar", "--confirm-basis", h]
    assert U.q(root, *args, fault="after_output:1").returncode == 86
    op = U.incomplete(root)[0]["op_id"]; assert U.plan_of(root, op)["action"] == "applicability_add"
    assert len(clr(root, cid)["applicability"]) == 1                                               # 第一步（CLR）已寫入
    r = U.q(root, *args) if entry == "resend" else U.q(root, "operation", "resume", op); assert r.returncode == 0, r.stderr
    assert U.incomplete(root) == [] and len(clr(root, cid)["applicability"]) == 1 and clr(root, cid)["applicability"][0]["op_id"] == op
