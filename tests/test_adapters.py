import shutil
import subprocess

import pytest

from csbench.adapters.bm25 import BM25Adapter, chunk, tokenize
from csbench.adapters.grep import GrepAdapter, extract_terms


def test_extract_terms_rule():
    text = (
        "Calling `QuerySet.bulk_update()` on MyModel fails in django/db/models/query.py.\n"
        "It's raising 'invalid value' and parseJSON is unused; __init__ too. x_y"
    )
    terms = extract_terms(text)
    assert terms[0] == "django/db/models/query.py"
    for t in [
        "QuerySet.bulk_update",
        "MyModel",
        "parseJSON",
        "bulk_update",
        "__init__",
        "QuerySet.bulk_update()",
        "invalid value",
    ]:
        assert t in terms
    assert "x_y" in terms and not any(t.startswith("s raising") for t in terms)
    assert len(extract_terms(" ".join(f"name_{i}" for i in range(100)), 64)) == 64


def test_extract_terms_drops_non_identifiers():
    text = (
        "See https://github.com/org/repo/issues/1 and keras.io or www.unidata.ucar.edu, "
        "mail me@example.com, e.g. this, i.e. that. Use 'where' but keep 'pop from empty' "
        "and `xr.where` and np.c_"
    )
    terms = extract_terms(text)
    for t in [
        "keras.io",
        "www.unidata.ucar.edu",
        "e.g",
        "i.e",
        "where",
        "example.com",
        "github.com/org/repo",
    ]:
        assert t not in terms
    assert {"pop from empty", "xr.where", "np.c_"} <= set(terms)


def test_tokenize_splits_code_identifiers():
    assert tokenize("parseJSONValue snake_case HTTPServer x") == [
        "parse",
        "json",
        "value",
        "snake",
        "case",
        "http",
        "server",
    ]


def test_chunk():
    lines = [f"{i}\n" for i in range(1, 8)]
    assert [(s, e) for s, e, _ in chunk(lines, 3)] == [(1, 3), (4, 6), (7, 7)]


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "models.py").write_text(
        "class QuerySet:\n" + "    pass\n" * 20 + "    def bulk_update(self):\n        pass\n"
    )
    (tmp_path / "pkg" / "other.py").write_text("def unrelated():\n    return 1\n")
    (tmp_path / "README.md").write_text("QuerySet docs\n")
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    return tmp_path


@pytest.mark.skipif(shutil.which("rg") is None, reason="ripgrep not installed")
def test_grep_adapter_ranks_by_hits(repo, tmp_path):
    a = GrepAdapter(context=1)
    a.build(repo, tmp_path / "idx")
    hits = a.search("`QuerySet.bulk_update` breaks QuerySet", top_k=10)
    assert hits[0].file == "pkg/models.py"
    assert {h.file for h in hits} == {"pkg/models.py", "README.md"}
    assert (hits[0].start, hits[0].end) == (1, 2)


@pytest.mark.skipif(shutil.which("rg") is None, reason="ripgrep not installed")
def test_grep_distinct_ranking(repo, tmp_path):
    (repo / "pkg" / "many.py").write_text("QuerySet\n" * 5)
    query = "QuerySet fails in bulk_update"
    by_hits = GrepAdapter(context=0)
    by_distinct = GrepAdapter(context=0, rank="distinct")
    for a in (by_hits, by_distinct):
        a.build(repo, tmp_path / "idx")
    assert by_hits.search(query, top_k=1)[0].file == "pkg/many.py"
    assert by_distinct.search(query, top_k=1)[0].file == "pkg/models.py"


def test_bm25_adapter(repo, tmp_path):
    a = BM25Adapter(chunk_lines=10)
    a.build(repo, tmp_path / "idx")
    hits = a.search("bulk_update on a queryset", top_k=3)
    assert hits[0].file == "pkg/models.py" and hits[0].start == 21
    assert a.search("zzzz nothing", top_k=3) == []


def test_registry():
    from csbench.adapters import get_adapter

    for name in ["grep", "bm25", "semble"]:
        assert get_adapter(name).name == name
    with pytest.raises(KeyError):
        get_adapter("nope")
