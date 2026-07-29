from local_llm.repo_context import build_repo_context, collect_repo_files, format_repo_context


def test_collect_repo_files_excludes_git_and_reads_text(tmp_path) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("secret", encoding="utf-8")
    (tmp_path / "main.py").write_text("print('hi')", encoding="utf-8")

    files = collect_repo_files(tmp_path)

    assert [file.path.as_posix() for file in files] == ["main.py"]
    assert "print('hi')" in format_repo_context(files)


def test_build_repo_context_ranks_task_matches(tmp_path) -> None:
    (tmp_path / "alpha.py").write_text("def train_model(): pass", encoding="utf-8")
    (tmp_path / "zeta.py").write_text("def unrelated(): pass", encoding="utf-8")

    context = build_repo_context(tmp_path, task="train model", max_files=1)

    assert context.files[0].path.as_posix() == "alpha.py"
    assert "alpha.py" in context.tree
