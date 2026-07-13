from pathlib import Path
import subprocess
import sys


def _script_path() -> Path:
    return Path(__file__).resolve().parent.parent / "predict_fatigue.py"


def test_cli_help_renders_without_traceback() -> None:
    result = subprocess.run(
        [sys.executable, str(_script_path()), "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Traceback" not in result.stderr
    assert "Elongation at fracture (%)" in result.stdout


def test_cli_single_sample_runs_successfully() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(_script_path()),
            "--uts",
            "300",
            "--ys",
            "200",
            "--elongation",
            "5",
            "--stress-amplitude",
            "150",
            "--mean-stress",
            "50",
            "--correction",
            "walker",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Predicted Cycles" in result.stdout
    assert "Run summary: 1 sample(s), 1 succeeded, 0 failed" in result.stdout
    assert "Error in sample" not in result.stderr


def test_cli_requires_manual_tensile_args_without_csv() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(_script_path()),
            "--stress-amplitude",
            "150",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "Provide either --csv-file or --uts and --elongation" in result.stderr
