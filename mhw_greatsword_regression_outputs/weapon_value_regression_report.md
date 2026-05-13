# Great Sword Weapon Value Regression Report

## 1. Modeling scope

This model uses `mhw_greatsword_efr_no_siege.csv`, which excludes Kulve Taroth / Taroth / Kjarr weapons and Safi'jiiva awakened weapons.

These siege, appraisal, and awakening weapon systems are excluded because their reward structures and stat budgets are not directly comparable to regular material weapon trees.

## 2. Model structure

### Model A: Stat Weight Model

Target variable:

```text
handicraft5_efr_critboost3
```

This model estimates how weapon-side stats contribute to raw-side theoretical DPS under the Handicraft 5 + Critical Boost 3 assumption.

### Model B: Residual Explanation Model

Target variable:

```text
handicraft5_efr_residual_percent
```

This model explains which weapon features are associated with being above or below the same-rarity baseline curve.

## 3. Model metrics

| model_name                        |   n_samples |   r2_in_sample |   mae_in_sample |   rmse_in_sample |   r2_cv_mean |   r2_cv_std |
|:----------------------------------|------------:|---------------:|----------------:|-----------------:|-------------:|------------:|
| ridge_stat_weight_handicraft5_efr |          44 |       0.997307 |      1.22598    |       1.46323    |    0.960144  |   0.0138337 |
| ridge_residual_explanation        |          44 |       0.983305 |      0.00649409 |       0.00791721 |    0.792834  |   0.0621969 |
| random_forest_residual_benchmark  |          44 |       0.865967 |      0.0171726  |       0.0224332  |    0.0242877 |   0.218358  |

The dataset is intentionally compact because it focuses on final-upgrade Great Swords after removing siege-system weapons. Cross-validation results should therefore be read as directional evidence rather than as production-scale predictive performance.

## 4. Stat Weight Model: top coefficients

| feature                                    |   coefficient |   abs_coefficient |
|:-------------------------------------------|--------------:|------------------:|
| true_raw                                   |      23.2823  |          23.2823  |
| affinity                                   |      16.9041  |          16.9041  |
| handicraft5_raw_sharpness_multiplier       |      10.2623  |          10.2623  |
| elderseal_小                               |       4.02189 |           4.02189 |
| source_category_detailed_rare_subspecies   |       3.38903 |           3.38903 |
| elderseal_中                               |      -3.32215 |           3.32215 |
| element_type_麻痹                          |       3.20192 |           3.20192 |
| handicraft5_max_sharpness_blue             |      -2.86385 |           2.86385 |
| handicraft_value_type_extends_same_tier    |      -2.86385 |           2.86385 |
| source_category_detailed_event_special     |      -2.51677 |           2.51677 |
| element_type_龙                            |      -2.4982  |           2.4982  |
| source_category_detailed_material_standard |      -2.1353  |           2.1353  |
| handicraft5_max_sharpness_purple           |       2.05419 |           2.05419 |
| element_type_雷                            |      -1.8739  |           1.8739  |
| source_category_detailed_guild_palace      |       1.69694 |           1.69694 |
| handicraft_value_type_unlocks_white        |       1.20391 |           1.20391 |
| base_max_sharpness_white                   |      -1.17362 |           1.17362 |
| source_category_detailed_elder_dragon      |      -1.16707 |           1.16707 |
| sharpness_comfort_gain                     |       1.15463 |           1.15463 |
| slot_count                                 |      -1.11586 |           1.11586 |

Related charts:

```text
charts/01_ridge_stat_weight_coefficients.png
charts/03_predicted_vs_actual_efr.png
```

## 5. Residual Explanation Model: top coefficients

| feature                                    |   coefficient |   abs_coefficient |
|:-------------------------------------------|--------------:|------------------:|
| true_raw                                   |    0.0594864  |        0.0594864  |
| affinity                                   |    0.0428824  |        0.0428824  |
| rarity                                     |   -0.0395597  |        0.0395597  |
| handicraft5_raw_sharpness_multiplier       |    0.0208186  |        0.0208186  |
| element_type_麻痹                          |    0.01499    |        0.01499    |
| source_category_detailed_event_special     |   -0.0137237  |        0.0137237  |
| element_type_龙                            |   -0.0120666  |        0.0120666  |
| sharpness_comfort_gain                     |    0.0120417  |        0.0120417  |
| elderseal_中                               |   -0.0114966  |        0.0114966  |
| element_type_雷                            |   -0.0114192  |        0.0114192  |
| source_category_detailed_rare_subspecies   |    0.00972941 |        0.00972941 |
| source_category_detailed_guild_palace      |    0.00813133 |        0.00813133 |
| elderseal_大                               |    0.00684014 |        0.00684014 |
| source_category_detailed_material_standard |   -0.00680428 |        0.00680428 |
| element_type_火                            |    0.00653716 |        0.00653716 |
| base_high_sharpness_units                  |   -0.0057319  |        0.0057319  |
| model_role_validation_marked               |   -0.00559239 |        0.00559239 |
| base_max_sharpness_white                   |   -0.00549014 |        0.00549014 |
| element_type_睡眠                          |    0.00542624 |        0.00542624 |
| handicraft_value_type_extends_same_tier    |   -0.00532059 |        0.00532059 |

Related charts:

```text
charts/02_ridge_residual_coefficients.png
charts/04_predicted_vs_actual_residual.png
charts/05_largest_residual_model_errors.png
```

## 6. Highest positive residual weapons

| weapon_name        |   rarity | source_category_detailed   | model_role         |   handicraft5_efr_critboost3 |   handicraft5_efr_residual_percent | handicraft5_efr_outlier_label   |
|:-------------------|---------:|:---------------------------|:-------------------|-----------------------------:|-----------------------------------:|:--------------------------------|
| 罪罚粉碎者2        |       11 | material_standard          | train_core         |                      403.1   |                          0.115385  | possible_overtuned              |
| 碎光之击剑         |       12 | variant_endgame            | validation_special |                      417     |                          0.111111  | possible_overtuned              |
| 狂击巨凶           |       11 | material_standard          | train_core         |                      397.818 |                          0.100769  | possible_overtuned              |
| 辉剑火龙           |       12 | rare_subspecies            | train_core         |                      412.83  |                          0.1       | possible_overtuned              |
| 隐密之炎2          |       10 | material_standard          | train_core         |                      366.96  |                          0.1       | possible_overtuned              |
| 鬼神金棒【猿魔王】 |       12 | variant_endgame            | validation_special |                      412.552 |                          0.0992593 | above_curve                     |
| 冥灯龙大剑改       |       12 | elder_dragon               | train_core         |                      399.168 |                          0.0635971 | above_curve                     |
| 宫廷王剑【金星】   |       12 | guild_palace               | validation_marked  |                      397.818 |                          0.06      | above_curve                     |
| 钢龙寒冰大剑       |       11 | elder_dragon               | train_core         |                      383.084 |                          0.06      | above_curve                     |
| 大鬼金棒           |       12 | material_standard          | train_core         |                      393.855 |                          0.0494404 | on_curve                        |
| 兵器蛮雷大剑       |       11 | material_standard          | train_core         |                      377.52  |                          0.0446043 | on_curve                        |
| 斩龙之炎2          |       10 | material_standard          | train_core         |                      347.5   |                          0.0416667 | on_curve                        |
| 断海冰牙           |       11 | material_standard          | train_core         |                      376.2   |                          0.0409519 | on_curve                        |
| 无相法身－不动－   |       12 | elder_dragon               | train_core         |                      389.2   |                          0.037037  | on_curve                        |
| 贼龙兵器2          |       10 | material_standard          | train_core         |                      343.2   |                          0.028777  | on_curve                        |

## 7. Highest negative residual weapons

| weapon_name        |   rarity | source_category_detailed   | model_role        |   handicraft5_efr_critboost3 |   handicraft5_efr_residual_percent | handicraft5_efr_outlier_label   |
|:-------------------|---------:|:---------------------------|:------------------|-----------------------------:|-----------------------------------:|:--------------------------------|
| 封龙大剑2          |       11 | elder_dragon               | train_core        |                      316.8   |                         -0.123409  | far_below_curve                 |
| 召雷剑【麒麟帝】   |       11 | elder_dragon               | train_core        |                      316.8   |                         -0.123409  | far_below_curve                 |
| 瞬间冷冻剑鱼       |       11 | event_special              | validation_marked |                      316.8   |                         -0.123409  | far_below_curve                 |
| 怨憎怪物           |       12 | elder_dragon               | train_core        |                      330     |                         -0.120703  | far_below_curve                 |
| 爆大剑恶霸之刃     |       11 | material_standard          | train_core        |                      330     |                         -0.0868843 | below_curve                     |
| 夜神剃刀2          |       10 | material_standard          | train_core        |                      316.8   |                         -0.0503597 | below_curve                     |
| 业剑暗黑暴食       |       12 | material_standard          | train_core        |                      360.01  |                         -0.0407407 | on_curve                        |
| 迅雷断裂斧2        |       11 | material_standard          | train_core        |                      347.5   |                         -0.0384615 | on_curve                        |
| 爆热机关式【银翼】 |       12 | event_special              | validation_marked |                      361.226 |                         -0.0375    | on_curve                        |
| 龙颚剑【绝牙】     |       11 | material_standard          | train_core        |                      348     |                         -0.037078  | on_curve                        |
| 轰大剑【王虎】     |       11 | material_standard          | train_core        |                      351.12  |                         -0.0284449 | on_curve                        |
| 魂焰刚剑·冥灯      |       12 | elder_dragon               | train_core        |                      368.35  |                         -0.0185185 | on_curve                        |
| 灭鬼凶器【断】     |       12 | elder_dragon               | train_core        |                      369.6   |                         -0.0151878 | on_curve                        |
| 兵器蛮炎大剑       |       10 | material_standard          | train_core        |                      329.67  |                         -0.0117806 | on_curve                        |
| 火碎剑2            |       10 | material_standard          | train_core        |                      330     |                         -0.0107914 | on_curve                        |

## 8. Design interpretation

I treat each weapon as a stat-budget package composed of several interpretable components:

```text
Raw / Affinity / Sharpness / Slots / Element or Status / Utility
```

The coefficient tables are used to examine which components explain raw-side theoretical DPS, while the residual model highlights which weapons sit above or below the same-rarity baseline after normalizing for progression tier.

In this project, the regression model is used as a balance-design lens rather than a black-box predictor. The goal is to identify stat trade-offs, isolate outlier weapons, and infer how hidden weapon budget may have been distributed across raw power, sharpness structure, slot value, elemental/status allocation, and source-specific reward tuning.
