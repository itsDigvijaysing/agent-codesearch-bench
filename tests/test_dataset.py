import json

from csbench.dataset import normalize_path, parse_gold


def test_normalize_path():
    assert normalize_path("./a/b.py") == "a/b.py"
    assert normalize_path("/a/b.py") == "a/b.py"
    assert normalize_path("a\\b.py") == "a/b.py"


def test_parse_gold_merges_per_file():
    gold = json.dumps(
        [
            {"file": "a.py", "start_line": 5, "end_line": 9, "content": ""},
            {"file": "./a.py", "start_line": 8, "end_line": 12, "content": ""},
            {"file": "b.py", "start_line": 3, "end_line": 3, "content": ""},
        ]
    )
    assert parse_gold(gold) == {"a.py": [(5, 12)], "b.py": [(3, 3)]}
