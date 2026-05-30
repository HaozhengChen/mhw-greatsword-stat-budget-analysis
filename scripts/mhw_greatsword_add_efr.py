import pandas as pd
from pathlib import Path

INPUT_CSV = "mhw_greatsword_classified.csv"
OUTPUT_CSV = "mhw_greatsword_efr.csv"


def safe_number(value, default=0.0):
    if pd.isna(value):
        return default
    return float(value)


def affinity_multiplier(affinity_percent, crit_bonus=0.25):
    """
    affinity_percent:
        25  -> 25% 会心
        -30 -> -30% 会心

    crit_bonus:
        0.25 = 无超会心，普通暴击 +25% raw
        0.40 = 超会心 3，正会心暴击 +40% raw

    注意：
    负会心惩罚固定按 -25% 处理，不受超会心影响。
    """
    affinity = safe_number(affinity_percent, 0.0) / 100.0

    if affinity >= 0:
        return 1.0 + affinity * crit_bonus
    else:
        return 1.0 + affinity * 0.25


def calculate_efr(row: pd.Series) -> pd.Series:
    true_raw = safe_number(row.get("true_raw"), 0.0)
    affinity = safe_number(row.get("affinity"), 0.0)

    base_sharpness = safe_number(row.get("base_raw_sharpness_multiplier"), 0.0)
    handicraft5_sharpness = safe_number(row.get("handicraft5_raw_sharpness_multiplier"), 0.0)

    aff_no_cb = affinity_multiplier(affinity, crit_bonus=0.25)
    aff_cb3 = affinity_multiplier(affinity, crit_bonus=0.40)

    base_efr_no_cb = true_raw * base_sharpness * aff_no_cb
    base_efr_cb3 = true_raw * base_sharpness * aff_cb3

    handicraft5_efr_no_cb = true_raw * handicraft5_sharpness * aff_no_cb
    handicraft5_efr_cb3 = true_raw * handicraft5_sharpness * aff_cb3

    return pd.Series({
        "affinity_multiplier_no_critboost": aff_no_cb,
        "affinity_multiplier_critboost3": aff_cb3,

        "base_efr_no_critboost": base_efr_no_cb,
        "base_efr_critboost3": base_efr_cb3,

        "handicraft5_efr_no_critboost": handicraft5_efr_no_cb,
        "handicraft5_efr_critboost3": handicraft5_efr_cb3,

        "efr_gain_from_handicraft_no_critboost": handicraft5_efr_no_cb - base_efr_no_cb,
        "efr_gain_from_handicraft_critboost3": handicraft5_efr_cb3 - base_efr_cb3,

        "efr_gain_from_handicraft_percent_no_critboost": (
            handicraft5_efr_no_cb / base_efr_no_cb - 1.0
            if base_efr_no_cb > 0 else None
        ),
        "efr_gain_from_handicraft_percent_critboost3": (
            handicraft5_efr_cb3 / base_efr_cb3 - 1.0
            if base_efr_cb3 > 0 else None
        ),
    })


def classify_outlier(residual_percent):
    """
    根据相对同稀有度训练集 median 的偏离程度进行标签化。

    residual_percent:
        0.10 = 高于同稀有度训练集基准 10%
        -0.08 = 低于同稀有度训练集基准 8%
    """
    if pd.isna(residual_percent):
        return "no_baseline"

    if residual_percent < -0.10:
        return "far_below_curve"
    elif residual_percent < -0.05:
        return "below_curve"
    elif residual_percent <= 0.05:
        return "on_curve"
    elif residual_percent <= 0.10:
        return "above_curve"
    elif residual_percent <= 0.20:
        return "possible_overtuned"
    else:
        return "far_above_curve"


def add_rarity_baselines(df: pd.DataFrame) -> pd.DataFrame:
    """
    用 include_in_efr_train = True 的武器作为训练集，
    按 rarity 计算 EFR 中位数基准线。
    """
    train = df[df["include_in_efr_train"] == True].copy()

    base_baseline = (
        train
        .groupby("rarity")["base_efr_critboost3"]
        .median()
        .rename("rarity_median_base_efr_critboost3")
    )

    handicraft_baseline = (
        train
        .groupby("rarity")["handicraft5_efr_critboost3"]
        .median()
        .rename("rarity_median_handicraft5_efr_critboost3")
    )

    df = df.merge(base_baseline, on="rarity", how="left")
    df = df.merge(handicraft_baseline, on="rarity", how="left")

    df["base_efr_residual_percent"] = (
        df["base_efr_critboost3"] / df["rarity_median_base_efr_critboost3"] - 1.0
    )

    df["handicraft5_efr_residual_percent"] = (
        df["handicraft5_efr_critboost3"] / df["rarity_median_handicraft5_efr_critboost3"] - 1.0
    )

    df["base_efr_outlier_label"] = df["base_efr_residual_percent"].apply(classify_outlier)
    df["handicraft5_efr_outlier_label"] = df["handicraft5_efr_residual_percent"].apply(classify_outlier)

    return df


def print_summary(df: pd.DataFrame):
    print("\n=== Dataset summary ===")
    print(f"Total rows: {len(df)}")

    if "model_role" in df.columns:
        print("\nmodel_role counts:")
        print(df["model_role"].value_counts(dropna=False))

    if "source_category_detailed" in df.columns:
        print("\nsource_category_detailed counts:")
        print(df["source_category_detailed"].value_counts(dropna=False))

    print("\n=== Top 20 by base_efr_critboost3 ===")
    cols = [
        "weapon_name",
        "model_role",
        "source_category_detailed",
        "rarity",
        "true_raw",
        "affinity",
        "base_max_sharpness",
        "base_efr_critboost3",
        "base_efr_residual_percent",
        "base_efr_outlier_label",
    ]
    cols = [c for c in cols if c in df.columns]
    print(df.sort_values("base_efr_critboost3", ascending=False)[cols].head(20).to_string(index=False))

    print("\n=== Top 20 by handicraft5_efr_critboost3 ===")
    cols = [
        "weapon_name",
        "model_role",
        "source_category_detailed",
        "rarity",
        "true_raw",
        "affinity",
        "handicraft5_max_sharpness",
        "handicraft5_efr_critboost3",
        "handicraft5_efr_residual_percent",
        "handicraft5_efr_outlier_label",
    ]
    cols = [c for c in cols if c in df.columns]
    print(df.sort_values("handicraft5_efr_critboost3", ascending=False)[cols].head(20).to_string(index=False))

    print("\n=== Validation outliers by base EFR residual ===")
    if "include_in_validation" in df.columns:
        validation = df[df["include_in_validation"] == True].copy()
        cols = [
            "weapon_name",
            "source_category_detailed",
            "rarity",
            "base_efr_critboost3",
            "rarity_median_base_efr_critboost3",
            "base_efr_residual_percent",
            "base_efr_outlier_label",
        ]
        cols = [c for c in cols if c in validation.columns]
        print(validation.sort_values("base_efr_residual_percent", ascending=False)[cols].head(30).to_string(index=False))


def main():
    input_path = Path(INPUT_CSV)

    if not input_path.exists():
        raise FileNotFoundError(f"找不到输入文件：{INPUT_CSV}")

    df = pd.read_csv(input_path)

    efr_columns = df.apply(calculate_efr, axis=1)
    df_out = pd.concat([df, efr_columns], axis=1)

    df_out = add_rarity_baselines(df_out)

    df_out.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    print(f"Input:  {INPUT_CSV}")
    print(f"Output: {OUTPUT_CSV}")

    print_summary(df_out)


if __name__ == "__main__":
    main()