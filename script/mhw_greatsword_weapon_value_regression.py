import math
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import RidgeCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

INPUT_CSV = "mhw_greatsword_efr_no_siege.csv"
OUTPUT_DIR = Path("mhw_greatsword_regression_outputs")
CHART_DIR = OUTPUT_DIR / "charts"
REPORT_PATH = OUTPUT_DIR / "weapon_value_regression_report.md"

RANDOM_STATE = 42


# -----------------------------
# Setup helpers
# -----------------------------

def ensure_dirs():
    OUTPUT_DIR.mkdir(exist_ok=True)
    CHART_DIR.mkdir(exist_ok=True)


def setup_chinese_font():
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


def as_bool_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin(["true", "1", "yes", "y"])


def save_chart(filename: str):
    path = CHART_DIR / filename
    plt.tight_layout()
    plt.savefig(path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"Saved chart: {path}")


# -----------------------------
# Load / feature engineering
# -----------------------------

def load_data() -> pd.DataFrame:
    df = pd.read_csv(INPUT_CSV)

    for col in [
        "include_in_efr_train",
        "include_in_validation",
        "is_hidden_element",
        "can_extend_by_handicraft",
    ]:
        if col in df.columns:
            df[col] = as_bool_series(df[col])

    numeric_cols = [
        "rarity",
        "true_raw",
        "affinity",
        "element_value",
        "defense_bonus",
        "slot_1",
        "slot_2",
        "slot_3",
        "base_raw_sharpness_multiplier",
        "handicraft5_raw_sharpness_multiplier",
        "base_white_units",
        "base_purple_units",
        "handicraft5_white_units",
        "handicraft5_purple_units",
        "handicraft_gain_units",
        "base_efr_critboost3",
        "handicraft5_efr_critboost3",
        "efr_gain_from_handicraft_percent_critboost3",
        "base_efr_residual_percent",
        "handicraft5_efr_residual_percent",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Slot feature: 4级孔在 Iceborne 后期不是线性价值，这里给更高权重。
    slot_value_map = {
        1: 1.0,
        2: 2.5,
        3: 4.0,
        4: 6.0,
    }

    def slot_value(x):
        if pd.isna(x):
            return 0.0
        return slot_value_map.get(int(x), 0.0)

    df["slot_score"] = (
            df.get("slot_1", pd.Series(index=df.index, dtype=float)).apply(slot_value)
            + df.get("slot_2", pd.Series(index=df.index, dtype=float)).apply(slot_value)
            + df.get("slot_3", pd.Series(index=df.index, dtype=float)).apply(slot_value)
    )

    df["slot_count"] = df[[c for c in ["slot_1", "slot_2", "slot_3"] if c in df.columns]].notna().sum(axis=1)

    # Sharpness comfort: 不是瞬时 EFR，而是斩味续航 / 斩味压力的 proxy。
    df["base_high_sharpness_units"] = df.get("base_white_units", 0).fillna(0) + df.get("base_purple_units", 0).fillna(
        0) * 1.5
    df["handicraft5_high_sharpness_units"] = df.get("handicraft5_white_units", 0).fillna(0) + df.get(
        "handicraft5_purple_units", 0).fillna(0) * 1.5
    df["sharpness_comfort_gain"] = df["handicraft5_high_sharpness_units"] - df["base_high_sharpness_units"]

    # Element/status flags. 第一版不直接把属性等价为 DPS，只作为预算解释项。
    df["has_element_or_status"] = df["element_value"].fillna(0) > 0
    df["element_value_filled"] = df["element_value"].fillna(0)
    df["defense_bonus_filled"] = df["defense_bonus"].fillna(0)

    # Model role fallback
    if "model_role" not in df.columns:
        df["model_role"] = "unknown"
    if "source_category_detailed" not in df.columns:
        df["source_category_detailed"] = "unknown"

    return df


# -----------------------------
# Model builders
# -----------------------------

def get_feature_columns(df: pd.DataFrame):
    numeric_features = [
        "rarity",
        "true_raw",
        "affinity",
        "base_raw_sharpness_multiplier",
        "handicraft5_raw_sharpness_multiplier",
        "base_high_sharpness_units",
        "handicraft5_high_sharpness_units",
        "sharpness_comfort_gain",
        "handicraft_gain_units",
        "slot_score",
        "slot_count",
        "element_value_filled",
        "defense_bonus_filled",
    ]

    categorical_features = [
        "base_max_sharpness",
        "handicraft5_max_sharpness",
        "handicraft_value_type",
        "source_category_detailed",
        "model_role",
        "element_type",
        "elderseal",
        "is_hidden_element",
        "can_extend_by_handicraft",
    ]

    numeric_features = [c for c in numeric_features if c in df.columns]
    categorical_features = [c for c in categorical_features if c in df.columns]

    return numeric_features, categorical_features


def make_preprocessor(numeric_features, categorical_features):
    numeric_transformer = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])

    categorical_transformer = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore")),
    ])

    return ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numeric_features),
            ("cat", categorical_transformer, categorical_features),
        ]
    )


def build_ridge_model(numeric_features, categorical_features):
    preprocessor = make_preprocessor(numeric_features, categorical_features)
    alphas = np.logspace(-3, 3, 25)
    model = RidgeCV(alphas=alphas)

    return Pipeline(steps=[
        ("preprocess", preprocessor),
        ("model", model),
    ])


def build_random_forest_model(numeric_features, categorical_features):
    preprocessor = make_preprocessor(numeric_features, categorical_features)
    model = RandomForestRegressor(
        n_estimators=500,
        random_state=RANDOM_STATE,
        min_samples_leaf=2,
    )

    return Pipeline(steps=[
        ("preprocess", preprocessor),
        ("model", model),
    ])


def get_feature_names(pipeline: Pipeline, numeric_features, categorical_features):
    preprocessor = pipeline.named_steps["preprocess"]
    names = []

    names.extend(numeric_features)

    if categorical_features:
        cat_pipe = preprocessor.named_transformers_["cat"]
        onehot = cat_pipe.named_steps["onehot"]
        cat_names = onehot.get_feature_names_out(categorical_features).tolist()
        names.extend(cat_names)

    return names


# -----------------------------
# Evaluation / outputs
# -----------------------------

def evaluate_model(name: str, model: Pipeline, X: pd.DataFrame, y: pd.Series):
    y_pred = model.predict(X)

    metrics = {
        "model_name": name,
        "n_samples": len(y),
        "r2_in_sample": r2_score(y, y_pred) if len(y) >= 2 else np.nan,
        "mae_in_sample": mean_absolute_error(y, y_pred),
        "rmse_in_sample": math.sqrt(mean_squared_error(y, y_pred)),
    }

    # Small data: use KFold CV only if sample size allows.
    if len(y) >= 8:
        n_splits = min(5, len(y))
        cv = KFold(n_splits=n_splits, shuffle=True, random_state=RANDOM_STATE)
        try:
            cv_scores = cross_val_score(model, X, y, cv=cv, scoring="r2")
            metrics["r2_cv_mean"] = float(np.mean(cv_scores))
            metrics["r2_cv_std"] = float(np.std(cv_scores))
        except Exception as exc:
            print(f"CV failed for {name}: {exc}")
            metrics["r2_cv_mean"] = np.nan
            metrics["r2_cv_std"] = np.nan
    else:
        metrics["r2_cv_mean"] = np.nan
        metrics["r2_cv_std"] = np.nan

    return metrics, y_pred


def export_ridge_coefficients(model: Pipeline, numeric_features, categorical_features, filename: str):
    feature_names = get_feature_names(model, numeric_features, categorical_features)
    coefs = model.named_steps["model"].coef_

    coef_df = pd.DataFrame({
        "feature": feature_names,
        "coefficient": coefs,
        "abs_coefficient": np.abs(coefs),
    }).sort_values("abs_coefficient", ascending=False)

    path = OUTPUT_DIR / filename
    coef_df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"Saved coefficients: {path}")

    return coef_df


def chart_coefficients(coef_df: pd.DataFrame, filename: str, title: str, top_n=25):
    plot_df = coef_df.head(top_n).sort_values("coefficient", ascending=True)

    colors = ["#d62728" if x > 0 else "#1f77b4" for x in plot_df["coefficient"]]

    plt.figure(figsize=(11, 8))
    plt.barh(plot_df["feature"], plot_df["coefficient"], color=colors)
    plt.axvline(0, color="black", linewidth=1)
    plt.xlabel("Standardized Ridge Coefficient")
    plt.title(title)
    save_chart(filename)


def chart_predicted_vs_actual(df: pd.DataFrame, actual_col: str, pred_col: str, filename: str, title: str):
    plot_df = df.dropna(subset=[actual_col, pred_col]).copy()

    plt.figure(figsize=(7, 7))
    for role, group in plot_df.groupby("model_role"):
        plt.scatter(group[actual_col], group[pred_col], label=role, alpha=0.75, s=50)

    min_val = min(plot_df[actual_col].min(), plot_df[pred_col].min())
    max_val = max(plot_df[actual_col].max(), plot_df[pred_col].max())
    plt.plot([min_val, max_val], [min_val, max_val], color="black", linestyle="--", linewidth=1)

    plt.xlabel("Actual")
    plt.ylabel("Predicted")
    plt.title(title)
    plt.legend()
    save_chart(filename)


def chart_model_residuals(df: pd.DataFrame, actual_col: str, pred_col: str, filename: str, title: str, top_n=25):
    plot_df = df.dropna(subset=[actual_col, pred_col]).copy()
    plot_df["model_error"] = plot_df[actual_col] - plot_df[pred_col]

    # Show largest absolute errors.
    plot_df = plot_df.reindex(plot_df["model_error"].abs().sort_values(ascending=False).index).head(top_n)
    plot_df = plot_df.sort_values("model_error", ascending=True)

    colors = ["#d62728" if x > 0 else "#1f77b4" for x in plot_df["model_error"]]

    plt.figure(figsize=(11, 8))
    plt.barh(plot_df["weapon_name"], plot_df["model_error"], color=colors)
    plt.axvline(0, color="black", linewidth=1)
    plt.xlabel("Actual - Predicted")
    plt.title(title)
    save_chart(filename)


# -----------------------------
# Main modelling flow
# -----------------------------

def run_models(df: pd.DataFrame):
    metrics = []

    numeric_features, categorical_features = get_feature_columns(df)

    # Primary modelling dataset: exclude progression, use no-siege data.
    model_df = df[df["model_role"] != "exclude_progression"].copy()

    # Model A: explain theoretical raw DPS proxy.
    target_a = "handicraft5_efr_critboost3"
    data_a = model_df.dropna(subset=[target_a]).copy()
    X_a = data_a[numeric_features + categorical_features]
    y_a = data_a[target_a]

    ridge_a = build_ridge_model(numeric_features, categorical_features)
    ridge_a.fit(X_a, y_a)
    metric_a, pred_a = evaluate_model("ridge_stat_weight_handicraft5_efr", ridge_a, X_a, y_a)
    metrics.append(metric_a)
    data_a["pred_handicraft5_efr_ridge"] = pred_a
    data_a["ridge_efr_model_error"] = data_a[target_a] - data_a["pred_handicraft5_efr_ridge"]

    coef_a = export_ridge_coefficients(
        ridge_a,
        numeric_features,
        categorical_features,
        "ridge_stat_weight_coefficients.csv",
    )

    # Model B: explain residual / hidden budget deviation.
    target_b = "handicraft5_efr_residual_percent"
    data_b = model_df.dropna(subset=[target_b]).copy()
    X_b = data_b[numeric_features + categorical_features]
    y_b = data_b[target_b]

    ridge_b = build_ridge_model(numeric_features, categorical_features)
    ridge_b.fit(X_b, y_b)
    metric_b, pred_b = evaluate_model("ridge_residual_explanation", ridge_b, X_b, y_b)
    metrics.append(metric_b)
    data_b["pred_handicraft5_residual_ridge"] = pred_b
    data_b["ridge_residual_model_error"] = data_b[target_b] - data_b["pred_handicraft5_residual_ridge"]

    coef_b = export_ridge_coefficients(
        ridge_b,
        numeric_features,
        categorical_features,
        "ridge_residual_coefficients.csv",
    )

    # Optional nonlinear benchmark: Random Forest for residual explanation.
    # 用于检查是否存在明显非线性，但不作为主要解释模型。
    rf_b = build_random_forest_model(numeric_features, categorical_features)
    rf_b.fit(X_b, y_b)
    metric_rf_b, pred_rf_b = evaluate_model("random_forest_residual_benchmark", rf_b, X_b, y_b)
    metrics.append(metric_rf_b)
    data_b["pred_handicraft5_residual_rf"] = pred_rf_b

    # Merge predictions back to full df.
    out = df.copy()
    for col in ["pred_handicraft5_efr_ridge", "ridge_efr_model_error"]:
        out[col] = data_a[col]
    for col in ["pred_handicraft5_residual_ridge", "ridge_residual_model_error", "pred_handicraft5_residual_rf"]:
        out[col] = data_b[col]

    out_path = OUTPUT_DIR / "regression_dataset_with_predictions.csv"
    out.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"Saved dataset with predictions: {out_path}")

    metrics_df = pd.DataFrame(metrics)
    metrics_path = OUTPUT_DIR / "model_metrics.csv"
    metrics_df.to_csv(metrics_path, index=False, encoding="utf-8-sig")
    print(f"Saved metrics: {metrics_path}")

    # Charts
    chart_coefficients(
        coef_a,
        "01_ridge_stat_weight_coefficients.png",
        "Ridge Stat Weight Model: Top Coefficients",
    )
    chart_coefficients(
        coef_b,
        "02_ridge_residual_coefficients.png",
        "Ridge Residual Model: Top Coefficients",
    )
    chart_predicted_vs_actual(
        out,
        "handicraft5_efr_critboost3",
        "pred_handicraft5_efr_ridge",
        "03_predicted_vs_actual_efr.png",
        "Stat Weight Model: Predicted vs Actual Handicraft 5 EFR",
    )
    chart_predicted_vs_actual(
        out,
        "handicraft5_efr_residual_percent",
        "pred_handicraft5_residual_ridge",
        "04_predicted_vs_actual_residual.png",
        "Residual Model: Predicted vs Actual Residual",
    )
    chart_model_residuals(
        out,
        "handicraft5_efr_residual_percent",
        "pred_handicraft5_residual_ridge",
        "05_largest_residual_model_errors.png",
        "Residual Model: Largest Actual - Predicted Errors",
    )

    return {
        "out": out,
        "metrics": metrics_df,
        "coef_a": coef_a,
        "coef_b": coef_b,
        "numeric_features": numeric_features,
        "categorical_features": categorical_features,
    }


# -----------------------------
# Markdown report
# -----------------------------

def make_report(results: dict):
    out = results["out"]
    metrics = results["metrics"]
    coef_a = results["coef_a"].head(20)
    coef_b = results["coef_b"].head(20)

    top_positive_residual = (
        out.dropna(subset=["handicraft5_efr_residual_percent"])
        .sort_values("handicraft5_efr_residual_percent", ascending=False)
        .head(15)
    )
    top_negative_residual = (
        out.dropna(subset=["handicraft5_efr_residual_percent"])
        .sort_values("handicraft5_efr_residual_percent", ascending=True)
        .head(15)
    )

    lines = []
    lines.append("# Great Sword Weapon Value Regression Report")
    lines.append("")
    lines.append("## 1. Modeling scope")
    lines.append("")
    lines.append(
        "This model uses `mhw_greatsword_efr_no_siege.csv`, which excludes Kulve Taroth / Taroth / Kjarr weapons and Safi'jiiva awakened weapons.")
    lines.append("")
    lines.append(
        "These siege, appraisal, and awakening weapon systems are excluded because their reward structures and stat budgets are not directly comparable to regular material weapon trees.")
    lines.append("")
    lines.append("## 2. Model structure")
    lines.append("")
    lines.append("### Model A: Stat Weight Model")
    lines.append("")
    lines.append("Target variable:")
    lines.append("")
    lines.append("```text")
    lines.append("handicraft5_efr_critboost3")
    lines.append("```")
    lines.append("")
    lines.append(
        "This model estimates how weapon-side stats contribute to raw-side theoretical DPS under the Handicraft 5 + Critical Boost 3 assumption.")
    lines.append("")
    lines.append("### Model B: Residual Explanation Model")
    lines.append("")
    lines.append("Target variable:")
    lines.append("")
    lines.append("```text")
    lines.append("handicraft5_efr_residual_percent")
    lines.append("```")
    lines.append("")
    lines.append(
        "This model explains which weapon features are associated with being above or below the same-rarity baseline curve.")
    lines.append("")
    lines.append("## 3. Model metrics")
    lines.append("")
    lines.append(metrics.to_markdown(index=False))
    lines.append("")
    lines.append(
        "The dataset is intentionally compact because it focuses on final-upgrade Great Swords after removing siege-system weapons. Cross-validation results should therefore be read as directional evidence rather than as production-scale predictive performance.")
    lines.append("")
    lines.append("## 4. Stat Weight Model: top coefficients")
    lines.append("")
    lines.append(coef_a[["feature", "coefficient", "abs_coefficient"]].to_markdown(index=False))
    lines.append("")
    lines.append("Related charts:")
    lines.append("")
    lines.append("```text")
    lines.append("charts/01_ridge_stat_weight_coefficients.png")
    lines.append("charts/03_predicted_vs_actual_efr.png")
    lines.append("```")
    lines.append("")
    lines.append("## 5. Residual Explanation Model: top coefficients")
    lines.append("")
    lines.append(coef_b[["feature", "coefficient", "abs_coefficient"]].to_markdown(index=False))
    lines.append("")
    lines.append("Related charts:")
    lines.append("")
    lines.append("```text")
    lines.append("charts/02_ridge_residual_coefficients.png")
    lines.append("charts/04_predicted_vs_actual_residual.png")
    lines.append("charts/05_largest_residual_model_errors.png")
    lines.append("```")
    lines.append("")
    lines.append("## 6. Highest positive residual weapons")
    lines.append("")
    display_cols = [
        "weapon_name",
        "rarity",
        "source_category_detailed",
        "model_role",
        "handicraft5_efr_critboost3",
        "handicraft5_efr_residual_percent",
        "handicraft5_efr_outlier_label",
    ]
    lines.append(top_positive_residual[display_cols].to_markdown(index=False))
    lines.append("")
    lines.append("## 7. Highest negative residual weapons")
    lines.append("")
    lines.append(top_negative_residual[display_cols].to_markdown(index=False))
    lines.append("")
    lines.append("## 8. Design interpretation")
    lines.append("")
    lines.append("I treat each weapon as a stat-budget package composed of several interpretable components:")
    lines.append("")
    lines.append("```text")
    lines.append("Raw / Affinity / Sharpness / Slots / Element or Status / Utility")
    lines.append("```")
    lines.append("")
    lines.append(
        "The coefficient tables are used to examine which components explain raw-side theoretical DPS, while the residual model highlights which weapons sit above or below the same-rarity baseline after normalizing for progression tier.")
    lines.append("")
    lines.append(
        "In this project, the regression model is used as a balance-design lens rather than a black-box predictor. The goal is to identify stat trade-offs, isolate outlier weapons, and infer how hidden weapon budget may have been distributed across raw power, sharpness structure, slot value, elemental/status allocation, and source-specific reward tuning.")
    lines.append("")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Saved report: {REPORT_PATH}")


# -----------------------------
# Entrypoint
# -----------------------------

def main():
    ensure_dirs()
    setup_chinese_font()

    df = load_data()
    results = run_models(df)
    make_report(results)

    print("")
    print("Done.")
    print(f"Output directory: {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()