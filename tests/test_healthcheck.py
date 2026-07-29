from local_llm.healthcheck import HealthItem, HealthReport, format_health_report, run_healthcheck
from local_llm.video_encode import FFmpegStatus


class FakeClient:
    def __init__(self, models: list[str]) -> None:
        self.models = models

    def list_models(self) -> list[str]:
        return self.models


def test_format_health_report_marks_ready_for_warnings() -> None:
    text = format_health_report(
        HealthReport(ok=True, items=[HealthItem("FFmpeg", "warn", "Optional")])
    )

    assert "READY" in text
    assert "[WARN] FFmpeg" in text


def test_run_healthcheck_reports_missing_model_as_warning(monkeypatch, tmp_path) -> None:
    (tmp_path / ".git").mkdir()
    monkeypatch.setattr("local_llm.healthcheck.shutil.which", lambda name: name)
    monkeypatch.setattr("local_llm.healthcheck.resolve_ffmpeg", lambda: FFmpegStatus(True, tmp_path / "ffmpeg.exe", "ok"))
    monkeypatch.setattr("local_llm.healthcheck.check_imports", lambda: HealthItem("imports", "pass", "ok"))
    monkeypatch.setattr("local_llm.healthcheck.check_git", lambda repo: HealthItem("git", "pass", "ok"))
    monkeypatch.setattr("local_llm.healthcheck.check_playwright", lambda: HealthItem("playwright", "pass", "ok"))

    report = run_healthcheck(tmp_path, model="ares-coder", client=FakeClient(["qwen2.5-coder:3b"]))  # type: ignore[arg-type]

    assert report.ok
    assert any(item.name == "Ollama" and item.status == "warn" for item in report.items)
