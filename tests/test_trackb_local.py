import json
from pathlib import Path

from csbench import trackb_local
from csbench.trackb_local import parse_stream, sandbox


def _stream(*events):
    return [json.dumps(e) for e in events]


def test_parse_stream_counts_tool_use_and_reads_the_result():
    lines = _stream(
        {"type": "system", "subtype": "init", "model": "m", "session_id": "s",
         "claude_code_version": "2.1"},
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Bash", "input": {"command": "semble search 'x' ."}},
            {"type": "tool_use", "name": "Bash", "input": {"command": "curl -s example.com"}},
            {"type": "tool_use", "name": "Task", "input": {}},
        ]}},
        {"type": "result", "subtype": "success", "is_error": False, "result": "done",
         "num_turns": 3, "duration_ms": 12500, "total_cost_usd": 0.01,
         "usage": {"input_tokens": 5, "output_tokens": 7, "cache_read_input_tokens": 100,
                   "cache_creation_input_tokens": 20,
                   "server_tool_use": {"web_search_requests": 0, "web_fetch_requests": 1}},
         "permission_denials": [{"tool_name": "Read"}]},
    )  # fmt: skip
    rec = parse_stream(lines + ["not json"], "semble")
    assert rec["status"] == "ok" and rec["model"] == "m" and rec["duration_s"] == 12.5
    assert rec["tool_calls"] == 1 and rec["network_commands"] == 1 and rec["subagent_calls"] == 1
    assert rec["cache_read_tokens"] == 100 and rec["web_requests"] == 1
    assert rec["permission_denials"] == 1
    assert parse_stream(lines, "baseline")["tool_calls"] is None


def test_parse_stream_without_result_is_an_error_and_limit_is_detected():
    assert parse_stream([], "baseline")["status"] == "error"
    hit = _stream({"type": "result", "subtype": "success", "is_error": True,
                   "result": "Claude AI usage limit reached"})  # fmt: skip
    assert parse_stream(hit, "baseline")["status"] == "limit"
    hit = _stream({"type": "result", "subtype": "success", "is_error": True,
                   "result": "You've hit your 5-hour limit · resets 11pm"})  # fmt: skip
    assert parse_stream(hit, "baseline")["status"] == "limit"
    hit = _stream({"type": "result", "subtype": "success", "is_error": True, "result": "",
                   "api_error_status": 429})  # fmt: skip
    assert parse_stream(hit, "baseline")["status"] == "limit"


def test_sandbox_hides_home_and_tmp_and_mounts_in_order(tmp_path, monkeypatch):
    monkeypatch.setattr(trackb_local, "WORK", tmp_path / "work")
    repo = Path("/home/user/proj")
    mounts = [("bind", tmp_path / "home", Path("/home/user")), ("bind", tmp_path / "r", repo)]
    argv = sandbox(repo, mounts)
    tmpfs = [argv[i + 1] for i, a in enumerate(argv) if a == "--tmpfs"]
    assert {"/home", "/tmp", "/var/tmp", "/run/user"} <= set(tmpfs)
    assert str(tmp_path / "work") in tmpfs or (tmp_path / "work").is_relative_to("/tmp")
    binds = [(argv[i + 1], argv[i + 2]) for i, a in enumerate(argv) if a == "--bind"]
    assert binds == [(str(tmp_path / "home"), "/home/user"), (str(tmp_path / "r"), str(repo))]
    assert max(i for i, a in enumerate(argv) if a == "--tmpfs") < argv.index("--bind")
    assert argv[argv.index("--chdir") + 1] == str(repo)


def test_session_paths_and_env_name_neither_benchmark_nor_arm(tmp_path, monkeypatch):
    from csbench.dataset import Task

    monkeypatch.setattr(trackb_local, "WORK", tmp_path)
    task = Task("SWE-Bench-Verified__python__x__abcd1234", "org/proj", "u", "python", "c",
                "issue", "Verified", {})  # fmt: skip
    for arm in ("baseline", "semble"):
        inside = [str(dst) for _, _, dst in trackb_local.arm_mounts(task, tmp_path / "t", arm)]
        env = " ".join(trackb_local.sandbox_env().values())
        for leak in ("SWE", "Verified", arm, "csbench", "bench"):
            assert not any(leak in p for p in inside) and leak not in env
        assert "/home/user/proj" in inside
