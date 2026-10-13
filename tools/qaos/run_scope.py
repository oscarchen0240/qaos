"""spec-to-testcase 的 run scope（ADR-013）：input.scope 寫成需求清單時，G-DESIGN 只要求 scope 內需求的覆蓋與規則。

語法：`<REQ 清單>[（說明）]`
- REQ 清單以「,」「，」「、」分隔；每一項是完整 ID（`REQ-<AREA>-<序號>`，序號至少三位），或只寫序號（沿用前一個完整 ID 的 `REQ-<AREA>-` 前綴）。
  例：`REQ-DAILYREPORT-001,005,007` ＝ REQ-DAILYREPORT-001、REQ-DAILYREPORT-005、REQ-DAILYREPORT-007。
- 說明只能是結尾的一段括號：從第一個「（」或「(」開始，到整段 scope 的最後一個字元才閉合（說明內可以有成對的括號）；
  括號中途閉合後又接著其他文字（例如每條需求各寫一段說明）→ 不合語法，避免後面的需求被靜默丟掉。
- 不以 `REQ-` 開頭的 scope（functional area 或其他自由文字）不是需求範圍：沿用原本的行為（綁定 revision 的全部需求）。
- 以 `REQ-`（不分大小寫）開頭卻不符語法 → ScopeError；new_run 拒絕建立 run。"""
import re

WORKFLOWS = ("spec-to-testcase",)
_FULL = re.compile(r"(REQ-[A-Z0-9]+-)([0-9]{3,})")
_SEQ = re.compile(r"[0-9]{3,}")
_SEP = re.compile(r"\s*[,，、]\s*")
_OPEN, _CLOSE = "（(", "）)"
HINT = "寫法：REQ-<AREA>-<序號>,<序號>,…（說明），例如 REQ-DAILYREPORT-001,005（T3RR 補強）；說明只能放在結尾的一段（）內；不是需求清單的 scope 不要以 REQ- 開頭"

class ScopeError(ValueError):
    pass

def _split_note(s: str) -> str:
    """回傳清單部分；說明必須是結尾的一段括號（中途閉合 → ScopeError）。"""
    i = next((k for k, ch in enumerate(s) if ch in _OPEN), None)
    if i is None:
        if any(ch in _CLOSE for ch in s): raise ScopeError(f"scope「{s}」有右括號但沒有左括號；{HINT}")
        return s
    depth = 0
    for k, ch in enumerate(s[i:], i):
        if ch in _OPEN: depth += 1
        elif ch in _CLOSE:
            depth -= 1
            if depth < 0 or (depth == 0 and k != len(s) - 1):
                raise ScopeError(f"scope「{s}」的說明在第 {k + 1} 個字元就結束，後面還有文字；{HINT}")
    if depth != 0: raise ScopeError(f"scope「{s}」的括號沒有閉合；{HINT}")
    return s[:i]

def parse(text) -> list[str] | None:
    """scope 文字 → 需求 ID 清單（依出現順序、去重）；不是需求清單 → None。"""
    if text is None: return None
    if not isinstance(text, str): raise ScopeError(f"scope 必須是字串（實際 {type(text).__name__}）；{HINT}")
    s = text.strip()
    if not re.match(r"(?i)REQ-", s): return None
    head = _split_note(s).strip()
    out, prefix = [], None
    for tok in _SEP.split(head):
        m = _FULL.fullmatch(tok)
        if m: prefix, rid = m.group(1), tok
        elif _SEQ.fullmatch(tok) and prefix: rid = prefix + tok
        else: raise ScopeError(f"scope「{text}」的「{tok}」不是需求 ID（完整 ID 或至少三位的序號）；{HINT}")
        if rid not in out: out.append(rid)
    return out

def requirement_ids(run: dict) -> list[str] | None:
    """run 的需求範圍；不適用的 workflow、沒有 scope、或 scope 不是需求清單 → None（不限範圍）。
    new_run 已拒絕不合語法的 scope；本變更之前建立的 run 若不合語法，沿用原本的行為（None）。"""
    if run.get("workflow_id") not in WORKFLOWS: return None
    try: return parse((run.get("input") or {}).get("scope"))
    except ScopeError: return None

def designable(r: dict) -> bool:
    """可以設計 TC 的需求：ACTIVE，且不是未經核准解決的 critical ambiguity（與 g_design 的檢查相同）。"""
    amb = r.get("ambiguity") or {}
    return r.get("status") == "ACTIVE" and not (amb.get("level") == "critical" and not amb.get("resolved_by_approval"))

def pin_issues(rs: list[str], reqs: dict, where: str) -> list[str]:
    """scope 與綁定 revision 的需求（{requirement_id: requirement}）對不上的問題：列了 revision 沒有的需求；或 scope 內沒有任何可設計的需求
    （G-DESIGN 不可能 PASS）。where：綁定 revision 的說明（訊息用）。"""
    unknown = [r for r in rs if r not in reqs]
    if unknown: return [f"run 的 scope 列出的 {', '.join(unknown)} 不在綁定的 {where}"]
    if not any(designable(reqs[r]) for r in rs):
        return [f"run 的 scope（{', '.join(rs)}）在綁定的 {where} 中沒有任何可設計的需求（全部非 ACTIVE 或為未解決的 critical ambiguity）"]
    return []

def packet_field(run: dict) -> dict | None:
    """派發包的 run_scope 欄位（Designer、Validator 用）；run 沒有 scope 或不適用 → None（不寫入）。"""
    if run.get("workflow_id") not in WORKFLOWS: return None
    raw = (run.get("input") or {}).get("scope")
    if raw is None: return None
    return {"raw": str(raw), "requirement_ids": requirement_ids(run)}
