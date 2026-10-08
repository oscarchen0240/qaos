"""P5：文件索取單——fulfill（名稱比對／人工對應）、重新驗證失效、waive-item、核准的 waive_missing 與最後判定（A8、A9）
（需求 A 第 6 章 §6；AC-10A-7、8、20～25、52～56、67～69）。
文件與引用宣告都以正式 `spec import`、`spec reference add|remove` 建立；文件索取單由 G-SPEC 入口 A／B 自動開出（E3）。"""
import json, pathlib
from tests import p1_util as U
from tests.test_p4_dispatch import mkroot, py

HDR = "from tests import p5_flow as P\nfrom tools.qaos import clr_lifecycle as L\n"
TWO_MISSING = ('F.req(1, [F.dp("Q01", "undefined", "{LEVEL}", subject="role.assign.scope", role=["site_manager"], coverage=F.cov(missing=['
               'F.missing(13, "手冊 v01 的角色模型（見 7.1.1 角色說明）", "手冊 7.1.1 角色說明"), F.missing(3, "角色與權限", "後台角色與權限_spec_vNN.md")]))], '
               'ambiguity=F.amb("{LEVEL}", "{LEVEL}"), statement="站長指派範圍")')

def import_doc(root, tmp_path, sid, filename=None, title=None):
    f = tmp_path / f"{sid}.md"; f.write_text(f"# {sid}\n\n內容。\n", encoding="utf-8")
    args = ["spec", "import", f, "--spec-id", sid, "--version", "1.0", "--product", "demo", "--area", "DOCS", "--by", "oscar"]
    if filename: args += ["--external-filename", filename]
    if title is not None: args += ["--title", title]
    U.q(root, *args, check=True)
    U.q(root, "spec", "reference", "add", "SPEC-DEMO-001@1.0", "--ref", f"{sid}@1.0", "--role", "informative", "--by", "oscar", check=True)

def doc_clr(root, level="minor"):
    return py(root, HDR + f"""
rid = F.new_run(); g = F.analyze(rid, [{TWO_MISSING.format(LEVEL=level)}]); assert g["result"] == "PASS", g
c = [x for x in F.clrs(requirement_id="REQ-DEMO-001") if x.get("kind") == "document_request"][-1]
print(json.dumps([rid, c["clarification_id"], F.waiting(rid)]))""")

def fulfill(root, cid, item, doc, reason=None, extra=()):
    args = ["clarification", "fulfill", cid, "--item", item, "--document", f"{doc}@1.0", "--by", "oscar", *extra]
    if reason: args += ["--mapping-reason", reason]
    return U.q(root, *args)

def test_fulfill_name_match_mapping_and_applied(tmp_path):
    """AC-10A-7、20、21、22：不相關的已宣告文件、不附理由 → 拒絕；外部檔名比對 → fulfilled（仍 OPEN）；人工對應 → fulfilled → APPLIED（A8）。"""
    root = mkroot(tmp_path)
    rid, cid, _ = doc_clr(root)
    import_doc(root, tmp_path, "SPEC-ROLE-001", filename="後台角色與權限_spec_v02.md")
    import_doc(root, tmp_path, "SPEC-ADMIN-001", filename="後台管理員系統_spec_v03.md", title="後台管理員系統")
    before = U.sha(pathlib.Path(root) / f"clarifications/demo/DEMO/{cid}.yaml")
    for item in ("D01", "D02"):                                                                       # AC-10A-20：P = SPEC-REF-001（已宣告、不相關）
        r = fulfill(root, cid, item, "SPEC-REF-001"); assert r.returncode != 0 and "--mapping-reason" in r.stderr
    r = fulfill(root, cid, "D02", "SPEC-OTHER-001"); assert r.returncode != 0 and "沒有在 SPEC-DEMO-001" in r.stderr   # 沒有宣告為引用
    r = fulfill(root, cid, "D02", "SPEC-ROLE-001", extra=["--by", "agent-x"]); assert r.returncode != 0                 # 附錄 A 6-12：agent 不能 fulfill
    assert U.sha(pathlib.Path(root) / f"clarifications/demo/DEMO/{cid}.yaml") == before
    r = fulfill(root, cid, "D02", "SPEC-ROLE-001"); assert r.returncode == 0, r.stderr                 # AC-10A-21
    c = U.load(root, f"clarifications/demo/DEMO/{cid}.yaml"); d2 = c["document_items"][1]
    assert c["status"] == "OPEN" and d2["status"] == "fulfilled" and d2["fulfillments"][0]["match"]["method"] == "name_match"   # AC-10A-7 第一步
    assert d2["fulfillments"][0]["match"]["matched_text"] == "後台角色與權限_spec" and d2["fulfillments"][0]["target_pin"]["spec_id"] == "SPEC-DEMO-001"
    r = fulfill(root, cid, "D01", "SPEC-ADMIN-001", reason="手冊第七章即後台管理員系統 spec"); assert r.returncode == 0, r.stderr   # AC-10A-22
    c = U.load(root, f"clarifications/demo/DEMO/{cid}.yaml"); d1 = c["document_items"][0]
    assert d1["fulfillments"][0]["match"] == {"method": "human_mapping", "reason": "手冊第七章即後台管理員系統 spec", "by": "oscar"}
    assert c["status"] == "APPLIED" and c["landings"][-1]["path"] == "a8" and [x["result"] for x in c["landings"][-1]["items"]] == ["fulfilled", "fulfilled"]

def test_one_document_two_items_and_revalidation(tmp_path):
    """AC-10A-23：一份文件補兩項 → 兩筆 fulfillment → APPLIED。AC-10A-24、8、25：第一項的宣告被移除 → 失效、不結案、show 顯示原因；重新宣告並重新 fulfill → APPLIED。"""
    root = mkroot(tmp_path)
    _, cid1, _ = doc_clr(root)
    import_doc(root, tmp_path, "SPEC-ROLE-001", filename="後台角色與權限_spec_v02.md")
    assert fulfill(root, cid1, "D01", "SPEC-ROLE-001", reason="同一份文件也涵蓋手冊 7.1.1").returncode == 0
    assert fulfill(root, cid1, "D02", "SPEC-ROLE-001").returncode == 0
    c1 = U.load(root, f"clarifications/demo/DEMO/{cid1}.yaml")
    assert c1["status"] == "APPLIED" and all(len(it["fulfillments"]) == 1 for it in c1["document_items"])
    # 另一張：兩項用不同文件
    U.q(root, "spec", "import", tmp_path / "SPEC-ROLE-001.md", "--spec-id", "SPEC-HAND-001", "--version", "1.0", "--product", "demo", "--area", "DOCS",
        "--external-filename", "手冊 7.1.1 角色說明_v01.md", "--change-summary", "同內容另一份", "--by", "oscar")
    U.q(root, "spec", "reference", "add", "SPEC-DEMO-001@1.0", "--ref", "SPEC-HAND-001@1.0", "--role", "informative", "--by", "oscar", check=True)
    out = py(root, HDR + f"""
rid = F.new_run(); g = F.analyze(rid, [{TWO_MISSING.format(LEVEL="minor").replace("F.req(1,", "F.req(2,")}])
c = [x for x in F.clrs(requirement_id="REQ-DEMO-002") if x.get("kind") == "document_request"][-1]
print(json.dumps([g["result"], g["issues"], c["clarification_id"]]))""")
    assert out[0] == "PASS", out[1]; cid = out[2]
    assert fulfill(root, cid, "D01", "SPEC-HAND-001").returncode == 0                                # 名稱比對（外部檔名）
    U.q(root, "spec", "reference", "remove", "SPEC-DEMO-001@1.0", "--ref", "SPEC-HAND-001@1.0", "--reason", "改用正式文件", "--by", "oscar", check=True)
    assert fulfill(root, cid, "D02", "SPEC-ROLE-001").returncode == 0
    c = U.load(root, f"clarifications/demo/DEMO/{cid}.yaml"); assert c["status"] == "OPEN"            # AC-10A-24：第一項重新驗證失效 → 不結案
    show = json.loads(U.q(root, "clarification", "show", cid, check=True).stdout)
    d1 = next(x for x in show["document_items"] if x["item_id"] == "D01")
    assert d1["fulfillment"].startswith("失效：") and "已不包含 SPEC-HAND-001@1.0" in d1["fulfillment"]   # AC-10A-8
    U.q(root, "spec", "reference", "add", "SPEC-DEMO-001@1.0", "--ref", "SPEC-HAND-001@1.0", "--role", "informative", "--by", "oscar", "--new-request", check=True)   # 新的 decl_rev（新請求）
    assert fulfill(root, cid, "D01", "SPEC-HAND-001", extra=["--new-request"]).returncode == 0
    c = U.load(root, f"clarifications/demo/DEMO/{cid}.yaml")
    assert c["status"] == "APPLIED" and len(c["document_items"][0]["fulfillments"]) == 2              # AC-10A-25

def test_name_validity(tmp_path):
    """AC-10A-52～56：名稱無效時不能比對成立；有效名稱以子字串比對；名稱無效但附理由 → human_mapping。"""
    root = mkroot(tmp_path)
    _, cid, _ = doc_clr(root)
    import_doc(root, tmp_path, "SPEC-BLANK-001", filename="無關檔案_v01.md", title="　 ")                # 52：title 全形加半形空白、外部檔名不相關
    r = fulfill(root, cid, "D02", "SPEC-BLANK-001"); assert r.returncode != 0 and "--mapping-reason" in r.stderr
    import_doc(root, tmp_path, "SPEC-EMPTY-001", filename="_v02.md", title="")                          # 53：去掉版本後為空、title 空
    r = fulfill(root, cid, "D02", "SPEC-EMPTY-001"); assert r.returncode != 0 and "--mapping-reason" in r.stderr
    import_doc(root, tmp_path, "SPEC-TITLE-001", filename="x_v01.md", title="角色與權限")               # 55：title 完整出現在 cited_at.text 中
    assert fulfill(root, cid, "D02", "SPEC-TITLE-001").returncode == 0
    r = fulfill(root, cid, "D01", "SPEC-BLANK-001", reason="這份是手冊 7.1.1 的匯出檔"); assert r.returncode == 0   # 56
    c = U.load(root, f"clarifications/demo/DEMO/{cid}.yaml")
    assert c["document_items"][1]["fulfillments"][-1]["match"]["method"] == "name_match" and c["document_items"][0]["fulfillments"][-1]["match"]["method"] == "human_mapping"
    out = py(root, """
from tools.qaos import clr_lifecycle as L
item = {"name": "後台角色與權限_spec_vNN.md", "cited_at": {"text": "x"}}
print(json.dumps([L._match({"source": {"external_filename": "後台角色與權限_spec_v02.md"}, "title": None}, item),
                  L._match({"source": {"external_filename": "_v02.md"}, "title": "　 "}, item)]))""")
    assert out == ["後台角色與權限_spec", None]                                                        # 54（函式層）：n1 去掉版本與副檔名後比對

def test_waive_item_and_approval_waive_interplay(tmp_path):
    """waive-item 之後全部 fulfilled 或 waived → APPLIED；核准的 waive_missing：已有有效 fulfillment 時 → APPLIED（AC-10A-67、68）；
    沒有有效 fulfillment、涵蓋全部 → A9 WITHDRAWN，含 fulfillment 已失效的情況（AC-10A-69）。"""
    root = mkroot(tmp_path)
    import_doc(root, tmp_path, "SPEC-ROLE-001", filename="後台角色與權限_spec_v02.md")
    _, cid0, _ = doc_clr(root, level="critical")                                                     # waive-item（critical：需求 DRAFT，之後的 run 不會跳過分析）
    assert fulfill(root, cid0, "D02", "SPEC-ROLE-001").returncode == 0
    r = U.q(root, "clarification", "waive-item", cid0, "--item", "D01", "--reason", "手冊不再提供", "--by", "agent-x"); assert r.returncode != 0
    assert U.q(root, "clarification", "waive-item", cid0, "--item", "D01", "--reason", "手冊不再提供", "--by", "oscar").returncode == 0
    assert U.load(root, f"clarifications/demo/DEMO/{cid0}.yaml")["status"] == "APPLIED"
    results = {}
    for case in ("67", "68", "69a", "69b"):
        n = {"67": 3, "68": 4, "69a": 5, "69b": 6}[case]
        rid, cid, apr = py(root, HDR + f"""
rid = F.new_run(); g = F.analyze(rid, [{TWO_MISSING.format(LEVEL="critical").replace("F.req(1,", f"F.req({n},")}]); assert g["result"] == "PASS", g
c = [x for x in F.clrs(requirement_id="REQ-DEMO-00{n}") if x.get("kind") == "document_request"][-1]
print(json.dumps([rid, c["clarification_id"], F.waiting(rid)]))""")
        if case in ("67", "68", "69b"): assert fulfill(root, cid, "D02", "SPEC-ROLE-001").returncode == 0
        if case == "69b":
            U.q(root, "spec", "reference", "remove", "SPEC-DEMO-001@1.0", "--ref", "SPEC-ROLE-001@1.0", "--reason", "暫時移除", "--by", "oscar", check=True)
        both = case != "67"
        out = py(root, HDR + f"""
p = F.pin()
items = [{{"cited_at": {{**p, "line": 13}}, "name": "手冊 7.1.1 角色說明"}}] + ([{{"cited_at": {{**p, "line": 3}}, "name": "後台角色與權限_spec_vNN.md"}}] if {both} else [])
F.approve("{apr}", resolutions=[{{"requirement_id": "REQ-DEMO-00{n}", "question_id": "Q01", "outcome": "waive_missing", "waived": items, "rationale": "改向 PM 直接確認"}}])
c = clr.load("{cid}"); print(json.dumps([c["status"], [i["status"] for i in c["document_items"]], len([l for l in c.get("landings") or [] if l["type"] == "applied"])]))""")
        results[case] = out
        if case == "69b":
            U.q(root, "spec", "reference", "add", "SPEC-DEMO-001@1.0", "--ref", "SPEC-ROLE-001@1.0", "--role", "informative", "--by", "oscar", "--new-request", check=True)
    assert results["67"] == ["APPLIED", ["waived", "fulfilled"], 1]
    assert results["68"] == ["APPLIED", ["waived", "waived"], 1]                                     # 已有有效 fulfillment → 不是 A9
    assert results["69a"] == ["WITHDRAWN", ["waived", "waived"], 0]
    assert results["69b"] == ["WITHDRAWN", ["waived", "waived"], 0]                                  # 依重新驗證分類，不看歷史紀錄
