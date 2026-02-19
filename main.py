"""
main.py — GUI entry point for development use.

For production / packaging, prefer:
    python -m schedule_app.ui_tk.app
or install with `pip install -e .` and run:
    schedule-gui

sys.path manipulation here is a fallback so that double-clicking this
file or running `python main.py` works without a prior editable install.
"""
import sys
from pathlib import Path

_src = Path(__file__).parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from schedule_app.ui_tk.app import main  # noqa: E402

if __name__ == "__main__":
    main()
