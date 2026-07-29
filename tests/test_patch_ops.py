from local_llm.patch_ops import assess_patch_safety, check_patch, is_safe_relative_path, patch_paths, summarize_patch


def test_patch_paths_extracts_git_diff_paths() -> None:
    patch = """diff --git a/src/app.py b/src/app.py
--- a/src/app.py
+++ b/src/app.py
@@ -1 +1 @@
-old
+new
"""

    assert [path.as_posix() for path in patch_paths(patch)] == ["src/app.py"]


def test_is_safe_relative_path_rejects_parent_paths() -> None:
    assert not is_safe_relative_path(__import__("pathlib").Path("../secret.txt"))


def test_check_patch_rejects_empty_patch(tmp_path) -> None:
    result = check_patch(tmp_path, "")

    assert not result.ok
    assert "No patch text" in result.message


def test_assess_patch_safety_rejects_generated_paths(tmp_path) -> None:
    patch = """diff --git a/runs/demo.txt b/runs/demo.txt
--- a/runs/demo.txt
+++ b/runs/demo.txt
@@ -1 +1 @@
-old
+new
"""

    result = assess_patch_safety(tmp_path, patch)

    assert not result.ok
    assert "generated or internal" in result.message


def test_assess_patch_safety_rejects_env_files(tmp_path) -> None:
    patch = """diff --git a/.env b/.env
--- a/.env
+++ b/.env
@@ -1 +1 @@
-A=1
+A=2
"""

    result = assess_patch_safety(tmp_path, patch)

    assert not result.ok
    assert "secret" in result.message


def test_summarize_patch_counts_additions_and_deletions(tmp_path) -> None:
    patch = """diff --git a/src/app.py b/src/app.py
--- a/src/app.py
+++ b/src/app.py
@@ -1,2 +1,3 @@
-old
+new
+extra
 keep
"""

    preview = summarize_patch(tmp_path, patch)

    assert preview.ok
    assert preview.total_additions == 2
    assert preview.total_deletions == 1
    assert preview.files[0].path.as_posix() == "src/app.py"
