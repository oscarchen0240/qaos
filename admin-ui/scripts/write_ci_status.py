#!/usr/bin/env python3
"""把工程 CI 的結果寫成控制台可讀的 ci-status.json。

兩種用法：
  1) 本機：直接跑兩個 pytest 並寫 admin-ui/data/ci-status.json
       python admin-ui/scripts/write_ci_status.py --run
  2) CI：從 junit xml 彙整（GitLab job 內用）
       python admin-ui/scripts/write_ci_status.py --from-junit reports/a.xml=runtime-pytest reports/b.xml=admin-ui-pytest --out reports/ci-status.json

schema（自定，控制台 /api/ci/status 讀）：
  {"status": "pass|fail|running", "sha": "...", "branch": "...", "updated_at": "...Z", "web_url": "...", "source": "local|gitlab",
   "jobs": [{"name": "...", "status": "pass|fail|running|skipped", "tests": 30, "failures": 0, "errors": 0, "duration_s": 3.9, "log": "..."}]}
不打網路；不寫 QAOS 任何目錄。
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "admin-ui" / "data" / "ci-status.json"
JOBS = [("runtime-pytest", ["tests/"]), ("admin-ui-pytest", ["admin-ui/backend/tests/"])]


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


def run_local() -> dict:
    jobs = []
    for name, paths in JOBS:
        t0 = dt.datetime.now()
        r = subprocess.run([sys.executable, "-m", "pytest", *paths, "-q", "-p", "no:cacheprovider"], cwd=ROOT, capture_output=True, text=True)
        tail = "\n".join(r.stdout.strip().splitlines()[-3:])
        summary = tail.splitlines()[-1] if tail else ""
        import re
        m_pass = re.search(r"(\d+) passed", summary); m_fail = re.search(r"(\d+) failed", summary); m_err = re.search(r"(\d+) error", summary)
        tests = (int(m_pass.group(1)) if m_pass else 0) + (int(m_fail.group(1)) if m_fail else 0)
        failures = int(m_fail.group(1)) if m_fail else 0
        errors = int(m_err.group(1)) if m_err else 0
        jobs.append({"name": name, "status": "pass" if r.returncode == 0 else "fail", "tests": tests, "failures": failures, "errors": errors,
                     "duration_s": round((dt.datetime.now() - t0).total_seconds(), 1), "log": tail[-2000:]})
    return {"status": "pass" if all(j["status"] == "pass" for j in jobs) else "fail", "sha": _git("rev-parse", "--short", "HEAD"), "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
            "updated_at": _now(), "web_url": os.environ.get("GITLAB_PIPELINE_URL", ""), "source": "local", "jobs": jobs}


def from_junit(pairs: list[str]) -> dict:
    jobs = []
    for pair in pairs:
        path, _, name = pair.partition("=")
        name = name or pathlib.Path(path).stem
        p = pathlib.Path(path)
        if not p.exists():
            jobs.append({"name": name, "status": "skipped", "tests": 0, "failures": 0, "errors": 0, "duration_s": 0, "log": f"{path} 不存在"}); continue
        root = ET.parse(p).getroot()
        suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
        tests = sum(int(s.get("tests", 0)) for s in suites); failures = sum(int(s.get("failures", 0)) for s in suites); errors = sum(int(s.get("errors", 0)) for s in suites)
        dur = round(sum(float(s.get("time", 0)) for s in suites), 1)
        jobs.append({"name": name, "status": "pass" if failures == 0 and errors == 0 else "fail", "tests": tests, "failures": failures, "errors": errors, "duration_s": dur, "log": ""})
    web = os.environ.get("CI_PIPELINE_URL") or os.environ.get("GITLAB_PIPELINE_URL", "")
    return {"status": "pass" if all(j["status"] == "pass" for j in jobs) else "fail", "sha": (os.environ.get("CI_COMMIT_SHORT_SHA") or _git("rev-parse", "--short", "HEAD")),
            "branch": os.environ.get("CI_COMMIT_REF_NAME") or _git("rev-parse", "--abbrev-ref", "HEAD"), "updated_at": _now(), "web_url": web, "source": "gitlab" if os.environ.get("CI") else "local", "jobs": jobs}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true", help="本機直接跑兩個 pytest")
    ap.add_argument("--from-junit", nargs="*", metavar="XML=JOB", help="從 junit xml 彙整")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    a = ap.parse_args()
    if not a.run and not a.from_junit:
        ap.error("--run 或 --from-junit 擇一")
    status = run_local() if a.run else from_junit(a.from_junit)
    out = pathlib.Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{status['status']} → {out}")
    return 0 if status["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
