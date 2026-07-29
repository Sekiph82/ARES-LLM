from local_llm.web_artifact import ArtifactFile, has_required_files, parse_artifact_files, quality_issues, slugify


def test_parse_artifact_files() -> None:
    response = """--- FILE: index.html ---
<html></html>
--- END FILE ---
--- FILE: styles.css ---
body {}
--- END FILE ---
--- FILE: app.js ---
console.log("ok");
--- END FILE ---
--- FILE: README.md ---
# Demo
--- END FILE ---
"""

    files = parse_artifact_files(response)

    assert has_required_files(files)
    assert files[0].path == "index.html"
    assert files[2].content.startswith("console.log")


def test_parse_artifact_files_rejects_unsafe_paths() -> None:
    response = """--- FILE: ../bad.py ---
print("bad")
--- END FILE ---
--- FILE: index.html ---
<html></html>
--- END FILE ---
"""

    files = parse_artifact_files(response)

    assert [file.path for file in files] == ["index.html"]


def test_parse_artifact_files_from_markdown_fences() -> None:
    response = """### index.html
```html
<html></html>
```

styles.css
```css
body {}
```

app.js
```js
console.log("ok");
```

README.md
```md
# Demo
```
"""

    files = parse_artifact_files(response)

    assert has_required_files(files)


def test_slugify() -> None:
    assert slugify("Build me an Ares dashboard!") == "build-me-an-ares-dashboard"


def test_quality_issues_rejects_thin_ui() -> None:
    files = [
        ArtifactFile("index.html", '<link rel="stylesheet" href="styles.css"><script src="app.js"></script>'),
        ArtifactFile("styles.css", "body { color: #111; }"),
        ArtifactFile("app.js", "console.log('thin');"),
        ArtifactFile("README.md", "# Demo"),
    ]

    issues = quality_issues(files)

    assert "css is too thin for a polished responsive UI" in issues
