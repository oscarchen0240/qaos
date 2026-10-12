"""spec-to-testcase 的 run scope（ADR-013）：input.scope 寫成需求清單時，G-DESIGN 只要求 scope 內需求的覆蓋與規則。

語法：`<REQ 清單>[（說明）]`
- REQ 清單以「,」「，」「、」分隔；每一項是完整 ID（`REQ-<AREA>-<序號>`），或只寫序號（沿用前一個完整 ID 的 `REQ-<AREA>-` 前綴）。
  例：`REQ-DAILYREPORT-001,005,007` ＝ REQ-DAILYREPORT-001、REQ-DAILYREPORT-005、REQ-DAILYREPORT-007。
- 說明放在第一個「（」或「(」之後，不參與解析。
- 不以 `REQ-` 開頭的 scope（functional area 或其他自由文字）不是需求範圍：沿用原本的行為（綁定 revision 的全部需求）。
- 以 `REQ-`（不分大小寫）開頭卻不符語法 → ScopeError；new_run 拒絕建立 run。"""
import re

WORKFLOWS = ("spec-to-testcase",)
_FULL = re.compile(r"(REQ-[A-Z0-9]+-)([0-9]+)")
_SEQ = re.compile(r"[0-9]+")
_SEP = re.compile(r"\s*[,，、]\s*")

class ScopeError(ValueError):
    pass

def parse(text) -> list[str] | None:
    """scope 文字 → 需求 ID 清單（依出現順序、去重）；不是需求清單 → None。"""
    if text is None: return None
    if not isinstance(text, str): raise ScopeError(f"scope 必須是字串（實際 {type(text).__name__}）")
    s = text.strip()
    if not re.match(r"(?i)REQ-", s): return None
    head = re.split(r"[（(]", s, maxsplit=1)[0].strip()
    out, prefix = [], None
    for tok in _SEP.split(head):
        m = _FULL.fullmatch(tok)
        if m: prefix, rid = m.group(1), tok
        elif _SEQ.fullmatch(tok) and prefix: rid = prefix + tok
        else:
            raise ScopeError(f"scope「{text}」的「{tok}」不是需求 ID：以 REQ- 開頭的 scope 必須是 REQ-<AREA>-<序號> 清單（以逗號分隔，"
                             "後面的項目可只寫序號），說明放在（）內；不是需求清單的 scope 不要以 REQ- 開頭")
        if rid not in out: out.append(rid)
    return out

def requirement_ids(run: dict) -> list[str] | None:
    """run 的需求範圍；不適用的 workflow、沒有 scope、或 scope 不是需求清單 → None（不限範圍）。
    new_run 已拒絕不合語法的 scope；本變更之前建立的 run 若不合語法，沿用原本的行為（None）。"""
    if run.get("workflow_id") not in WORKFLOWS: return None
    try: return parse((run.get("input") or {}).get("scope"))
    except ScopeError: return None

def packet_field(run: dict) -> dict | None:
    """派發包的 run_scope 欄位（Designer、Validator、TC Risk Reviewer 用）；run 沒有 scope 或不適用 → None（不寫入）。"""
    if run.get("workflow_id") not in WORKFLOWS: return None
    raw = (run.get("input") or {}).get("scope")
    if raw is None: return None
    return {"raw": str(raw), "requirement_ids": requirement_ids(run)}
