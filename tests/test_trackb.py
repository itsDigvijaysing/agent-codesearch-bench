from pathlib import Path

from csbench.dataset import Task
from csbench.trackb import CLAUDE_MD_HEADING, load_config, parse_locations, score, session_request

ROOT = Path(__file__).parent.parent
TASK = Task(
    "t1",
    "org/proj",
    "https://github.com/org/proj.git",
    "python",
    "abc",
    "Bug in x",
    "Verified",
    {"pkg/a.py": [(10, 19)], "pkg/b.py": [(1, 5)]},
)


def test_parse_locations_takes_last_json_block():
    text = (
        'thinking ```json\n{"locations": [{"file": "old.py"}]}\n```\nfinal:\n'
        '```json\n{"locations": [{"file": "./pkg/a.py", "start_line": 12, "end_line": 15},'
        ' {"file": "/home/user/proj/pkg/b.py", "start_line": 3},'
        ' {"bad": 1}]}\n```'
    )
    assert parse_locations(text, "org/proj", 20) == [("pkg/a.py", 12, 15), ("pkg/b.py", 3, 3)]
    assert parse_locations("no json here", "org/proj", 20) == []
    assert parse_locations("```json\n{broken\n```", "org/proj", 20) == []


def test_score_and_failed_session():
    rec = {
        "status": "ok",
        "input_tokens": 100,
        "output_tokens": 20,
        "cache_read_tokens": 5,
        "num_turns": 4,
        "duration_s": 30,
        "result_text": '```json\n{"locations": [{"file": "pkg/a.py", "start_line": 10, '
        '"end_line": 19}]}\n```',
    }
    s = score(TASK, rec, 20)
    assert s["file_recall@1"] == 0.5 and s["mrr"] == 1.0 and s["span_precision"] == 1.0
    assert s["total_tokens"] == 125 and s["ok"]
    failed = score(TASK, {"status": "error"}, 20)
    assert failed["file_recall@10"] == 0 and failed["total_tokens"] is None


def test_session_request_differs_only_by_arm_setup():
    cfg, root = load_config(ROOT / "configs" / "trackb.yaml", "trackb-haiku")
    assert cfg["model"] == "claude-haiku-5-5" and list(cfg["arms"]) == [
        "baseline",
        "semble",
        "graphify",
    ]
    pilot, _ = load_config(ROOT / "configs" / "trackb.yaml", "trackb-pilot")
    assert list(pilot["arms"]) == ["baseline", "semble"] and pilot["limit"] == 10
    base = session_request(cfg, root, TASK, "baseline")
    tool = session_request(cfg, root, TASK, "semble")
    assert "CLAUDE.md" not in base["prompt"] and "semble search" in tool["prompt"]
    assert tool["prompt"].startswith(CLAUDE_MD_HEADING) and "<!--" not in tool["prompt"]
    graph = session_request(cfg, root, TASK, "graphify")
    setup = cfg["arms"]["graphify"]["setup"]
    assert graph["prompt"].split("---\n\n", 1)[1].replace(setup, "") == base["prompt"]
    assert base["source_revision"] == "abc" and "<issue>\nBug in x\n</issue>" in base["prompt"]
    assert tool["prompt"].split("---\n\n", 1)[1] == base["prompt"]  # preinstalled: no setup


def test_clean_normalizes_whitespace():
    from csbench.trackb import clean

    assert clean("a  \r\nb\t \r\n\r\n") == "a\nb"
