# MHW Great Sword Stat Budget Analysis

A data-driven balance analysis project for **Monster Hunter: World / Iceborne Great Sword final-upgrade weapons**.

This project reverse-engineers weapon stat allocation by collecting weapon data, calculating Effective Raw (EFR), visualizing theoretical DPS patterns, and building interpretable regression models to study hidden stat-budget behavior.

## Project overview

This is not a player-facing build guide.

This project focuses on system design and game balance analysis:

- Reverse-engineering weapon stat allocation
- Estimating hidden stat-budget trade-offs
- Comparing same-rarity final-upgrade weapons
- Analyzing raw-side theoretical DPS through Effective Raw
- Identifying above-curve and below-curve weapons
- Exploring how weapon source categories affect balance curves
- Building interpretable regression models for stat-weight analysis

The current scope focuses on **Great Sword final-upgrade weapons**.

## Data source

Weapon data is collected from Kiranico:

```
https://mhworld.kiranico.com/zh/weapons
```

The dataset includes Great Sword final-upgrade weapons and parsed weapon attributes such as:

- Display attack
- True raw
- Affinity
- Element / status value
- Hidden element flag
- Sharpness values
- Handicraft 5 sharpness values
- Decoration slots
- Defense bonus
- Elderseal
- Rarity
- Weapon source category

Sharpness values are extracted from Kiranico's HTML sharpness bars.

The conversion used in this project is:

```
sharpness units = pixel width × 4
```

## Scope and filtering

The analysis separates weapons into modeling roles instead of simply deleting special cases.

| Role | Description |
| --- | --- |
| `train_core` | Regular material, elder dragon, and rare subspecies weapons used to build the baseline curve |
| `validation_marked` | Special but non-siege weapons retained for validation, such as Guild Palace or event weapons |
| `validation_special` | Late-progression or special-source weapons used for outlier validation |
| `exclude_progression` | Progression catch-up weapons, such as Defender weapons |

For the regression stage, siege-system weapons are excluded:

- Kulve Taroth
- Taroth
- Kjarr
- Gold appraisal weapons
- Safi'jiiva awakened weapons

These weapons are excluded because appraisal, siege, and awakening systems follow different reward and stat-budget rules from regular material weapon trees.

## Methodology

### 1. Effective Raw calculation

The main theoretical DPS proxy is Effective Raw:

```
EFR = True Raw × Sharpness Raw Multiplier × Affinity Multiplier
```

Two EFR states are calculated:

```
base_efr_critboost3
handicraft5_efr_critboost3
```

Where:

- `base_efr_critboost3` = no Handicraft, assuming Critical Boost 3
- `handicraft5_efr_critboost3` = Handicraft 5, assuming Critical Boost 3

Affinity multiplier:

```
if affinity >= 0:
    affinity_multiplier = 1 + affinity × 0.40
else:
    affinity_multiplier = 1 + affinity × 0.25
```

Negative affinity is still penalized by the normal negative-critical modifier and is not affected by Critical Boost.

### 2. Same-rarity baseline

For regular training weapons, the project calculates median EFR by rarity:

```
same-rarity baseline = median EFR of train_core weapons at the same rarity
```

Each weapon then receives a residual value:

```
EFR residual percent = weapon EFR / same-rarity median EFR - 1
```

This shows whether a weapon is above or below the expected curve for its progression tier.

### 3. Outlier labeling

Weapons are labeled based on their residual:

| Label | Meaning |
| --- | --- |
| `far_below_curve` | Significantly below the same-rarity curve |
| `below_curve` | Moderately below the curve |
| `on_curve` | Close to the expected curve |
| `above_curve` | Moderately above the curve |
| `possible_overtuned` | Substantially above the curve |
| `far_above_curve` | Extreme positive outlier |
| `no_baseline` | No available same-rarity baseline |

### 4. Visualization

The visualization script generates:

- Rarity baseline EFR charts
- Top base EFR weapons
- Top Handicraft 5 EFR weapons
- Handicraft gain charts
- Validation residual charts
- Base vs Handicraft 5 EFR scatter plots
- Outlier label distribution charts

### 5. Regression modeling

The regression script builds two interpretable models.

#### Model A: Stat Weight Model

Target:

```
handicraft5_efr_critboost3
```

Purpose:

```
Estimate how weapon-side stats contribute to raw-side theoretical DPS.
```

This model is partially formula-aligned with the EFR calculation, so it is used as a stat-weight sanity check rather than an independent prediction system.

#### Model B: Residual Explanation Model

Target:

```
handicraft5_efr_residual_percent
```

Purpose:

```
Explain which weapon features are associated with being above or below the same-rarity baseline curve.
```

This model is closer to hidden budget analysis because it studies deviation from expected same-rarity performance.

## Project structure

```
.
├── data/
│   ├── mhw_greatsword_filtered.csv
│   ├── mhw_greatsword_classified.csv
│   ├── mhw_greatsword_efr.csv
│   └── mhw_greatsword_efr_no_siege.csv
│
├── scripts/
│   ├── mhw_kiranico_greatsword_scraper.py
│   ├── mhw_greatsword_add_classification_fields.py
│   ├── mhw_greatsword_add_efr.py
│   ├── mhw_greatsword_exclude_siege_weapons.py
│   ├── mhw_greatsword_visualize_efr.py
│   └── mhw_greatsword_weapon_value_regression.py
│
├── mhw_greatsword_visuals/
│   ├── charts/
│   ├── summary_tables/
│   └── mhw_greatsword_visual_report.md
│
├── mhw_greatsword_regression_outputs/
│   ├── charts/
│   ├── regression_dataset_with_predictions.csv
│   ├── ridge_stat_weight_coefficients.csv
│   ├── ridge_residual_coefficients.csv
│   ├── model_metrics.csv
│   └── weapon_value_regression_report.md
│
└── README.md
```

## Installation

Use Python 3.11 or newer and keep the repository's folder structure.
From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

The dependency versions in `requirements.txt` match the verified offline environment.
For Chinese chart labels, install a font recognized by the scripts, such as
Noto Sans CJK SC, Microsoft YaHei, or PingFang SC. Without one, the analysis still
runs but some chart labels may be missing.

## Usage

### Reproduce from the committed data snapshot

```bash
python run_pipeline.py
```

This command runs classification, EFR calculation, siege exclusion, visualizations,
and regression in order. It reads `data/mhw_greatsword_filtered.csv` and rebuilds
derived CSV files in `data/` plus the two existing report folders. It does not
contact Kiranico. Re-running it overwrites generated outputs in those locations.

To rebuild only the three derived CSV files:

```bash
python run_pipeline.py --data-only
```

Every script resolves data and output paths relative to its own repository,
so execution does not depend on the shell's working directory. For example:

```bash
python /absolute/path/to/mhw-greatsword-stat-budget-analysis/run_pipeline.py
```

### Run an individual stage

Run these commands from the repository root, in dependency order:

```bash
python scripts/mhw_greatsword_add_classification_fields.py
python scripts/mhw_greatsword_add_efr.py
python scripts/mhw_greatsword_exclude_siege_weapons.py
python scripts/mhw_greatsword_visualize_efr.py
python scripts/mhw_greatsword_weapon_value_regression.py
```

### Check the numerical assumptions

```bash
python -m unittest discover -s tests -v
```

The tests cover positive and negative affinity, hand-calculated EFR, zero-base
relative gain, train-only rarity baselines, missing baselines, and label boundaries.
They verify these assumptions, not whether theoretical EFR predicts real hunt DPS.

### Optional: refresh source data

The scraper is separate from the offline pipeline:

```bash
python -m pip install -r requirements-scraper.txt
python scripts/mhw_kiranico_greatsword_scraper.py
```

It reads `data/greatsword_final_urls.txt`, contacts Kiranico, and overwrites
`data/mhw_greatsword_raw.csv` and `data/mhw_greatsword_filtered.csv`. Review its
source/filter rules before refreshing; the offline reproduction check does not
verify today's website structure or the completeness of freshly scraped data.

## Key outputs

### Visualization outputs

```
mhw_greatsword_visuals/charts/
mhw_greatsword_visuals/summary_tables/
mhw_greatsword_visuals/mhw_greatsword_visual_report.md
```

### Regression outputs

```
mhw_greatsword_regression_outputs/regression_dataset_with_predictions.csv
mhw_greatsword_regression_outputs/ridge_stat_weight_coefficients.csv
mhw_greatsword_regression_outputs/ridge_residual_coefficients.csv
mhw_greatsword_regression_outputs/model_metrics.csv
mhw_greatsword_regression_outputs/weapon_value_regression_report.md
```

## Interpretation notes

This analysis focuses on raw-side theoretical DPS.

It does not attempt to fully simulate real hunt performance.

Not included in the current DPS model:

- Elemental damage calculation
- Status buildup probability
- Monster-specific hitzones
- Motion value rotation timing
- Sharpness uptime over long combat windows
- Player execution
- Skill opportunity cost from decoration slots
- Matchup-specific utility

For this reason, EFR should be interpreted as a **weapon-side theoretical DPS proxy**, not as a complete ranking of real in-game performance.

## Design analysis framing

I treat each weapon as a stat-budget package composed of several interpretable components:

```
Raw / Affinity / Sharpness / Slots / Element or Status / Utility
```

The project uses EFR and residual modeling to examine how those components interact.

The goal is to identify trade-offs, isolate outliers, and infer how hidden weapon budget may be distributed across raw power, sharpness structure, slot value, element/status allocation, and source-specific reward tuning.

## Current limitations

- The project currently focuses only on Great Sword.
- The theoretical DPS model is raw-side only.
- Element and status value are treated as explanatory features, not full DPS contributors.
- Community usage data and speedrun adoption are not included.
- Regression results should be interpreted as design-analysis evidence, not production-grade predictive modeling.

## Future work

Potential extensions:

- Add other weapon types for cross-weapon budget comparison
- Incorporate motion value rotations for weapon-specific DPS simulation
- Add element and status DPS models
- Add decoration-slot opportunity cost modeling
- Compare theoretical DPS with community meta usage
- Build version-by-version progression curves
- Add interactive dashboards for weapon comparison

## Disclaimer

Monster Hunter: World / Iceborne is developed by Capcom.

This is an independent fan analysis project for educational and portfolio purposes.