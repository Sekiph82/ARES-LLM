from local_llm.patch_ops import check_patch, is_safe_relative_path, patch_paths


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
