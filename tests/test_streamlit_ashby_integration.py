from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_app_renders_ashby_screening_controls_without_errors() -> None:
    app_path = Path(__file__).resolve().parent.parent / "app.py"
    app = AppTest.from_file(str(app_path), default_timeout=10).run()

    assert not app.exception
    assert any(expander.label == "Ashby material screening" for expander in app.expander)
    selectbox_labels = {selectbox.label for selectbox in app.selectbox}
    assert "Horizontal-axis property" in selectbox_labels
    assert "Vertical-axis property" in selectbox_labels
    assert "Review material record" in selectbox_labels
    assert app.get("image")
    assert any(
        "Screening aid only" in warning.value
        for warning in app.warning
    )
