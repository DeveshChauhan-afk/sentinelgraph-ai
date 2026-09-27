#!/usr/bin/env python3
"""
Root entrypoint wrapper for fast demo-data seeding.

Usage:
    python scripts/seed_extended_demo_data.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from dotenv import load_dotenv

# Add backend directory to sys.path and load environment variables
backend_dir = Path(__file__).resolve().parent.parent / "backend"
load_dotenv(backend_dir / ".env")
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.scripts.seed_extended_demo_data import main  # noqa: E402

if __name__ == "__main__":
    main()
