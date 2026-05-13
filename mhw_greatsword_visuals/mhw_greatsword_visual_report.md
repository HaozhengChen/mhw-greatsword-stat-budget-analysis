# MHW: Iceborne Great Sword Theoretical DPS Visualization Report

## 1. Analysis scope

This report uses `mhw_greatsword_efr.csv` as the input dataset.

The current theoretical DPS metric is a raw-side EFR proxy:

```text
EFR = True Raw × Sharpness Raw Multiplier × Affinity Multiplier
```

The report compares two weapon states:

- `base_efr_critboost3`: no Handicraft, assuming Critical Boost 3
- `handicraft5_efr_critboost3`: Handicraft 5, assuming Critical Boost 3

This is not a full in-game DPS simulation. It does not include elemental damage, status buildup, slot-to-skill conversion, sharpness uptime, animation timing, hitzone selection, or player execution.

## 2. Dataset segmentation

### model_role counts

| model_role         |   count |
|:-------------------|--------:|
| validation_special |      68 |
| train_core         |      39 |
| validation_marked  |       3 |

### source_category_detailed counts

| source_category_detailed   |   count |
|:---------------------------|--------:|
| siege_kulve                |      48 |
| material_standard          |      26 |
| siege_safi                 |      18 |
| elder_dragon               |      12 |
| variant_endgame            |       2 |
| event_special              |       2 |
| rare_subspecies            |       1 |
| guild_palace               |       1 |

## 3. Same-rarity EFR baseline

The baseline is calculated from weapons with `include_in_efr_train = True`. Median EFR by rarity is used as the reference curve for regular material-tree weapons.

|   rarity |   train_count |   median_base_efr |   median_handicraft5_efr |   mean_base_efr |   mean_handicraft5_efr |
|---------:|--------------:|------------------:|-------------------------:|----------------:|-----------------------:|
|       10 |            11 |            316.8  |                    333.6 |         324.005 |                336.901 |
|       11 |            15 |            343.2  |                    361.4 |         342.302 |                360.672 |
|       12 |            13 |            358.05 |                    375.3 |         362.718 |                377.233 |

Related chart:

```text
charts/01_rarity_baseline_efr.png
```

## 4. Training set: top 10 base EFR

| weapon_name      |   rarity | source_category_detailed   |   true_raw |   affinity | base_max_sharpness   |   base_efr_critboost3 |   base_efr_residual_percent | base_efr_outlier_label   |
|:-----------------|---------:|:---------------------------|-----------:|-----------:|:---------------------|----------------------:|----------------------------:|:-------------------------|
| 冥灯龙大剑改     |       12 | elder_dragon               |        280 |         20 | white                |               399.168 |                   0.114839  | possible_overtuned       |
| 狂击巨凶         |       11 | material_standard          |        270 |         15 | purple               |               397.818 |                   0.159143  | possible_overtuned       |
| 辉剑火龙         |       12 | rare_subspecies            |        270 |         25 | white                |               392.04  |                   0.0949309 | above_curve              |
| 断海冰牙         |       11 | material_standard          |        250 |         35 | white                |               376.2   |                   0.0961538 | above_curve              |
| 狱界断罪斧改     |       12 | material_standard          |        270 |          0 | purple               |               375.3   |                   0.0481776 | on_curve                 |
| 无相法身－不动－ |       12 | elder_dragon               |        280 |          0 | white                |               369.6   |                   0.0322581 | on_curve                 |
| 灭鬼凶器【断】   |       12 | elder_dragon               |        280 |          0 | white                |               369.6   |                   0.0322581 | on_curve                 |
| 隐密之炎2        |       10 | material_standard          |        240 |         25 | purple               |               366.96  |                   0.158333  | possible_overtuned       |
| 钢龙寒冰大剑     |       11 | elder_dragon               |        260 |         15 | white                |               363.792 |                   0.06      | above_curve              |
| 魂焰刚剑·炎妃    |       12 | elder_dragon               |        250 |         25 | white                |               363     |                   0.0138249 | on_curve                 |

Related chart:

```text
charts/02_train_core_r12_top_base_efr.png
```

## 5. Training set: top 10 Handicraft 5 EFR

| weapon_name      |   rarity | source_category_detailed   |   true_raw |   affinity | handicraft5_max_sharpness   |   handicraft5_efr_critboost3 |   handicraft5_efr_residual_percent | handicraft5_efr_outlier_label   |
|:-----------------|---------:|:---------------------------|-----------:|-----------:|:----------------------------|-----------------------------:|-----------------------------------:|:--------------------------------|
| 辉剑火龙         |       12 | rare_subspecies            |        270 |         25 | purple                      |                      412.83  |                          0.1       | possible_overtuned              |
| 罪罚粉碎者2      |       11 | material_standard          |        290 |          0 | purple                      |                      403.1   |                          0.115385  | possible_overtuned              |
| 冥灯龙大剑改     |       12 | elder_dragon               |        280 |         20 | white                       |                      399.168 |                          0.0635971 | above_curve                     |
| 狂击巨凶         |       11 | material_standard          |        270 |         15 | purple                      |                      397.818 |                          0.100769  | possible_overtuned              |
| 大鬼金棒         |       12 | material_standard          |        310 |        -15 | white                       |                      393.855 |                          0.0494404 | on_curve                        |
| 无相法身－不动－ |       12 | elder_dragon               |        280 |          0 | purple                      |                      389.2   |                          0.037037  | on_curve                        |
| 钢龙寒冰大剑     |       11 | elder_dragon               |        260 |         15 | purple                      |                      383.084 |                          0.06      | above_curve                     |
| 魂焰刚剑·炎妃    |       12 | elder_dragon               |        250 |         25 | purple                      |                      382.25  |                          0.0185185 | on_curve                        |
| 兵器蛮雷大剑     |       11 | material_standard          |        260 |         25 | white                       |                      377.52  |                          0.0446043 | on_curve                        |
| 断海冰牙         |       11 | material_standard          |        250 |         35 | white                       |                      376.2   |                          0.0409519 | on_curve                        |

Related charts:

```text
charts/03_train_core_r12_top_handicraft5_efr.png
charts/04_top_handicraft_efr_gain_percent.png
```

## 6. Validation set: deviation from the regular weapon curve

Validation weapons are not used to define the baseline. They are retained to check how special sources deviate from the regular material-tree curve.

| weapon_name        |   rarity | source_category_detailed   |   handicraft5_efr_critboost3 |   handicraft5_efr_residual_percent | handicraft5_efr_outlier_label   |
|:-------------------|---------:|:---------------------------|-----------------------------:|-----------------------------------:|:--------------------------------|
| 碎光之击剑         |       12 | variant_endgame            |                      417     |                          0.111111  | possible_overtuned              |
| 鬼神金棒【猿魔王】 |       12 | variant_endgame            |                      412.552 |                          0.0992593 | above_curve                     |
| 宫廷王剑【金星】   |       12 | guild_palace               |                      397.818 |                          0.06      | above_curve                     |
| 赤龙断绝剑·水      |       12 | siege_safi                 |                      363.528 |                         -0.0313669 | on_curve                        |
| 赤龙断绝剑·火      |       12 | siege_safi                 |                      363.528 |                         -0.0313669 | on_curve                        |
| 赤龙断绝剑·爆破    |       12 | siege_safi                 |                      363.528 |                         -0.0313669 | on_curve                        |
| 赤龙断绝剑·火      |       12 | siege_safi                 |                      363.528 |                         -0.0313669 | on_curve                        |
| 赤龙断绝剑·冰      |       12 | siege_safi                 |                      363.528 |                         -0.0313669 | on_curve                        |
| 赤龙断绝剑·雷      |       12 | siege_safi                 |                      363.528 |                         -0.0313669 | on_curve                        |
| 赤龙断绝剑·龙      |       12 | siege_safi                 |                      363.528 |                         -0.0313669 | on_curve                        |

Related charts:

```text
charts/05_validation_handicraft5_residuals.png
charts/06_base_vs_handicraft5_efr_scatter.png
charts/07_handicraft5_outlier_label_counts.png
```

## 7. Interpretation guide

- `on_curve`: the weapon is close to the same-rarity raw-side EFR baseline.
- `above_curve`: the weapon is moderately above the baseline, usually due to favorable raw, affinity, or sharpness structure.
- `possible_overtuned`: the weapon is substantially above the same-rarity baseline and should be reviewed as a potential high-budget or late-progression reward case.
- `far_below_curve`: the weapon is significantly below the raw-side EFR baseline. Its budget may be allocated to element/status value, slots, utility, special acquisition systems, or historical version context.

## 8. Next step: weapon value regression

For the next modeling step, the recommended primary target is:

```text
handicraft5_efr_critboost3
```

A second analysis can use the same-rarity residual as the target:

```text
handicraft5_efr_residual_percent
```

Candidate features:

- `true_raw`
- `affinity`
- `base_raw_sharpness_multiplier`
- `handicraft5_raw_sharpness_multiplier`
- `base_white_units`, `base_purple_units`
- `handicraft5_white_units`, `handicraft5_purple_units`
- `slot_1`, `slot_2`, `slot_3`
- `element_value`
- `is_hidden_element`
- `source_category_detailed`

Start with an interpretable linear model, then optionally compare it against nonlinear benchmarks such as Random Forest or gradient-boosted trees.
