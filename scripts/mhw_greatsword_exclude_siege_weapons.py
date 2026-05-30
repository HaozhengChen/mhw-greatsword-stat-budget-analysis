import pandas as pd
from pathlib import Path

INPUT_CSV = "mhw_greatsword_efr.csv"
OUTPUT_CSV = "mhw_greatsword_efr_no_siege.csv"

EXCLUDE_SOURCE_CATEGORIES = {
    "siege_kulve",
    "siege_safi",
}


def main():
    input_path = Path(INPUT_CSV)

    if not input_path.exists():
        raise FileNotFoundError(f"找不到输入文件：{INPUT_CSV}")

    df = pd.read_csv(input_path)

    if "source_category_detailed" not in df.columns:
        raise KeyError("缺少字段：source_category_detailed。请确认输入文件是 mhw_greatsword_efr.csv。")

    before_count = len(df)

    excluded = df[df["source_category_detailed"].isin(EXCLUDE_SOURCE_CATEGORIES)].copy()
    kept = df[~df["source_category_detailed"].isin(EXCLUDE_SOURCE_CATEGORIES)].copy()

    after_count = len(kept)

    kept.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    print(f"Input:  {INPUT_CSV}")
    print(f"Output: {OUTPUT_CSV}")
    print("")
    print(f"Rows before: {before_count}")
    print(f"Rows after:  {after_count}")
    print(f"Rows removed: {before_count - after_count}")
    print("")

    print("Removed source_category_detailed counts:")
    print(excluded["source_category_detailed"].value_counts(dropna=False))
    print("")

    print("Remaining model_role counts:")
    print(kept["model_role"].value_counts(dropna=False))
    print("")

    print("Remaining source_category_detailed counts:")
    print(kept["source_category_detailed"].value_counts(dropna=False))


if __name__ == "__main__":
    main()