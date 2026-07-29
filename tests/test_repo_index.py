from local_llm.repo_index import build_repo_index, extract_python_symbols


def test_extract_python_symbols(tmp_path) -> None:
    path = tmp_path / "sample.py"
    path.write_text(
        "import os\nfrom pathlib import Path\n\nclass App:\n    pass\n\ndef run():\n    pass\n",
        encoding="utf-8",
    )

    symbols, imports = extract_python_symbols(path)

    assert [symbol.name for symbol in symbols] == ["App", "run"]
    assert "os" in imports
    assert "pathlib" in imports


def test_build_repo_index_includes_git_status(tmp_path) -> None:
    (tmp_path / "sample.py").write_text("def run(): pass", encoding="utf-8")

    index = build_repo_index(tmp_path)

    assert index.files[0].path.as_posix() == "sample.py"
    assert "Git command failed" in index.git_status or index.git_status
