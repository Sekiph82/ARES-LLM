from local_llm.ollama_manager import format_model_status, installed_models, model_matches, model_status


class FakeClient:
    def list_models(self) -> list[str]:
        return ["zeta:1b", "ares-coder"]


def test_installed_models_are_sorted() -> None:
    assert installed_models(FakeClient()) == ["ares-coder", "zeta:1b"]  # type: ignore[arg-type]


def test_model_status_formats_installed_model() -> None:
    status = model_status("ares-coder", FakeClient())  # type: ignore[arg-type]

    assert status.installed
    assert "ares-coder is installed" in format_model_status(status)


def test_model_matches_latest_alias() -> None:
    assert model_matches("ares-coder", "ares-coder:latest")
    assert not model_matches("ares-coder:3b", "ares-coder:latest")
