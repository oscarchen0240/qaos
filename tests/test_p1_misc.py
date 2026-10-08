"""P1：暫存檔殘留（9c、9l）、外部修改（9m、AC-07-12）、巢狀衍生輸出（AC-07-75、76）。"""
import pathlib, pytest
from tests import p1_util as U

def spec_args(v="1.0"):
    return ["spec", "import", U.FIXTURES / f"SPEC-AUTH-001-v{v}.md", "--spec-id", "SPEC-AUTH-001", "--version", v, "--product", "demo", "--area", "AUTH", "--by", "t"]

@pytest.mark.parametrize("entry", ["resend", "resume"])
def test_9c_9l_half_written_tmp_is_cleaned(entry):
    """暫存檔寫完、原子替換前中止 → 正式路徑沒有半寫內容；續做先清除本 op 的暫存檔再寫入。"""
    root = U.mkroot(); args = spec_args()
    assert U.q(root, *args, fault="before_replace:1").returncode == 86
    op = U.incomplete(root)[0]["op_id"]; step = U.plan_of(root, op)["steps"][0]
    target = pathlib.Path(root) / step["path"]
    tmps = list(target.parent.glob(f".qaos-tmp-{op[:16]}-*")); assert tmps, "應有本 op 的暫存檔"
    assert U.sha(target) == step["expected_before"]                       # 正式檔沒有半寫內容
    assert (U.q(root, *args) if entry == "resend" else U.q(root, "operation", "resume", op)).returncode == 0
    assert not list(pathlib.Path(root).rglob(".qaos-tmp-*")) and U.sha(target) == step["expected_after"]

def test_9m_12_external_modification_stops():
    """續做時目標業務檔既不是 before 也不是 after → 停止並報告，不覆寫；計畫維持未完成。"""
    root = U.mkroot(); args = spec_args()
    assert U.q(root, *args, fault="after_register").returncode == 86
    op = U.incomplete(root)[0]["op_id"]; step = U.plan_of(root, op)["steps"][0]
    target = pathlib.Path(root) / step["path"]; target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("external: true\n")                                  # 外部修改
    r = U.q(root, "operation", "resume", op); assert r.returncode != 0 and "外部修改" in r.stderr
    assert target.read_text() == "external: true\n" and U.incomplete(root)[0]["op_id"] == op

def _clr(root):
    U.import_auth_spec(root)
    r = U.q(root, "clarification", "new", "--product", "demo", "--area", "AUTH", "--spec-id", "SPEC-AUTH-001", "--spec-version", "1.0",
            "--question", "全形字元算幾個字？", "--consulted", "SPEC-AUTH-001@1.0", "--by", "oscar", check=True)
    return r.stdout.split()[0]

def test_75_answer_rebuilds_derived_in_same_executor():
    root = U.mkroot(); cid = _clr(root)
    U.q(root, "clarification", "answer", cid, "--answer", "算一個", "--answered-by", "pm", "--resolution", "requirement_clarified", "--by", "oscar", check=True)
    plan = U.last_plan(root)
    md = next(s for s in plan["steps"] if s["path"].endswith(f"{cid}.md"))
    assert md["step_id"].startswith("derived")                             # 衍生輸出在同一個計畫、同一個 executor 內
    assert "算一個" in (pathlib.Path(root) / md["path"]).read_text()
    assert U.incomplete(root) == []

@pytest.mark.parametrize("entry", ["resend", "resume"])
def test_76_answer_abort_before_derived_then_resume(entry):
    root = U.mkroot(); cid = _clr(root)
    args = ["clarification", "answer", cid, "--answer", "算一個", "--answered-by", "pm", "--resolution", "requirement_clarified", "--by", "oscar"]
    ref = U.mkroot(); _clr(ref); U.q(ref, *args, check=True)
    derived = next(s for s in U.last_plan(ref)["steps"] if s["step_id"].startswith("derived"))
    assert U.q(root, *args, fault=f"before_output:{derived['seq']}").returncode == 86
    op = U.incomplete(root)[0]["op_id"]
    assert "（待回覆）" in (pathlib.Path(root) / derived["path"]).read_text()     # 衍生輸出還是舊的
    assert (U.q(root, *args) if entry == "resend" else U.q(root, "operation", "resume", op)).returncode == 0
    assert "算一個" in (pathlib.Path(root) / derived["path"]).read_text() and U.incomplete(root) == []
