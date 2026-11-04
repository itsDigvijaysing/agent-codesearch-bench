import subprocess

from csbench.runner import resolve_hits, run_worker


def test_resolve_hits_clips_and_handles_missing(tmp_path):
    (tmp_path / "a.py").write_text("x = 1\ny = 2\nz = 3\n")
    hits = [
        {"file": "./a.py", "start": 2, "end": 99},
        {"file": str(tmp_path / "a.py"), "start": None, "end": None},
        {"file": "missing.py", "start": 1, "end": 5},
    ]
    r = resolve_hits(tmp_path, hits, "o200k_base")
    assert (r[0].file, r[0].start, r[0].end) == ("a.py", 2, 3)
    assert (r[1].start, r[1].end) == (1, 3) and r[1].tokens > r[0].tokens
    assert r[2].file == "missing.py" and r[2].tokens == 0


def test_resolve_hits_counts_returned_text(tmp_path):
    (tmp_path / "min.js").write_text("var a=1;" * 2000 + "\n")
    whole, sliced = resolve_hits(
        tmp_path,
        [
            {"file": "min.js", "start": 1, "end": 1},
            {"file": "min.js", "start": 1, "end": 1, "text": "var a=1;"},
        ],
        "o200k_base",
    )
    assert whole.tokens > 1000 and 0 < sliced.tokens < 10
    assert (sliced.start, sliced.end) == (1, 1)


def test_worker_runs_in_subprocess(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "m.py").write_text("def bulk_update():\n    pass\n")
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    spec = {
        "adapter": "bm25",
        "params": {"chunk_lines": 10},
        "repo": str(repo),
        "index_dir": str(tmp_path / "idx"),
        "query": "bulk update",
        "top_k": 5,
        "out": str(tmp_path / "out.json"),
    }
    out = run_worker(spec, timeout=60)
    assert out["status"] == "ok", out.get("error")
    assert out["hits"][0]["file"] == "m.py"
    assert 0 < out["peak_rss_mib"] < 2000
