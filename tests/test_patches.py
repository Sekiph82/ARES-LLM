from local_llm.patches import extract_unified_diffs


def test_extract_unified_diff_from_fenced_block() -> None:
    text = """Use this:

```diff
diff --git a/a.txt b/a.txt
--- a/a.txt
+++ b/a.txt
@@ -1 +1 @@
-old
+new
```
"""

    bundle = extract_unified_diffs(text)

    assert bundle.has_patches
    assert "diff --git" in bundle.patches[0]
