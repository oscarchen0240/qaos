#!/usr/bin/env python3
"""2026-09-13 收件：~/Downloads 的實體機台開發包、紅利幣別文件、bug 單、RD 回報、QA 筆記 → QAOS 各正式/收件目錄。可重跑。"""
import re, sys, html as H, base64, shutil, pathlib, io
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from tools.qaos import store, ids, schema, clarification as clr
from tools.qaos.cli import main as cli

DL = pathlib.Path("/Users/oscar/Downloads"); PKG = DL / "實體機台開發包_20260904"
BY = "oscarchen@blockaction.tech"; PRODUCT = "ba-admin"
INTAKE = store.ROOT / "intake"
for d in ("bugs", "rd-reports", "qa-notes", "package-20260904", "pm-decisions"): (INTAKE / d).mkdir(parents=True, exist_ok=True)

def vnum(tag):  # v07 → 0.7, v04 → 0.4
    n = int(tag[1:]); return f"{n // 10}.{n % 10}"

# ---------- 1. Spec ----------
SPECS = [  # (檔案, area, spec_id, title, version)
    (PKG / "spec/前言與通用規則_spec_v01.md", "COMMON", "SPEC-COMMON-001", "前言與通用規則", "0.1"),
    (PKG / "spec/實體機台_spec_v07.md", "ARCADE", "SPEC-ARCADE-001", "實體機台（正本）", "0.7"),
    (PKG / "spec/站台列表_spec_v04.md", "SITELIST", "SPEC-SITELIST-001", "站台列表擴充", "0.4"),
    (PKG / "spec/創建會員帳號_spec_v01.md", "ACCOUNT", "SPEC-ACCOUNT-001", "帳號與機台管理（創建會員帳號）", "0.1"),
    (PKG / "spec/機台金流與場次_spec_v01.md", "CASHFLOW", "SPEC-CASHFLOW-001", "機台金流與場次", "0.1"),
    (PKG / "spec/機台交易紀錄_spec_v01.md", "TXLOG", "SPEC-TXLOG-001", "機台交易紀錄", "0.1"),
    (PKG / "spec/洗分出金核實_spec_v01.md", "CASHOUT", "SPEC-CASHOUT-001", "洗分出金核實", "0.1"),
    (PKG / "spec/場館日結報表_spec_v01.md", "DAILYREPORT", "SPEC-DAILYREPORT-001", "場館日結報表", "0.1"),
    (PKG / "spec/機台場館平台規則_spec_v01.md", "PLATFORMRULE", "SPEC-PLATFORMRULE-001", "機台場館平台規則", "0.1"),
    (PKG / "spec/機台更新包_spec_v01.md", "UPDATEPACK", "SPEC-UPDATEPACK-001", "機台功能更新包", "0.1"),
    (PKG / "spec/會員與加盟商_spec_v02.md", "MEMBER", "SPEC-MEMBER-001", "會員與加盟商（客戶可見章節）", "0.2"),
    (DL / "17-給QA的說明.md", "BONUSCCY", "SPEC-BONUSCCY-001", "17 給 QA 的說明（系統記帳幣別改為每站自訂）", "1.0"),
    (DL / "18-紅利幣別盤點.md", "BONUSCCY", "SPEC-BONUSCCY-002", "18 紅利（彩金）幣別盤點", "1.0"),
    (DL / "20-紅利調整說明.md", "BONUSCCY", "SPEC-BONUSCCY-003", "20 紅利調整說明", "1.0"),
]
AREA_TITLES = {"COMMON": "前言與通用規則", "ARCADE": "實體機台正本", "SITELIST": "站台列表", "ACCOUNT": "帳號與機台管理", "CASHFLOW": "機台金流與場次", "TXLOG": "機台交易紀錄",
               "CASHOUT": "洗分出金核實", "DAILYREPORT": "場館日結報表", "PLATFORMRULE": "機台場館平台規則", "UPDATEPACK": "機台功能更新包", "MEMBER": "會員與加盟商",
               "BONUSCCY": "紅利幣別", "SCREENMGMT": "畫面管理", "SYSUSER": "系統使用者"}
PROTO = {"SITELIST": "站台列表_proto_v04.html", "ACCOUNT": "創建會員帳號_proto_v01.html", "TXLOG": "機台交易紀錄_proto_v01.html", "CASHOUT": "洗分出金核實_proto_v01.html",
         "DAILYREPORT": "場館日結報表_proto_v01.html", "UPDATEPACK": "機台更新包_proto_v01.html", "MEMBER": "會員列表_proto_v01.html"}
for f, area, sid, title, ver in SPECS:
    d = store.spec_dir(sid)
    if d and any(v["spec_version"] == ver for v in store.load(d / "spec.yaml")["versions"]): print("skip spec", sid, ver); continue
    cli(["spec", "import", str(f), "--spec-id", sid, "--version", ver, "--product", PRODUCT, "--area", area, "--title", title, "--area-title", AREA_TITLES[area],
         "--source", f"downloads/{f.relative_to(DL)} (實體機台開發包 2026-09-04 快照；正本以 git ba-spec 為準)" if PKG in f.parents else f"downloads/{f.name}", "--by", BY])
for area, proto in PROTO.items():
    sid = next(s[2] for s in SPECS if s[1] == area); dst = store.spec_dir(sid) / "attachments"; dst.mkdir(exist_ok=True)
    if not (dst / proto).exists(): shutil.copyfile(PKG / "proto" / proto, dst / proto)
for f in (PKG / "README.md", PKG / "開發總清單.html"): shutil.copyfile(f, INTAKE / "package-20260904" / f.name)

# ---------- 2. 測試環境 / QA 筆記 / RD 回報 ----------
env = store.ROOT / "docs" / "environments"; env.mkdir(exist_ok=True)
shutil.copyfile(DL / "機台開發用測試頁.md", env / "ba-admin-arcade-test.md")
for f in ("紅利幣別改動_QA整理.md", "機台與多幣別站台_測試checklist.md", "機台測試checklist.html", "機台測試checklist_v02.html"): shutil.copyfile(DL / f, INTAKE / "qa-notes" / f)
for f in ("0904files_修復回報.md", "2026-09-04.md", "2026-09-04_1500後.md"): shutil.copyfile(DL / f, INTAKE / "rd-reports" / f)
shutil.copyfile(DL / "0904files.zip", INTAKE / "bugs" / "0904files.zip")

# ---------- 3. Bug 單 → intake/bugs + ManualTestRecord + Evidence ----------
def html_to_text_and_images(path):
    s = path.read_text(encoding="utf-8", errors="ignore")
    imgs = re.findall(r'<img[^>]+src="data:image/(png|jpeg|jpg|webp);base64,([^"]+)"', s)
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", s, flags=re.S); t = re.sub(r"<img[^>]+>", "\n[圖]\n", t); t = re.sub(r"<[^>]+>", "\n", t)
    t = H.unescape(t); t = re.sub(r"[ \t]+", " ", t); t = re.sub(r"\n\s*\n+", "\n", t).strip()
    return t, imgs

def md_sections(text):
    secs = {}; cur = None
    for line in text.splitlines():
        m = re.match(r"^\*\*(.+?)[:：]\*\*\s*(.*)$", line.strip())
        if m: cur = m.group(1).strip(); secs[cur] = m.group(2).strip(); continue
        if cur: secs[cur] += "\n" + line
    return {k: v.strip() for k, v in secs.items()}

BUGS = [  # (檔案, area, spec_id, spec_version, tested_at)
    (DL / "bug單_場館日結報表欄位缺失.md", "DAILYREPORT", "SPEC-DAILYREPORT-001", "0.1", "2026-09-08"),
    (DL / "bug單_洗分出金核實入口角標計數與頁面實際筆數不符.md", "CASHOUT", "SPEC-CASHOUT-001", "0.1", "2026-09-07"),
    (DL / "bug單_系統使用者列表查無登入中帳號.md", "PLATFORMRULE", "SPEC-PLATFORMRULE-001", "0.1", "2026-09-04"),
    (DL / "bug單_ZZAA00264上層站台異常可自由選取.html", "SITELIST", "SPEC-SITELIST-001", "0.4", "2026-09-04"),
    (DL / "bug單_上層站台選單異常與根層機台建立受阻.html", "SITELIST", "SPEC-SITELIST-001", "0.4", "2026-09-04"),
    (DL / "bug單_子站台類型與核心貨幣顯示錯誤.html", "SITELIST", "SPEC-SITELIST-001", "0.4", "2026-09-04"),
    (DL / "bug單_不支援TWD遊戲商於機台場館顯示異常.html", "SCREENMGMT", None, None, "2026-09-08"),
    (DL / "bug單_畫面管理OFF未實際隱藏前台TAB.html", "SCREENMGMT", None, None, "2026-09-08"),
]
existing = {store.load(p).get("notes", "") for p in (store.ROOT / "testcases" / "manual").glob("MAN-*.yaml")}
areas = store.load(f"specs/{PRODUCT}/areas.yaml")
for f, area, sid, sver, date in BUGS:
    areas["areas"].setdefault(area, {"title": AREA_TITLES[area]})
    shutil.copyfile(f, INTAKE / "bugs" / f.name)
    if any(f.name in n for n in existing): print("skip bug", f.name); continue
    if f.suffix == ".md":
        text = f.read_text(encoding="utf-8"); imgs = []
        title = re.search(r"## Title\s*\n+(.+)", text).group(1).strip(); secs = md_sections(text)
        steps_src = secs.get("複製步驟") or secs.get("問題詳述", "")
        env_ = secs.get("測試環境", ""); acct = secs.get("測試帳號", ""); detail = secs.get("問題詳述", ""); expected = secs.get("預期結果", "")
    else:
        text, imgs = html_to_text_and_images(f)
        title = text.splitlines()[0].replace("Bug單：", "").strip()
        def grab(label):
            m = re.search(rf"\n{label}\n(.*?)(?=\n(?:遊戲商|遊戲名稱|測試環境|測試帳號|測試時間|問題詳述|預期結果|複製步驟|API URL|Request|Response)\n|\Z)", text, re.S); return m.group(1).strip() if m else ""
        env_ = grab("測試環境") or (re.search(r"測試環境：([^｜\n]+)", text) or [None, ""])[1]; acct = grab("測試帳號"); detail = grab("問題詳述"); expected = grab("預期結果"); steps_src = grab("複製步驟") or detail
    steps = [re.sub(r"^\d+[\.、]\s*", "", l).strip() for l in steps_src.splitlines() if re.match(r"^\s*\d+[\.、]\s", l)] or [l.strip() for l in steps_src.splitlines() if l.strip()][:8]
    # Evidence：整份 bug 單文字 + 內嵌圖片
    owner = "bug-intake-20260913"; (store.ROOT / "evidence" / owner).mkdir(parents=True, exist_ok=True); ev_ids = []
    eid = ids.alloc("EVD"); uri = f"evidence/{owner}/{eid}.md"; (store.ROOT / uri).write_text(text, encoding="utf-8")
    ev = {"evidence_id": eid, "type": "other", "uri": uri, "sha256": store.sha256_text(text), "mime_type": "text/markdown", "captured_at": f"{date}T00:00:00Z", "captured_by": BY, "description": f"bug 單全文：{f.name}", "inline_content": text}
    assert not schema.errors(ev, "execution/evidence.schema.json"); store.save(f"evidence/{owner}/{eid}.yaml", ev); ev_ids.append(eid)
    for i, (ext, b64) in enumerate(imgs, 1):
        eid = ids.alloc("EVD"); ext = "jpg" if ext == "jpeg" else ext; uri = f"evidence/{owner}/{eid}.{ext}"
        (store.ROOT / uri).write_bytes(base64.b64decode(b64))
        ev = {"evidence_id": eid, "type": "screenshot", "uri": uri, "sha256": store.sha256_file(uri), "mime_type": f"image/{ext}", "size_bytes": (store.ROOT / uri).stat().st_size, "captured_at": f"{date}T00:00:00Z", "captured_by": BY, "description": f"{f.name} 圖{i}"}
        assert not schema.errors(ev, "execution/evidence.schema.json"); store.save(f"evidence/{owner}/{eid}.yaml", ev); ev_ids.append(eid)
    rid = ids.alloc("MAN")
    rec = {"record_id": rid, "title": title[:200], "tester": BY, "tested_at": f"{date}T00:00:00Z", "product": PRODUCT, "functional_area": area,
           "environment": (env_ or "stage-arcade-violet.springkyle.online")[:300], "preconditions": [f"測試帳號：{acct}"] if acct else [],
           "steps_performed": steps or ["（見 bug 單全文）"], "observed_result": detail[:2000] or title, "outcome": "fail", "evidence_ids": ev_ids,
           "notes": f"source: downloads/{f.name}; 預期結果（原單）: {expected[:600]}"}
    if sid: rec["spec_hint"] = {"spec_id": sid, "spec_version": sver}
    errs = schema.errors(rec, "testcase/manual-test-record.schema.json"); assert not errs, (f.name, errs)
    store.save(f"testcases/manual/{rid}.yaml", rec); store.audit(None, BY, "IMPORT_MANUAL_RECORD", f"{rid} ← {f.name} evidence={ev_ids}")
    print("bug →", rid, f.name, f"({len(imgs)} imgs)")
store.save(f"specs/{PRODUCT}/areas.yaml", areas)

# ---------- 4. PM 已結案疑問 → Clarification（回填） ----------
pm = DL / "待PM確認_站長最高權限定義疑問_精簡版.html"
if not pm.exists(): pm = pathlib.Path("/tmp/0904files/待PM確認_站長最高權限定義疑問_精簡版.html")
shutil.copyfile(pm, INTAKE / "pm-decisions" / pm.name)
if not any(c["question"].startswith("「站長＝最高權限」") for c in clr.list_(open_only=False)):
    c = clr.new(PRODUCT, "PLATFORMRULE", "SPEC-PLATFORMRULE-001", "0.1", "「站長＝最高權限」的定義是否仍有效？三份 spec 的權限層級互相矛盾", BY,
                context="前言與通用規則_spec_v01 寫站長=最高權限；站台列表_spec_v04 為 Admin/站長兩層；機台場館平台規則_spec_v01 為 Admin/站長/操作員三層。延伸：ZZAA00264（站長，指派在 admin）可自由選取上層站台是否為 bug？",
                options=["以前言為準：站長最高", "以功能 spec 三層模型為準：管理員 > 站長 > 操作員"], requirement_id=None, impact="影響站台列表 / 平台規則所有權限相關 TC 的 expected")
    clr.ask(c["clarification_id"], "PM", BY)
    clr.answer(c["clarification_id"], "以功能 spec 三層模型為準：管理員（最高）＞站長＞操作員。原則：可見範圍由所屬站台決定、權限層級由角色決定，兩者分開。ZZAA00264 案確認為 bug（站長不應有自由選取上層站台的管理員專屬能力）。前言「站長＝最高權限」已過時。",
               "PM", "requirement_clarified", BY)
    print("clarification backfilled:", c["clarification_id"])
clr.build_index()
print("intake done")
