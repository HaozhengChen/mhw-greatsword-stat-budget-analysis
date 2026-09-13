"""Protect analysis assumptions with hand-calculated examples."""

import unittest

import pandas as pd

from scripts.mhw_greatsword_add_efr import (
    add_rarity_baselines, affinity_multiplier, calculate_efr, classify_outlier,
)


class EfrContractTests(unittest.TestCase):
    def test_positive_affinity_uses_selected_critical_bonus(self):
        self.assertAlmostEqual(affinity_multiplier(25, 0.25), 1.0625)
        self.assertAlmostEqual(affinity_multiplier(25, 0.40), 1.1)

    def test_negative_affinity_is_not_improved_by_critical_boost(self):
        self.assertAlmostEqual(affinity_multiplier(-30, 0.25), 0.925)
        self.assertAlmostEqual(affinity_multiplier(-30, 0.40), 0.925)

    def test_zero_affinity_and_hand_calculated_efr(self):
        result = calculate_efr(pd.Series({
            "true_raw": 100, "affinity": 0,
            "base_raw_sharpness_multiplier": 1.20,
            "handicraft5_raw_sharpness_multiplier": 1.32,
        }))
        self.assertAlmostEqual(result["base_efr_critboost3"], 120)
        self.assertAlmostEqual(result["handicraft5_efr_critboost3"], 132)
        self.assertAlmostEqual(result["efr_gain_from_handicraft_percent_critboost3"], .1)

    def test_zero_base_efr_has_no_relative_gain(self):
        result = calculate_efr(pd.Series({"true_raw": 0}))
        self.assertTrue(pd.isna(result["efr_gain_from_handicraft_percent_critboost3"]))

    def test_special_weapons_do_not_set_the_training_baseline(self):
        frame = pd.DataFrame({
            "rarity": [10, 10, 10, 12],
            "include_in_efr_train": [True, True, False, False],
            "base_efr_critboost3": [100., 120., 999., 200.],
            "handicraft5_efr_critboost3": [110., 130., 999., 220.],
        })
        result = add_rarity_baselines(frame)
        self.assertEqual(result.loc[2, "rarity_median_base_efr_critboost3"], 110)
        self.assertEqual(result.loc[2, "rarity_median_handicraft5_efr_critboost3"], 120)
        self.assertEqual(result.loc[3, "base_efr_outlier_label"], "no_baseline")
        self.assertTrue(pd.isna(result.loc[3, "base_efr_residual_percent"]))

    def test_outlier_threshold_boundaries(self):
        cases = [(-.101, "far_below_curve"), (-.10, "below_curve"),
                 (-.05, "on_curve"), (.05, "on_curve"),
                 (.10, "above_curve"), (.20, "possible_overtuned"),
                 (.201, "far_above_curve"), (float("nan"), "no_baseline")]
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(classify_outlier(value), expected)


if __name__ == "__main__":
    unittest.main()
