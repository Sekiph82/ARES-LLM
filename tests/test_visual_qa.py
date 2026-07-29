from local_llm.visual_qa import VisualQAResult


def test_visual_qa_result_serializes() -> None:
    result = VisualQAResult(ok=True, skipped=True, screenshots=[], issues=["missing playwright"])

    assert result.to_dict()["skipped"] is True
    assert result.to_dict()["issues"] == ["missing playwright"]
