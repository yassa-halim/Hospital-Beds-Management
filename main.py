"""
main.py
=======
Entry point for the Hospital Knowledge Management System.

Usage:
    python main.py
    python main.py --data-dir "path/to/csv/folder"
"""

import sys
import os
from pathlib import Path


def main():
    # Parse optional --data-dir argument
    data_dir: str | None = None
    args = sys.argv[1:]
    if "--data-dir" in args:
        idx = args.index("--data-dir")
        if idx + 1 < len(args):
            data_dir = args[idx + 1]

    # Ensure working directory is the script's directory so CSV files can
    # be found by default.
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    try:
        from gui_app import HospitalKMSApp
    except ImportError as e:
        print(f"[Error] Could not import gui_app: {e}")
        print("Make sure all required packages are installed:")
        print("  pip install pandas networkx matplotlib")
        sys.exit(1)

    app = HospitalKMSApp()

    # If a data directory was provided via CLI, set it before showing the window
    if data_dir:
        app._data_dir = data_dir

    app.run()


if __name__ == "__main__":
    main()
