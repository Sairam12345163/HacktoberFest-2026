#!/usr/bin/env python3
"""Thin wrapper so the skill works from a checkout without `pip install`."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from first_pr_pilot.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(["plan"] + sys.argv[1:]))
