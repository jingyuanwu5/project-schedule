import sys
from pathlib import Path

_src = Path(__file__).parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from schedule_app.ui_tk.app import main

if __name__ == "__main__":
    main()