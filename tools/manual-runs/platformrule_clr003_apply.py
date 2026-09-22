#!/usr/bin/env python3
"""套用 CLR-PLATFORMRULE-003 PM 回覆（2026-09-22）：新需求——操作員有權限進入「注單查詢」與「稽核明細」。
1) 新增 REQ-PLATFORMRULE-024（權限表未列，現有 REQ 掛不上）；2) REQ-PLATFORMRULE-014 statement 移除「選單僅含四頁」的過時實機描述。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store
SID, SV, BY = "SPEC-PLATFORMRULE-001", "0.1", "oscarchen@blockaction.tech"
p = store.requirements_path(SID, SV); d = store.load(p)
ids_ = {r["requirement_id"] for r in d["requirements"]}; assert "REQ-PLATFORMRULE-024" not in ids_
sr = {"spec_id": SID, "spec_version": SV, "location": "§角色與權限（權限表未列「注單查詢」「稽核明細」；依 CLR-PLATFORMRULE-003 PM 回覆 2026-09-22 新增）", "quote": "可見場館範圍 | 全部場館 | 自身站台及所有子站台下的場館 | 僅自身所屬場館"}
new = {"requirement_id": "REQ-PLATFORMRULE-024", "version": 1, "spec_id": SID, "spec_version": SV, "type": "security",
       "title": "操作員可進入注單查詢與稽核明細，可見範圍限自身場館",
       "statement": "操作員角色的後台選單含「各式報表 > 注單查詢」與「各式報表 > 稽核明細」，可進入並查詢；資料範圍依 REQ-PLATFORMRULE-013 限自身所屬場館。（CLR-PLATFORMRULE-003 PM 回覆 2026-09-22：新需求；spec 權限表尚未補列，現行實機操作員選單無此兩頁，屬未實作）",
       "acceptance_criteria": [
           {"ac_id": "AC-PLATFORMRULE-0241", "given": "以操作員身分登入後台，站台切換選單已選定自身所屬的機台場館", "when": "展開各式報表分類", "then": "選單含「注單查詢」與「稽核明細」，可進入並執行查詢"},
           {"ac_id": "AC-PLATFORMRULE-0242", "given": "以操作員身分於注單查詢或稽核明細頁查詢", "when": "檢視查詢結果（含嘗試指定自身場館以外的範圍）", "then": "僅能查得自身所屬場館範圍內的資料"}],
       "spec_reference": sr, "ambiguity": None, "risk": "high", "status": "ACTIVE", "behavior_kind": "rejection",
       "rejection_contract": {"defined": True, "description": "可見範圍規則由 REQ-013 定義（僅自身所屬場館）；頁面存取權由 CLR-PLATFORMRULE-003 定案", "spec_reference": {"spec_id": SID, "spec_version": SV, "location": "§角色與權限", "quote": ""}},
       "history": [{"at": store.now(), "from_status": None, "to_status": "ACTIVE", "by": BY, "trigger": "clarification_applied_CLR-PLATFORMRULE-003：PM 新需求，操作員可進入注單查詢與稽核明細"}]}
d["requirements"].append(new)
for r in d["requirements"]:
    if r["requirement_id"] == "REQ-PLATFORMRULE-014":
        r["statement"] = ("操作員角色的後台選單完全沒有「站台列表」這個項目，因此無法進入場館設定頁面，額度上限等欄位無從檢視或修改。"
                          "（2026-09-15 實機截圖確認操作員選單含：會員與加盟商>會員列表、帳務管理>洗分出金核實、各式報表>交易紀錄查詢/場館日結報表；"
                          "依 CLR-PLATFORMRULE-003 PM 回覆 2026-09-22，各式報表另須含注單查詢與稽核明細，見 REQ-PLATFORMRULE-024）")
        r.setdefault("history", []).append({"at": store.now(), "from_status": "ACTIVE", "to_status": "ACTIVE", "by": BY, "trigger": "clarification_applied_CLR-PLATFORMRULE-003：statement 移除「選單僅含四頁」的過時實機描述，改引 REQ-024"})
store.save(p, d); print("REQ-PLATFORMRULE-024 added; REQ-014 statement updated")
