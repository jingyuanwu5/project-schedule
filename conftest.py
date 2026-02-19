"""
conftest.py — placed at the project root so pytest finds it automatically.

Inserts src/ into sys.path before any test is collected, which means
  from schedule_app.xxx import yyy
works in tests even without running `pip install -e .` first.

Reference: pytest docs, "conftest.py: local per-directory plugins"
https://docs.pytest.org/en/stable/reference/fixtures.html
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
