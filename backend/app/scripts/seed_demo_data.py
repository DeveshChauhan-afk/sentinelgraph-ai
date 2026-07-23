"""
Seeds SentinelGraph AI with demo incidents.

Usage:
    python scripts/seed_demo_data.py
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import requests

BASE_URL = "http://localhost:8000/api/v1/complaints/"

DATASET = Path(__file__).parent / "data" / "demo_dataset.json"


def main() -> None:

    if not DATASET.exists():
        raise FileNotFoundError(
            "demo_dataset.json not found.\n" "Run build_demo_dataset.py first."
        )

    with DATASET.open("r", encoding="utf-8") as f:
        incidents = json.load(f)

    total = len(incidents)

    print(f"\nSeeding {total} incidents...\n")

    success = 0

    for index, incident in enumerate(incidents, start=1):

        try:
            response = requests.post(
                BASE_URL,
                json=incident,
                timeout=120,
            )

            if response.status_code in (200, 201):
                success += 1
                print(f"✓ [{index:02}/{total}] {incident['title']}")
            else:
                print(
                    f"✗ [{index:02}/{total}] "
                    f"{incident['title']}\n"
                    f"    {response.status_code} : {response.text}"
                )

        except Exception as exc:
            print(f"✗ [{index:02}/{total}] " f"{incident['title']}\n" f"    {exc}")

        time.sleep(50)

    print("\n==============================")
    print(f"Successful : {success}")
    print(f"Failed     : {total-success}")
    print("==============================")


if __name__ == "__main__":
    main()
