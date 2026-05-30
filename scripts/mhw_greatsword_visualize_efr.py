import math
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager


INPUT_CSV = "mhw_greatsword_efr.csv"
OUTPUT_DIR = Path("mhw_greatsword_visuals")
CHART_DIR = OUTPUT_DIR / "charts"
TABLE_DIR = OUTPUT_DIR / "summary_tables"
REPORT_PATH = OUTPUT_DIR / "mhw_greatsword_visual_report.md"


# -----------------------------
# Display / formatting helpers
# -----------------------------

def setup_chinese_font():
    """
    尝试设置中文字体，避免图表中文乱码。
    如果你的机器没有这些字体，图表仍会生成，只是中文可能显示为方块。
    """
    candidates = [
        "Microsoft YaHei",
        "SimHei",
        "PingFang SC",
        "Noto Sans CJK SC",
        "Arial Unicode MS",
    ]

    available_fonts = {f.name for f in font_manager.fontManager.ttflist}

    for font in candidates:
        if font in available_fonts:
            plt.rcParams["font.sans-serif"] = [font]
            plt.rcParams["axes.unicode_minus"] = False
            print(f"Using font: {font}")
            return

    plt.rcParams["axes.unicode_minus"] = False
    print("Warning: No preferred Chinese font found. Chinese labels may not render correctly.")


def ensure_dirs():
    OUTPUT_DIR.mkdir(exist_ok=True)
    CHART_DIR.mkdir(exist_ok=True)
    TABLE_DIR.mkdir(exist_ok=True)


def as_bool_series(series: pd.Series) -> pd.Series:
    """
    兼容 True/False、true/false、1/0、字符串等格式。
    """
    return series.astype(str).str.lower().isin(["true", "1", "yes", "y"])


def pct(x):
    if pd.isna(x):
        return ""
    return f"{x * 100:.1f}%"


def save_table(df: pd.DataFrame, filename: str):
    path = TABLE_DIR / filename
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"Saved table: {path}")


def save_chart(filename: str):
    path = CHART_DIR / filename
    plt.tight_layout()
    plt.savefig(path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"Saved chart: {path}")


def top_n_by_group(df, group_col, sort_col, n=10, ascending=False):
    return (
        df.sort_values([group_col, sort_col], ascending=[True, ascending])
        .groupby(group_col)
        .head(n)
        .reset_index(drop=True)
    )


# -----------------------------
# Load / clean data
# -----------------------------

def load_data() -> pd.DataFrame:
    df = pd.read_csv(INPUT_CSV)

    # Boolean normalization
    for col in ["include_in_efr_train", "include_in_validation", "efr_train_inclusion", "validation_inclusion"]:
        if col in df.columns:
            df[col] = as_bool_series(df[col])

    # Numeric normalization
    numeric_cols = [
        "rarity",
        "true_raw",
        "affinity",
        "base_efr_critboost3",
        "handicraft5_efr_critboost3",
        "efr_gain_from_handicraft_percent_critboost3",
        "base_efr_residual_percent",
        "handicraft5_efr_residual_percent",
        "rarity_median_base_efr_critboost3",
        "rarity_median_handicraft5_efr_critboost3",
        "base_white_units",
        "base_purple_units",
        "handicraft5_white_units",
        "handicraft5_purple_units",
        "slot_1",
        "slot_2",
        "slot_3",
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Helpful derived display fields
    df["weapon_label"] = df["weapon_name"].fillna("(unknown)") + " R" + df["rarity"].astype("Int64").astype(str)

    return df


# -----------------------------
# Summary tables
# -----------------------------

def make_summary_tables(df: pd.DataFrame):
    train = df[df["include_in_efr_train"] == True].copy()
    validation = df[df["include_in_validation"] == True].copy()

    # 1) Dataset counts
    model_role_counts = (
        df["model_role"]
        .value_counts(dropna=False)
        .rename_axis("model_role")
        .reset_index(name="count")
    )
    save_table(model_role_counts, "summary_model_role_counts.csv")

    source_counts = (
        df["source_category_detailed"]
        .value_counts(dropna=False)
        .rename_axis("source_category_detailed")
        .reset_index(name="count")
    )
    save_table(source_counts, "summary_source_category_counts.csv")

    # 2) Rarity baseline
    rarity_baseline = (
        train
        .groupby("rarity")
        .agg(
            train_count=("weapon_name", "count"),
            median_base_efr=("base_efr_critboost3", "median"),
            median_handicraft5_efr=("handicraft5_efr_critboost3", "median"),
            mean_base_efr=("base_efr_critboost3", "mean"),
            mean_handicraft5_efr=("handicraft5_efr_critboost3", "mean"),
        )
        .reset_index()
        .sort_values("rarity")
    )
    save_table(rarity_baseline, "summary_rarity_baseline.csv")

    # 3) Top train by rarity
    keep_cols = [
        "weapon_name",
        "rarity",
        "source_category_detailed",
        "true_raw",
        "affinity",
        "base_max_sharpness",
        "handicraft5_max_sharpness",
        "base_efr_critboost3",
        "handicraft5_efr_critboost3",
        "efr_gain_from_handicraft_percent_critboost3",
        "base_efr_residual_percent",
        "handicraft5_efr_residual_percent",
        "base_efr_outlier_label",
        "handicraft5_efr_outlier_label",
    ]

    top_base_by_rarity = top_n_by_group(train, "rarity", "base_efr_critboost3", n=10, ascending=False)[keep_cols]
    save_table(top_base_by_rarity, "top_train_base_efr_by_rarity.csv")

    top_hand_by_rarity = top_n_by_group(train, "rarity", "handicraft5_efr_critboost3", n=10, ascending=False)[keep_cols]
    save_table(top_hand_by_rarity, "top_train_handicraft5_efr_by_rarity.csv")

    # 4) Handicraft gains
    hand_gain = (
        df
        .sort_values("efr_gain_from_handicraft_percent_critboost3", ascending=False)
        [keep_cols + ["model_role"]]
        .head(30)
    )
    save_table(hand_gain, "top_handicraft_efr_gain.csv")

    # 5) Validation outliers
    validation_cols = [
        "weapon_name",
        "rarity",
        "source_category_detailed",
        "model_role",
        "true_raw",
        "affinity",
        "base_max_sharpness",
        "handicraft5_max_sharpness",
        "base_efr_critboost3",
        "handicraft5_efr_critboost3",
        "base_efr_residual_percent",
        "handicraft5_efr_residual_percent",
        "base_efr_outlier_label",
        "handicraft5_efr_outlier_label",
    ]

    validation_outliers = (
        validation
        .sort_values("handicraft5_efr_residual_percent", ascending=False)
        [validation_cols]
    )
    save_table(validation_outliers, "validation_outliers_by_handicraft5_residual.csv")

    return {
        "train": train,
        "validation": validation,
        "model_role_counts": model_role_counts,
        "source_counts": source_counts,
        "rarity_baseline": rarity_baseline,
        "top_base_by_rarity": top_base_by_rarity,
        "top_hand_by_rarity": top_hand_by_rarity,
        "hand_gain": hand_gain,
        "validation_outliers": validation_outliers,
    }


# -----------------------------
# Charts
# -----------------------------

def chart_rarity_baseline(rarity_baseline: pd.DataFrame):
    plt.figure(figsize=(8, 5))
    x = np.arange(len(rarity_baseline))
    width = 0.35

    plt.bar(
        x - width / 2,
        rarity_baseline["median_base_efr"],
        width,
        label="Base EFR",
    )
    plt.bar(
        x + width / 2,
        rarity_baseline["median_handicraft5_efr"],
        width,
        label="Handicraft 5 EFR",
    )

    plt.xticks(x, rarity_baseline["rarity"].astype(int))
    plt.xlabel("Rarity")
    plt.ylabel("Median EFR")
    plt.title("Train Core: Median EFR by Rarity")
    plt.legend()
    save_chart("01_rarity_baseline_efr.png")


def chart_top_train_r12(train: pd.DataFrame, mode: str):
    if mode == "base":
        sort_col = "base_efr_critboost3"
        title = "Train Core R12: Top Base EFR"
        filename = "02_train_core_r12_top_base_efr.png"
    else:
        sort_col = "handicraft5_efr_critboost3"
        title = "Train Core R12: Top Handicraft 5 EFR"
        filename = "03_train_core_r12_top_handicraft5_efr.png"

    r12 = train[train["rarity"] == 12].copy()
    top = r12.sort_values(sort_col, ascending=True).tail(15)

    plt.figure(figsize=(10, 7))
    plt.barh(top["weapon_name"], top[sort_col])
    plt.xlabel("EFR")
    plt.title(title)
    save_chart(filename)


def chart_handicraft_gain(df: pd.DataFrame):
    top = (
        df
        .dropna(subset=["efr_gain_from_handicraft_percent_critboost3"])
        .sort_values("efr_gain_from_handicraft_percent_critboost3", ascending=True)
        .tail(20)
    )

    plt.figure(figsize=(10, 8))
    plt.barh(top["weapon_name"], top["efr_gain_from_handicraft_percent_critboost3"] * 100)
    plt.xlabel("EFR Gain from Handicraft 5 (%)")
    plt.title("Top EFR Gain from Handicraft 5")
    save_chart("04_top_handicraft_efr_gain_percent.png")


def chart_validation_residuals(validation: pd.DataFrame):
    if validation.empty:
        return

    plot_df = (
        validation
        .dropna(subset=["handicraft5_efr_residual_percent"])
        .sort_values("handicraft5_efr_residual_percent", ascending=True)
    )

    # 过多时只显示最高 / 最低各 20 个，避免图太长
    if len(plot_df) > 40:
        plot_df = pd.concat([plot_df.head(20), plot_df.tail(20)]).drop_duplicates()

    colors = []
    for val in plot_df["handicraft5_efr_residual_percent"]:
        if val >= 0.10:
            colors.append("#d62728")  # red
        elif val >= 0.05:
            colors.append("#ff7f0e")  # orange
        elif val <= -0.10:
            colors.append("#1f77b4")  # blue
        elif val <= -0.05:
            colors.append("#17becf")  # cyan
        else:
            colors.append("#7f7f7f")  # gray

    plt.figure(figsize=(11, 10))
    plt.barh(plot_df["weapon_name"], plot_df["handicraft5_efr_residual_percent"] * 100, color=colors)
    plt.axvline(0, color="black", linewidth=1)
    plt.axvline(5, color="gray", linewidth=0.8, linestyle="--")
    plt.axvline(10, color="gray", linewidth=0.8, linestyle="--")
    plt.axvline(-5, color="gray", linewidth=0.8, linestyle="--")
    plt.axvline(-10, color="gray", linewidth=0.8, linestyle="--")
    plt.xlabel("Handicraft 5 EFR Residual vs Same-Rarity Train Median (%)")
    plt.title("Validation Weapons: EFR Residuals")
    save_chart("05_validation_handicraft5_residuals.png")


def chart_base_vs_handicraft_scatter(df: pd.DataFrame):
    plt.figure(figsize=(8, 7))

    role_colors = {
        "train_core": "#2ca02c",
        "validation_marked": "#ff7f0e",
        "validation_special": "#d62728",
        "exclude_progression": "#9467bd",
    }

    for role, group in df.groupby("model_role"):
        plt.scatter(
            group["base_efr_critboost3"],
            group["handicraft5_efr_critboost3"],
            label=role,
            alpha=0.75,
            s=40,
            c=role_colors.get(role, "#7f7f7f"),
        )

    min_val = min(df["base_efr_critboost3"].min(), df["handicraft5_efr_critboost3"].min())
    max_val = max(df["base_efr_critboost3"].max(), df["handicraft5_efr_critboost3"].max())
    plt.plot([min_val, max_val], [min_val, max_val], color="black", linestyle="--", linewidth=1)

    plt.xlabel("Base EFR")
    plt.ylabel("Handicraft 5 EFR")
    plt.title("Base EFR vs Handicraft 5 EFR")
    plt.legend()
    save_chart("06_base_vs_handicraft5_efr_scatter.png")


def chart_outlier_counts(df: pd.DataFrame):
    labels_order = [
        "far_below_curve",
        "below_curve",
        "on_curve",
        "above_curve",
        "possible_overtuned",
        "far_above_curve",
        "no_baseline",
    ]

    counts = (
        df["handicraft5_efr_outlier_label"]
        .value_counts()
        .reindex(labels_order)
        .fillna(0)
    )

    plt.figure(figsize=(10, 5))
    plt.bar(counts.index, counts.values)
    plt.xticks(rotation=30, ha="right")
    plt.ylabel("Weapon Count")
    plt.title("Handicraft 5 EFR Outlier Label Counts")
    save_chart("07_handicraft5_outlier_label_counts.png")


def make_charts(df: pd.DataFrame, summaries: dict):
    chart_rarity_baseline(summaries["rarity_baseline"])
    chart_top_train_r12(summaries["train"], mode="base")
    chart_top_train_r12(summaries["train"], mode="handicraft5")
    chart_handicraft_gain(df)
    chart_validation_residuals(summaries["validation"])
    chart_base_vs_handicraft_scatter(df)
    chart_outlier_counts(df)


# -----------------------------
# Markdown report
# -----------------------------

def make_markdown_report(df: pd.DataFrame, summaries: dict):
    train = summaries["train"]
    validation = summaries["validation"]

    top_train_base = (
        train
        .sort_values("base_efr_critboost3", ascending=False)
        .head(10)
    )

    top_train_hand = (
        train
        .sort_values("handicraft5_efr_critboost3", ascending=False)
        .head(10)
    )

    top_validation = (
        validation
        .dropna(subset=["handicraft5_efr_residual_percent"])
        .sort_values("handicraft5_efr_residual_percent", ascending=False)
        .head(10)
    )

    lines = []
    lines.append("# MHW: Iceborne Great Sword Theoretical DPS Visualization Report")
    lines.append("")
    lines.append("## 1. Analysis scope")
    lines.append("")
    lines.append("This report uses `mhw_greatsword_efr.csv` as the input dataset.")
    lines.append("")
    lines.append("The current theoretical DPS metric is a raw-side EFR proxy:")
    lines.append("")
    lines.append("```text")
    lines.append("EFR = True Raw × Sharpness Raw Multiplier × Affinity Multiplier")
    lines.append("```")
    lines.append("")
    lines.append("The report compares two weapon states:")
    lines.append("")
    lines.append("- `base_efr_critboost3`: no Handicraft, assuming Critical Boost 3")
    lines.append("- `handicraft5_efr_critboost3`: Handicraft 5, assuming Critical Boost 3")
    lines.append("")
    lines.append("This is not a full in-game DPS simulation. It does not include elemental damage, status buildup, slot-to-skill conversion, sharpness uptime, animation timing, hitzone selection, or player execution.")
    lines.append("")
    lines.append("## 2. Dataset segmentation")
    lines.append("")
    lines.append("### model_role counts")
    lines.append("")
    lines.append(summaries["model_role_counts"].to_markdown(index=False))
    lines.append("")
    lines.append("### source_category_detailed counts")
    lines.append("")
    lines.append(summaries["source_counts"].to_markdown(index=False))
    lines.append("")
    lines.append("## 3. Same-rarity EFR baseline")
    lines.append("")
    lines.append("The baseline is calculated from weapons with `include_in_efr_train = True`. Median EFR by rarity is used as the reference curve for regular material-tree weapons.")
    lines.append("")
    lines.append(summaries["rarity_baseline"].to_markdown(index=False))
    lines.append("")
    lines.append("Related chart:")
    lines.append("")
    lines.append("```text")
    lines.append("charts/01_rarity_baseline_efr.png")
    lines.append("```")
    lines.append("")
    lines.append("## 4. Training set: top 10 base EFR")
    lines.append("")
    display_cols = [
        "weapon_name",
        "rarity",
        "source_category_detailed",
        "true_raw",
        "affinity",
        "base_max_sharpness",
        "base_efr_critboost3",
        "base_efr_residual_percent",
        "base_efr_outlier_label",
    ]
    lines.append(top_train_base[display_cols].to_markdown(index=False))
    lines.append("")
    lines.append("Related chart:")
    lines.append("")
    lines.append("```text")
    lines.append("charts/02_train_core_r12_top_base_efr.png")
    lines.append("```")
    lines.append("")
    lines.append("## 5. Training set: top 10 Handicraft 5 EFR")
    lines.append("")
    display_cols = [
        "weapon_name",
        "rarity",
        "source_category_detailed",
        "true_raw",
        "affinity",
        "handicraft5_max_sharpness",
        "handicraft5_efr_critboost3",
        "handicraft5_efr_residual_percent",
        "handicraft5_efr_outlier_label",
    ]
    lines.append(top_train_hand[display_cols].to_markdown(index=False))
    lines.append("")
    lines.append("Related charts:")
    lines.append("")
    lines.append("```text")
    lines.append("charts/03_train_core_r12_top_handicraft5_efr.png")
    lines.append("charts/04_top_handicraft_efr_gain_percent.png")
    lines.append("```")
    lines.append("")
    lines.append("## 6. Validation set: deviation from the regular weapon curve")
    lines.append("")
    lines.append("Validation weapons are not used to define the baseline. They are retained to check how special sources deviate from the regular material-tree curve.")
    lines.append("")
    display_cols = [
        "weapon_name",
        "rarity",
        "source_category_detailed",
        "handicraft5_efr_critboost3",
        "handicraft5_efr_residual_percent",
        "handicraft5_efr_outlier_label",
    ]
    if not top_validation.empty:
        lines.append(top_validation[display_cols].to_markdown(index=False))
    else:
        lines.append("No validation rows found.")
    lines.append("")
    lines.append("Related charts:")
    lines.append("")
    lines.append("```text")
    lines.append("charts/05_validation_handicraft5_residuals.png")
    lines.append("charts/06_base_vs_handicraft5_efr_scatter.png")
    lines.append("charts/07_handicraft5_outlier_label_counts.png")
    lines.append("```")
    lines.append("")
    lines.append("## 7. Interpretation guide")
    lines.append("")
    lines.append("- `on_curve`: the weapon is close to the same-rarity raw-side EFR baseline.")
    lines.append("- `above_curve`: the weapon is moderately above the baseline, usually due to favorable raw, affinity, or sharpness structure.")
    lines.append("- `possible_overtuned`: the weapon is substantially above the same-rarity baseline and should be reviewed as a potential high-budget or late-progression reward case.")
    lines.append("- `far_below_curve`: the weapon is significantly below the raw-side EFR baseline. Its budget may be allocated to element/status value, slots, utility, special acquisition systems, or historical version context.")
    lines.append("")
    lines.append("## 8. Next step: weapon value regression")
    lines.append("")
    lines.append("For the next modeling step, the recommended primary target is:")
    lines.append("")
    lines.append("```text")
    lines.append("handicraft5_efr_critboost3")
    lines.append("```")
    lines.append("")
    lines.append("A second analysis can use the same-rarity residual as the target:")
    lines.append("")
    lines.append("```text")
    lines.append("handicraft5_efr_residual_percent")
    lines.append("```")
    lines.append("")
    lines.append("Candidate features:")
    lines.append("")
    lines.append("- `true_raw`")
    lines.append("- `affinity`")
    lines.append("- `base_raw_sharpness_multiplier`")
    lines.append("- `handicraft5_raw_sharpness_multiplier`")
    lines.append("- `base_white_units`, `base_purple_units`")
    lines.append("- `handicraft5_white_units`, `handicraft5_purple_units`")
    lines.append("- `slot_1`, `slot_2`, `slot_3`")
    lines.append("- `element_value`")
    lines.append("- `is_hidden_element`")
    lines.append("- `source_category_detailed`")
    lines.append("")
    lines.append("Start with an interpretable linear model, then optionally compare it against nonlinear benchmarks such as Random Forest or gradient-boosted trees.")
    lines.append("")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Saved report: {REPORT_PATH}")


def main():
    ensure_dirs()
    setup_chinese_font()

    df = load_data()
    summaries = make_summary_tables(df)
    make_charts(df, summaries)
    make_markdown_report(df, summaries)

    print("")
    print("Done.")
    print(f"Output directory: {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()