from local_llm.memory import append_memory, load_memory


def test_append_and_load_memory(tmp_path) -> None:
    append_memory(tmp_path, "Patch lesson", "Always run tests after applying patches.")

    text = load_memory(tmp_path)

    assert "Patch lesson" in text
    assert "Always run tests" in text
