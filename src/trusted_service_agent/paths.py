"""Repo-relative paths for config, data and runtime output."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config"
DATA = ROOT / "data"
RUNS = ROOT / "runs"
