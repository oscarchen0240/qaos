"""P5：開單關卡與 issue key 去重（需求 A 第 3 章 §4、§5；AC-07-1～7、10、11、101～104）。
CLR 以正式入口建立：入口 A、B（G-SPEC 自動開單）、入口 C（CLI clarification new）、入口 D（腳本呼叫 clarification.new，另外標示）。"""
import json, pathlib
from tests import p1_util as U
from tests.test_p4_dispatch import mkroot, py

ENTRY_D = """
def d(subject="site.child.delete", role=("admin",), params=None, topic="permission", kind="spec_question", rid="REQ-DEMO-001", by="agent-spec-analyst", q="Q01", **kw):
    try:
        c = clr.new("demo", "DEMO", F.SPEC, F.VER, kw.pop("question", "子站台能否刪除？"), by, requirement_id=rid, new_request=True, kind=kind, question_id=q, topic=topic,
                    subject=subject, role_scope=list(role), params=params or {}, level="minor", known_rules=[], coverage=F.cov(), **kw)
        return {"id": c["clarification_id"], "linked": bool(c.get("_linked")), "related": c.get("related_clarifications"), "key": c.get("issue_key")}
    except clr.ClarificationError as e: return {"error": str(e)}
"""

def test_ac_07_1_2_3_6_different_scopes_open_new_and_params_normalize(tmp_path):
    root = mkroot(tmp_path)
    out = py(root, ENTRY_D + """
a = d(subject="cashout.redeemed_amount.attribution_date", topic="calculation")
b = d(subject="cashout.voided_receipt.display", topic="calculation")                               # AC-07-1：不同 subject
c1 = d(subject="report.venue_scope", role=("operator",)); c2 = d(subject="report.venue_scope", role=("admin", "site_manager"))   # AC-07-2：不同 role_scope
e1 = d(subject="csv_export.header_when_empty", topic="display_format"); e2 = d(subject="csv_export.decimal_format", topic="display_format")   # AC-07-3
same = d(subject="cashout.voided_receipt.display", topic="calculation")                            # key 完全相同 → 連結
k1 = clr.key_material({"kind": "spec_question", "spec_id": F.SPEC, "requirement_id": "REQ-DEMO-001", "topic": "permission", "subject": "s", "params": {"role": ["b", "a"], "x": "1"}, "role_scope": ["b", "a"]})
k2 = clr.key_material({"kind": "spec_question", "spec_id": F.SPEC, "requirement_id": "REQ-DEMO-001", "topic": "permission", "subject": "s", "params": {"x": "1", "role": ["a", "b", "a"]}, "role_scope": ["a", "b", "a"]})
print(json.dumps({"a": a, "b": b, "c1": c1, "c2": c2, "e1": e1, "e2": e2, "same": same, "k_equal": k1 == k2}))""")
    ids_ = [out[k]["id"] for k in ("a", "b", "c1", "c2", "e1", "e2")]
    assert len(set(ids_)) == 6 and not any(out[k]["linked"] for k in ("a", "b", "c1", "c2", "e1", "e2"))
    assert out["same"]["linked"] and out["same"]["id"] == out["b"]["id"]                              # AC-07-5 的連結規則（入口 D）
    assert out["k_equal"]                                                                             # AC-07-6：params 陣列排序去重、鍵順序無關

def test_ac_07_4_10_11_topic_other_always_new(tmp_path):
    root = mkroot(tmp_path)
    out = py(root, ENTRY_D + """
x = d(subject="ui.banner.color", topic="other"); y = d(subject="ui.footer.text", topic="other"); z = d(subject="ui.banner.color", topic="other")
print(json.dumps({"x": x, "y": y, "z": z}))""")
    x, y, z = out["x"], out["y"], out["z"]
    assert len({x["id"], y["id"], z["id"]}) == 3                                                      # AC-07-4：一律新開
    assert {"id": x["id"], "relation": "possible_duplicate"} in y["related"]
    assert {"id": x["id"], "relation": "possible_duplicate"} in z["related"] and {"id": y["id"], "relation": "possible_duplicate"} in z["related"]
    # AC-07-10：同一請求中止後重送 → 沿用計畫中的 CLR ID；AC-07-11：新請求 → 新開並標記
    args = ["clarification", "new", "--product", "demo", "--area", "DEMO", "--spec-id", "SPEC-DEMO-001", "--spec-version", "1.0", "--question", "橫幅顏色要不要可設定？",
            "--requirement-id", "REQ-DEMO-002", "--consulted", "SPEC-DEMO-001@1.0", "--kind", "spec_question", "--question-id", "Q01", "--topic", "other",
            "--subject", "ui.banner.color", "--role-scope", "*", "--no-params", "--level", "minor", "--by", "oscar"]
    r = U.q(root, *args, fault="after_output:1"); assert r.returncode == 86
    r = U.q(root, *args); assert r.returncode == 0, r.stderr
    made = [p.stem for p in pathlib.Path(root).glob("clarifications/demo/DEMO/CLR-*.yaml") if U.load(root, f"clarifications/demo/DEMO/{p.name}").get("requirement_id") == "REQ-DEMO-002"]
    assert len(made) == 1                                                                              # 中止後續做只有一張
    r = U.q(root, *args, "--new-request"); assert r.returncode == 0, r.stderr
    made2 = sorted(p.stem for p in pathlib.Path(root).glob("clarifications/demo/DEMO/CLR-*.yaml") if U.load(root, f"clarifications/demo/DEMO/{p.name}").get("requirement_id") == "REQ-DEMO-002")
    assert len(made2) == 2
    new = U.load(root, f"clarifications/demo/DEMO/{[m for m in made2 if m not in made][0]}.yaml")
    assert {"id": made[0], "relation": "possible_duplicate"} in new["related_clarifications"]

def test_ac_07_5_resent_gspec_links_entry_a_and_b(tmp_path):
    """同一份分析（critical 與 minor 兩個未決決策點）退回後重送 G-SPEC：入口 A、B 都不重複開單；入口 B 連結時核准單 impact 含該 CLR；audit 有 LINK_CLARIFICATION。"""
    root = mkroot(tmp_path)
    out = py(root, """
from tests import p5_flow as P
q2 = F.dp("Q02", "undefined", "minor", subject="site.child.rename", decision_needed="子站台能否改名")
r = P.conflict_req(1); r["decision_points"].append(q2)
rid = F.new_run(); F.analyze(rid, [r]); apr1 = F.waiting(rid)
first = sorted(c["clarification_id"] for c in F.clrs(requirement_id="REQ-DEMO-001"))
F.approve(apr1, decision="reject")
F.analyze(rid, [r]); apr2 = F.waiting(rid)
second = sorted(c["clarification_id"] for c in F.clrs(requirement_id="REQ-DEMO-001"))
impact = store.load(f"approvals/{apr2}.yaml")["impact"]
ev = [store.load(p)["action"] for p in store.glob(f"runs/{rid}/audit.d/*.yaml")]
print(json.dumps([first, second, impact, ev.count("LINK_CLARIFICATION")]))""")
    first, second, impact, links = out
    assert len(first) == 2 and second == first                                                         # 沒有重複開單
    crit = [c for c in first if c in {i["id"] for i in impact}]
    assert len(crit) == 1 and links == 2                                                               # 入口 B 連結的單在新核准單的 impact；A、B 各一筆 LINK

def test_ac_07_7_and_104_basis_change(tmp_path):
    """只有 basis 不同（目標宣告改變）→ 新開、prior_version；basis 也相同 → 連結（AC-07-7、104）。"""
    root = mkroot(tmp_path, refs=())
    out = py(root, ENTRY_D + """
a = d(); same = d()
print(json.dumps([a, same]))""")
    a, same = out
    assert same["linked"] and same["id"] == a["id"]                                                   # 104 (b)：target_decl_rev 沒變 → 連結
    U.q(root, "spec", "reference", "declare-empty", "SPEC-DEMO-001@1.0", "--reason", "沒有引用", "--by", "oscar", check=True)   # 只改 target_decl_rev
    out2 = py(root, ENTRY_D + "print(json.dumps(d()))")
    assert not out2["linked"] and out2["id"] != a["id"] and out2["key"] != a["key"]                  # 104 (a)：新開
    assert out2["related"] == [{"id": a["id"], "relation": "prior_version"}]                          # AC-07-7：prior_version

def test_ac_07_101_102_103_gate(tmp_path):
    root = mkroot(tmp_path)
    before = U.snapshot(root)
    out = py(root, """
try: clr.new("demo", "DEMO", F.SPEC, F.VER, "缺欄位的單", "agent-spec-analyst", requirement_id="REQ-DEMO-001", new_request=True, kind="spec_question", subject="a.b"); r = "accepted"
except clr.ClarificationError as e: r = str(e)
print(json.dumps(r))""")
    assert "決策點欄位" in out and "AC-07-101" in out
    d = U.diff(before, U.snapshot(root)); assert not d["changed"] and not [p for p in d["added"] if not p.startswith(("operations/", "locks/"))], d
    base = ["clarification", "new", "--product", "demo", "--area", "DEMO", "--spec-id", "SPEC-DEMO-001", "--spec-version", "1.0", "--question", "子站台能否改名？", "--requirement-id", "REQ-DEMO-001", "--by", "oscar"]
    before = U.snapshot(root)
    r = U.q(root, *base); assert r.returncode != 0 and "--consulted" in r.stderr                    # (a) 拒絕、不寫入
    d = U.diff(before, U.snapshot(root)); assert not d["changed"] and not [p for p in d["added"] if not p.startswith(("operations/", "locks/"))], d
    r = U.q(root, *base, "--no-source-check", "--reason", "PM 口頭提出，尚未查文件", "--new-request"); assert r.returncode == 0, r.stderr   # (b)
    cid_b = r.stdout.split()[0]; c = U.load(root, f"clarifications/demo/DEMO/{cid_b}.yaml")
    assert "PM 口頭提出" in c["history"][0]["note"]
    events = [U.load(root, f"runs/_audit.d/{p.name}") for p in pathlib.Path(root).glob("runs/_audit.d/*.yaml")]
    r = U.q(root, *base, "--consulted", "SPEC-DEMO-001@1.0", "--consulted", "SPEC-REF-001@1.0", "--new-request"); assert r.returncode == 0, r.stderr   # (c)
    cid_c = r.stdout.split()[0]; c = U.load(root, f"clarifications/demo/DEMO/{cid_c}.yaml")
    assert [p["spec_id"] for p in c["coverage"]["consulted"]] == ["SPEC-DEMO-001", "SPEC-REF-001"]
    # AC-07-103：同需求已有沒有 issue key 的舊單（cid_b、cid_c 都沒有 key）→ 新單標 possible_duplicate，audit 有警告
    assert {"id": cid_b, "relation": "possible_duplicate"} in c["related_clarifications"]
    warns = [U.load(root, f"runs/_audit.d/{p.name}") for p in pathlib.Path(root).glob("runs/_audit.d/*.yaml")]
    assert any(e["action"] == "WARN_POSSIBLE_DUPLICATE" and cid_c in e["detail"] for e in warns)
