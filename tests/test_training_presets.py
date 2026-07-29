from local_llm.training_presets import TRAINING_PRESETS, ascii_loss_chart, preset_args


def test_training_preset_args() -> None:
    args = preset_args(TRAINING_PRESETS["Tiny CPU"])

    assert "--max-steps" in args
    assert "250" in args
    assert "--stage" in args
    assert "pretrain" in args
    assert "--log-interval" in args


def test_sft_training_preset_args() -> None:
    args = preset_args(TRAINING_PRESETS["Ares SFT CPU Demo"])

    assert "--stage" in args
    assert "sft" in args
    assert "--block-size" in args


def test_ascii_loss_chart() -> None:
    chart = ascii_loss_chart(
        {
            "metrics": [
                {"step": 0, "train": 3.0, "val": 3.2},
                {"step": 50, "train": 2.4, "val": 2.7},
            ]
        }
    )

    assert "train=3.000" in chart
    assert "val=2.700" in chart
    assert "tok/s=" in chart


def test_ascii_loss_chart_reads_llmc_style_metrics() -> None:
    chart = ascii_loss_chart(
        {
            "metrics": [
                {"step": 0, "train_loss": 3.0, "val_loss": 3.2, "tokens_per_sec": 1200},
                {"step": 50, "train_loss": 2.4, "val_loss": 2.7, "tokens_per_sec": 1400},
            ]
        }
    )

    assert "val=2.700" in chart
    assert "tok/s=   1400" in chart
