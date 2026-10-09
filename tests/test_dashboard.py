"""Dashboard smoke test: the app runs top to bottom without raising an exception."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "dashboard" / "app.py"


def test_dashboard_runs_without_errors():
    at = AppTest.from_file(str(APP), default_timeout=120).run()
    assert not at.exception
