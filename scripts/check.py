"""Run the same checks as CI, locally.

Usage:
    python scripts/check.py
"""

from __future__ import annotations

import subprocess
import sys

COMMANDS = [
    [sys.executable, "-m", "ruff", "check", "."],
    [sys.executable, "-m", "ruff", "format", "--check", "."],
    [sys.executable, "-m", "mypy", "src/options_pricer", "scripts"],
    [sys.executable, "-m", "pytest"],
]


def main() -> int:
    for command in COMMANDS:
        print("$", " ".join(command))
        result = subprocess.run(command, check=False)
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
