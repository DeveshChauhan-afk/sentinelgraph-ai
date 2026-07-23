"""
Builds a combined demo dataset from all fraud ring JSON files.

Usage:
    python scripts/build_demo_dataset.py
"""

from __future__ import annotations

import json
import random
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

INPUT_FILES = [
    "ring_alpha_kyc.json",
    "ring_beta_marketplace.json",
    "ring_gamma_courier.json",
    "ring_delta_investment.json",
    "independent_cases.json",
]

OUTPUT_FILE = DATA_DIR / "demo_dataset.json"


def load_json(path: Path) -> list[dict]:
    """Load a JSON file if it exists."""
    if not path.exists():
        print(f"[SKIP] {path.name} not found.")
        return []

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    dataset: list[dict] = []

    for filename in INPUT_FILES:
        complaints = load_json(DATA_DIR / filename)
        dataset.extend(complaints)
        print(f"Loaded {len(complaints):2} complaints from {filename}")

    random.shuffle(dataset)

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=4, ensure_ascii=False)

    print("\n--------------------------------")
    print(f"Total Complaints : {len(dataset)}")
    print(f"Output File      : {OUTPUT_FILE}")
    print("--------------------------------")


if __name__ == "__main__":
    main()
