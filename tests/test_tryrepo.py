import subprocess

from csbench.tryrepo import gold_from_diff, message, mine_tasks

DIFF = """diff --git a/pkg/a.py b/pkg/a.py
--- a/pkg/a.py
+++ b/pkg/a.py
@@ -10,2 +10,3 @@ def f():
@@ -30,0 +32 @@ def g():
diff --git a/tests/test_a.py b/tests/test_a.py
--- a/tests/test_a.py
+++ b/tests/test_a.py
@@ -5 +5 @@
diff --git a/new.py b/new.py
--- /dev/null
+++ b/new.py
@@ -0,0 +1,3 @@
"""


def test_gold_from_diff_uses_preimage_lines_and_skips_tests_and_new_files():
    gold, touched = gold_from_diff(DIFF)
    assert gold == {"pkg/a.py": [(10, 11), (30, 30)]}
    assert touched == 3


def test_message_strips_trailers():
    raw = "Fix parser on empty input\n\nDetails here.\n\nSigned-off-by: A <a@b.c>\n"
    assert message(raw) == "Fix parser on empty input\n\nDetails here."


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def test_mine_tasks(tmp_path):
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "t@example.com")
    git(tmp_path, "config", "user.name", "t")
    src = tmp_path / "calc.py"
    src.write_text("def add(a, b):\n    return a - b\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "Initial import of the calculator module")
    src.write_text("def add(a, b):\n    return a + b\n")
    git(tmp_path, "commit", "-qam", "Fix add returning the difference instead of the sum")
    src.write_text("def add(a, b):\n    return a + b  # ok\n")
    git(tmp_path, "commit", "-qam", "Bump version to 1.2.3 and refresh the changelog")
    tasks = mine_tasks(tmp_path, n=5)
    assert len(tasks) == 1
    t = tasks[0]
    assert t.problem_statement.startswith("Fix add returning")
    assert t.gold_lines == {"calc.py": [(2, 2)]}
    assert t.repo_url == str(tmp_path.resolve())
