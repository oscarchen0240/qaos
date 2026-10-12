import sqlite3
import datetime
from contextlib import contextmanager

from .config import DATA_DIR, DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS todos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'todo' CHECK (status IN ('todo','doing','done')),
  scheduled_date TEXT,
  due_date TEXT,
  estimate_min INTEGER,
  details TEXT NOT NULL DEFAULT '',
  linked_output_path TEXT,
  linked_report_id INTEGER,
  auto_complete INTEGER NOT NULL DEFAULT 1,   -- 關聯產出審閱完成時自動完成
  auto_completed_at TEXT,                     -- 由規則自動完成的時間（手動完成為 NULL）
  position REAL NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  completed_at TEXT
);

-- 每個檔案的追蹤（首次看到、mtime/size 變化、已讀）
CREATE TABLE IF NOT EXISTS output_files (
  output_path TEXT PRIMARY KEY,
  group_key TEXT NOT NULL,
  first_seen_at TEXT NOT NULL,
  last_seen_mtime REAL NOT NULL,
  last_seen_size INTEGER NOT NULL,
  acknowledged_at TEXT,
  updated_at TEXT NOT NULL
);

-- 審閱狀態以「群組」為單位：同一模組的 json/html 共用（group_key = AREA；無法辨識模組的檔案 = 檔案路徑）
CREATE TABLE IF NOT EXISTS output_reviews (
  group_key TEXT PRIMARY KEY,
  review_status TEXT NOT NULL DEFAULT 'pending' CHECK (review_status IN ('pending','reviewed','returned')),
  note TEXT NOT NULL DEFAULT '',
  updated_at TEXT NOT NULL
);

-- TC 層級審閱：模組狀態由此彙總（有 returned → returned；全部 reviewed → reviewed；否則 pending）
CREATE TABLE IF NOT EXISTS tc_reviews (
  group_key TEXT NOT NULL,
  testcase_id TEXT NOT NULL,
  review_status TEXT NOT NULL DEFAULT 'pending' CHECK (review_status IN ('pending','reviewed','returned')),
  reason TEXT NOT NULL DEFAULT '',   -- 退回理由（未來組成 bin/qaos approve --rationale 送回 QAOS）
  updated_at TEXT NOT NULL,
  PRIMARY KEY (group_key, testcase_id)
);

-- kind: manual（手動）/ output（產出完成自動建立）/ automation（自動化測試完成自動建立，M4 預留）
-- source_key：output → 產出群組 key；automation → test_runs.id；auto_md 為系統重新產生的段落，body_md 為人寫的結論
CREATE TABLE IF NOT EXISTS reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  summary TEXT NOT NULL DEFAULT '',
  body_md TEXT NOT NULL DEFAULT '',
  kind TEXT NOT NULL DEFAULT 'manual' CHECK (kind IN ('manual','output','automation')),
  source_key TEXT,
  auto_md TEXT NOT NULL DEFAULT '',
  auto_generated_at TEXT,
  auto_signature TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS reports_source ON reports(kind, source_key) WHERE source_key IS NOT NULL;

CREATE TABLE IF NOT EXISTS report_outputs (
  report_id INTEGER NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
  output_path TEXT NOT NULL,
  PRIMARY KEY (report_id, output_path)
);

-- 資料夾：TC 歸檔（跨模組），純管理系統資料
CREATE TABLE IF NOT EXISTS folders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  description TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS folder_items (
  folder_id INTEGER NOT NULL REFERENCES folders(id) ON DELETE CASCADE,
  group_key TEXT NOT NULL,
  testcase_id TEXT NOT NULL,
  added_at TEXT NOT NULL,
  PRIMARY KEY (folder_id, group_key, testcase_id)
);

-- 單據決定草稿（APR / CLR / BUG）：平台上標的決定與理由；sent_at = 使用者已把產生的指令貼去 QA session 執行
CREATE TABLE IF NOT EXISTS ticket_drafts (
  ticket_id TEXT PRIMARY KEY,
  kind TEXT NOT NULL CHECK (kind IN ('approval','clarification','bug')),
  decision TEXT,
  option TEXT,
  rationale TEXT NOT NULL DEFAULT '',
  per_item TEXT NOT NULL DEFAULT '{}',
  extra TEXT NOT NULL DEFAULT '{}',
  sent_at TEXT,
  sent_command TEXT,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
  session_id TEXT PRIMARY KEY,
  label TEXT NOT NULL DEFAULT '',
  tracked INTEGER NOT NULL DEFAULT 0,
  ignored INTEGER NOT NULL DEFAULT 0,
  first_seen_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

-- 自動化測試（M4 預留，尚未實作；欄位僅為未來接 runner 的最小骨架）
-- M5b：平台代為執行 bin/qaos 的紀錄（一筆一次執行；handoff_id 對應 .warroom/handoff.jsonl）
CREATE TABLE IF NOT EXISTS ticket_executions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ticket_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  action TEXT NOT NULL DEFAULT '',
  command TEXT NOT NULL,
  exit_code INTEGER,
  stdout TEXT NOT NULL DEFAULT '',
  stderr TEXT NOT NULL DEFAULT '',
  post_json TEXT NOT NULL DEFAULT '[]',
  run_id TEXT,
  run_status_after TEXT,
  next_task TEXT,
  session_id TEXT,
  handoff_id TEXT,
  hint TEXT NOT NULL DEFAULT '',
  started_at TEXT NOT NULL,
  ended_at TEXT NOT NULL
);

-- M7 測試執行（TestRail 式回合）：test_runs 一輪一筆；test_results 一條 TC 一筆，內容是建立回合時的 TC 快照
CREATE TABLE IF NOT EXISTS test_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  trigger TEXT NOT NULL DEFAULT 'manual',
  status TEXT NOT NULL DEFAULT 'planned',
  environment TEXT NOT NULL DEFAULT '',
  build TEXT NOT NULL DEFAULT '',
  notes TEXT NOT NULL DEFAULT '',
  created_by TEXT NOT NULL DEFAULT '',
  import_all INTEGER NOT NULL DEFAULT 0,
  report_id INTEGER,
  started_at TEXT,
  ended_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS test_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id INTEGER NOT NULL REFERENCES test_runs(id) ON DELETE CASCADE,
  position INTEGER NOT NULL DEFAULT 0,
  testcase_id TEXT NOT NULL,
  testcase_version INTEGER,
  group_key TEXT NOT NULL DEFAULT '',
  spec_id TEXT,
  spec_version TEXT,
  title TEXT NOT NULL DEFAULT '',
  priority TEXT,
  risk TEXT,
  requirement_ids TEXT NOT NULL DEFAULT '[]',
  preconditions TEXT NOT NULL DEFAULT '[]',
  steps TEXT NOT NULL DEFAULT '[]',
  expected_result TEXT NOT NULL DEFAULT '',
  result TEXT NOT NULL DEFAULT 'untested',
  actual_result TEXT NOT NULL DEFAULT '',
  notes TEXT NOT NULL DEFAULT '',
  duration_ms INTEGER,
  log_path TEXT,
  evidence TEXT NOT NULL DEFAULT '[]',
  executed_at TEXT,
  executed_by TEXT,
  qaos_execution_id TEXT,
  qaos_evidence_ids TEXT NOT NULL DEFAULT '[]',
  qaos_import_request TEXT,
  bug_run_id TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT ''
);
"""


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def init_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with connect() as con:
        _migrate_v1_reviews(con)
        _migrate_reports(con)
        con.executescript(SCHEMA)
        _migrate_todos(con)
        _migrate_tc_reviews(con)
        _migrate_testruns(con)


def _migrate_reports(con):
    cols = [r["name"] for r in con.execute("PRAGMA table_info(reports)").fetchall()]
    if cols and "kind" not in cols:
        con.execute("ALTER TABLE reports ADD COLUMN kind TEXT NOT NULL DEFAULT 'manual'")
        con.execute("ALTER TABLE reports ADD COLUMN source_key TEXT")
        con.execute("ALTER TABLE reports ADD COLUMN auto_md TEXT NOT NULL DEFAULT ''")
        con.execute("ALTER TABLE reports ADD COLUMN auto_generated_at TEXT")
        con.execute("ALTER TABLE reports ADD COLUMN auto_signature TEXT")
        con.execute("CREATE UNIQUE INDEX IF NOT EXISTS reports_source ON reports(kind, source_key) WHERE source_key IS NOT NULL")


def _migrate_tc_reviews(con):
    cols = [r["name"] for r in con.execute("PRAGMA table_info(tc_reviews)").fetchall()]
    if cols and "reason" not in cols:
        con.execute("ALTER TABLE tc_reviews ADD COLUMN reason TEXT NOT NULL DEFAULT ''")


def _migrate_todos(con):
    cols = [r["name"] for r in con.execute("PRAGMA table_info(todos)").fetchall()]
    if cols and "auto_complete" not in cols:
        con.execute("ALTER TABLE todos ADD COLUMN auto_complete INTEGER NOT NULL DEFAULT 1")
        con.execute("ALTER TABLE todos ADD COLUMN auto_completed_at TEXT")


def _migrate_v1_reviews(con):
    """M2 初版的 output_reviews 是以檔案為 key；改成群組共用後把舊表換名保留，不再使用。"""
    cols = [r["name"] for r in con.execute("PRAGMA table_info(output_reviews)").fetchall()]
    if cols and "output_path" in cols:
        con.execute("ALTER TABLE output_reviews RENAME TO output_reviews_v1")


@contextmanager
def connect():
    con = sqlite3.connect(DB_PATH, timeout=5)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = WAL")
    try:
        yield con
        con.commit()
    finally:
        con.close()


def rows(cur) -> list[dict]:
    return [dict(r) for r in cur.fetchall()]


def one(cur) -> dict | None:
    r = cur.fetchone()
    return dict(r) if r else None


def _migrate_testruns(con):
    """M4 stub 建的舊表只有幾個欄位；M7 補齊（ADD COLUMN 逐一補，缺什麼補什麼）。"""
    want_runs = {"environment": "TEXT NOT NULL DEFAULT ''", "build": "TEXT NOT NULL DEFAULT ''", "notes": "TEXT NOT NULL DEFAULT ''", "created_by": "TEXT NOT NULL DEFAULT ''",
                 "import_all": "INTEGER NOT NULL DEFAULT 0", "report_id": "INTEGER", "updated_at": "TEXT NOT NULL DEFAULT ''"}
    want_res = {"position": "INTEGER NOT NULL DEFAULT 0", "testcase_version": "INTEGER", "group_key": "TEXT NOT NULL DEFAULT ''", "spec_id": "TEXT", "spec_version": "TEXT",
                "title": "TEXT NOT NULL DEFAULT ''", "priority": "TEXT", "risk": "TEXT", "requirement_ids": "TEXT NOT NULL DEFAULT '[]'", "preconditions": "TEXT NOT NULL DEFAULT '[]'",
                "steps": "TEXT NOT NULL DEFAULT '[]'", "expected_result": "TEXT NOT NULL DEFAULT ''", "actual_result": "TEXT NOT NULL DEFAULT ''", "notes": "TEXT NOT NULL DEFAULT ''",
                "evidence": "TEXT NOT NULL DEFAULT '[]'", "executed_at": "TEXT", "executed_by": "TEXT", "qaos_execution_id": "TEXT", "qaos_evidence_ids": "TEXT NOT NULL DEFAULT '[]'",
                "qaos_import_request": "TEXT", "bug_run_id": "TEXT", "updated_at": "TEXT NOT NULL DEFAULT ''",
                # B2（R03／R04）：登記證據時的清單快照、開 bug 的指令、交接與執行紀錄是否補齊
                "qaos_evidence_snapshot": "TEXT", "bug_run_command": "TEXT", "bug_handoff_id": "TEXT"}
    # B2（R04）：單據 execute 先落一筆 pending 的執行紀錄，交接與 mark_sent 完成後才改 done；'done' 是既有資料的預設值
    want_exec = {"completion": "TEXT NOT NULL DEFAULT 'done'"}
    for table, want in (("test_runs", want_runs), ("test_results", want_res), ("ticket_executions", want_exec)):
        cols = [r["name"] for r in con.execute(f"PRAGMA table_info({table})").fetchall()]
        if not cols:
            continue
        for c, ddl in want.items():
            if c not in cols:
                con.execute(f"ALTER TABLE {table} ADD COLUMN {c} {ddl}")
                if (table, c) == ("test_results", "bug_handoff_id"):
                    # 新欄位只回填新欄位本身：此前開過 bug 且已寫過執行紀錄（含 handoff_id）的結果視為交接完成，
                    # 否則升級後它們都會被當成「待補交接」而重送一筆交接
                    con.execute("""UPDATE test_results SET bug_handoff_id = (SELECT handoff_id FROM ticket_executions e
                                       WHERE e.ticket_id = 'TESTRUN-' || test_results.run_id || '/' || test_results.id AND e.kind = 'bug_filing' AND e.handoff_id IS NOT NULL
                                       ORDER BY e.id DESC LIMIT 1)
                                   WHERE bug_run_id IS NOT NULL""")
