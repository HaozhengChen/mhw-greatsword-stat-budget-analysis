"""Rebuild the analysis from the committed CSV snapshot without web access."""

import argparse
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parent
DATA_STEPS = (
    "mhw_greatsword_add_classification_fields.py",
    "mhw_greatsword_add_efr.py",
    "mhw_greatsword_exclude_siege_weapons.py",
)
REPORT_STEPS = (
    "mhw_greatsword_visualize_efr.py",
    "mhw_greatsword_weapon_value_regression.py",
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-only", action="store_true",
        help="Rebuild CSV tables only; skip charts and regression reports.",
    )
    args = parser.parse_args()
    steps = DATA_STEPS if args.data_only else DATA_STEPS + REPORT_STEPS
    for step in steps:
        print(f"\nRunning {step}", flush=True)
        subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / step)], check=True,
        )
    print("\nOffline pipeline completed.")


if __name__ == "__main__":
    main()
