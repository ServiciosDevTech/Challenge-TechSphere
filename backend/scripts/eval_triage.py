"""Eval harness placeholder — extend with dataset_final.xlsx cases."""

from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline triage eval harness")
    parser.add_argument(
        "--dataset",
        default="../data/dataset/dataset_final.xlsx",
        help="Path to dataset_final.xlsx",
    )
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    print(
        "Usa pytest tests/test_golden_triage.py para el subset golden.\n"
        f"Dataset configurado: {args.dataset} (limit={args.limit}).\n"
        "Extiende este harness para batch eval contra label_ground_truth."
    )


if __name__ == "__main__":
    main()
