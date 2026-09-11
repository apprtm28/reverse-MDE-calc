import importlib.util
import os
import unittest

import numpy as np
from scipy import stats

MODULE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "reverse-ab-calc.py")
)


def load_module():
    spec = importlib.util.spec_from_file_location("reverse_ab_calc", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


calc = load_module()


class TestSignificanceToZ(unittest.TestCase):
    def test_two_sided_alpha_005(self):
        self.assertAlmostEqual(calc.significance_to_z(0.05, True), 1.95996398, places=6)

    def test_one_sided_alpha_005(self):
        self.assertAlmostEqual(calc.significance_to_z(0.05, False), 1.64485363, places=6)


class TestTwoProportionPower(unittest.TestCase):
    def test_null_effect_power_equals_alpha_two_sided(self):
        for alpha in (0.05, 0.01, 0.10):
            power = calc.two_proportion_power(0.0, 1000, 0.30, alpha, two_sided=True)
            self.assertAlmostEqual(power, alpha, places=6)

    def test_null_effect_power_equals_alpha_one_sided(self):
        power = calc.two_proportion_power(0.0, 1000, 0.30, 0.05, two_sided=False)
        self.assertAlmostEqual(power, 0.05, places=6)

    def test_power_increases_with_effect(self):
        powers = [
            calc.two_proportion_power(e, 10000, 0.30, 0.05, two_sided=True)
            for e in np.linspace(0.0, 0.5, 25)
        ]
        self.assertTrue(all(b >= a for a, b in zip(powers, powers[1:])))

    def test_power_defined_for_negative_effects(self):
        for e in (-0.25, -0.1, -0.05):
            power = calc.two_proportion_power(e, 5000, 0.20)
            self.assertTrue(np.isfinite(power))
            self.assertGreater(power, 0.0)
            self.assertLessEqual(power, 1.0)

    def test_invalid_alternative_rate_is_finite(self):
        power = calc.two_proportion_power(0.5, 1000, 0.90)
        self.assertTrue(np.isfinite(power))
        self.assertGreaterEqual(power, 0.0)
        self.assertLessEqual(power, 1.0)


class TestCalculateMde(unittest.TestCase):
    def test_round_trip_hits_target_power(self):
        for baseline in (0.05, 0.30, 0.60):
            for n in (500, 10000, 250000):
                mde = calc.calculate_mde(n, baseline, power=0.8, significance_level=0.05)
                achieved = calc.two_proportion_power(mde, n, baseline, 0.05, True)
                self.assertAlmostEqual(achieved, 0.8, places=3)

    def test_known_value(self):
        mde = calc.calculate_mde(10000, 0.30, power=0.8, significance_level=0.05)
        self.assertAlmostEqual(mde, 0.0610, delta=0.002)

    def test_larger_sample_reduces_mde(self):
        small = calc.calculate_mde(5000, 0.30)
        large = calc.calculate_mde(50000, 0.30)
        self.assertLess(large, small)

    def test_high_baseline_stays_valid(self):
        for baseline in (0.90, 0.95, 0.99):
            mde = calc.calculate_mde(1000, baseline)
            self.assertTrue(np.isfinite(mde))
            self.assertGreater(mde, 0)
            self.assertLessEqual(baseline * (1 + mde), 1.0 + 1e-9)


class TestCalculateRequiredSampleSize(unittest.TestCase):
    def test_round_trip_hits_target_power(self):
        for baseline in (0.05, 0.30):
            for mde in (0.05, 0.1, 0.2):
                n = calc.calculate_required_sample_size(mde, baseline)
                achieved = calc.two_proportion_power(mde, n, baseline, 0.05, True)
                self.assertGreaterEqual(achieved, 0.8)
                self.assertLess(achieved, 0.8005)

    def test_known_value(self):
        n = calc.calculate_required_sample_size(0.10, 0.30)
        self.assertAlmostEqual(n, 3760, delta=60)

    def test_larger_mde_needs_fewer_samples(self):
        small = calc.calculate_required_sample_size(0.05, 0.30)
        large = calc.calculate_required_sample_size(0.20, 0.30)
        self.assertLess(large, small)


class TestEvaluateTest(unittest.TestCase):
    def setUp(self):
        self.control = (1000, 300)
        self.variant_up = (1000, 350)
        self.variant_down = (1000, 250)

    def test_two_sided_increase(self):
        r = calc.evaluate_test(*self.control, *self.variant_up, two_sided=True)
        self.assertAlmostEqual(r["p_value"], 0.01683, places=4)
        self.assertTrue(r["significant"])
        self.assertGreater(r["uplift"], 0)

    def test_two_sided_decrease_is_significant(self):
        r = calc.evaluate_test(*self.control, *self.variant_down, two_sided=True)
        self.assertAlmostEqual(r["p_value"], 0.01214, delta=0.0005)
        self.assertTrue(r["significant"])
        self.assertLess(r["uplift"], 0)

    def test_one_sided_greater_increase_is_significant(self):
        r = calc.evaluate_test(
            *self.control, *self.variant_up, two_sided=False, alternative="greater"
        )
        self.assertAlmostEqual(r["p_value"], 0.00842, delta=0.0003)
        self.assertTrue(r["significant"])

    def test_one_sided_greater_decrease_is_not_significant(self):
        r = calc.evaluate_test(
            *self.control, *self.variant_down, two_sided=False, alternative="greater"
        )
        self.assertGreater(r["p_value"], 0.99)
        self.assertFalse(r["significant"])

    def test_one_sided_less_decrease_is_significant(self):
        r = calc.evaluate_test(
            *self.control, *self.variant_down, two_sided=False, alternative="less"
        )
        self.assertAlmostEqual(r["p_value"], 0.00607, delta=0.0003)
        self.assertTrue(r["significant"])

    def test_one_sided_less_increase_is_not_significant(self):
        r = calc.evaluate_test(
            *self.control, *self.variant_up, two_sided=False, alternative="less"
        )
        self.assertGreater(r["p_value"], 0.99)
        self.assertFalse(r["significant"])

    def test_one_sided_pvalues_sum_to_one(self):
        for variant in (self.variant_up, self.variant_down):
            greater = calc.evaluate_test(
                *self.control, *variant, two_sided=False, alternative="greater"
            )["p_value"]
            less = calc.evaluate_test(
                *self.control, *variant, two_sided=False, alternative="less"
            )["p_value"]
            self.assertAlmostEqual(greater + less, 1.0, places=10)

    def test_two_sided_pvalue_is_twice_min_one_sided(self):
        two = calc.evaluate_test(*self.control, *self.variant_up, two_sided=True)["p_value"]
        greater = calc.evaluate_test(
            *self.control, *self.variant_up, two_sided=False, alternative="greater"
        )["p_value"]
        less = calc.evaluate_test(
            *self.control, *self.variant_up, two_sided=False, alternative="less"
        )["p_value"]
        self.assertAlmostEqual(two, 2 * min(greater, less), places=10)

    def test_standard_error_of_difference(self):
        r = calc.evaluate_test(*self.control, *self.variant_up)
        expected = np.sqrt(0.30 * 0.70 / 1000 + 0.35 * 0.65 / 1000)
        self.assertAlmostEqual(r["se_diff"], expected, places=12)

    def test_zero_control_rate_does_not_crash(self):
        r = calc.evaluate_test(1000, 0, 1000, 50, two_sided=True)
        self.assertEqual(r["uplift"], 0.0)
        self.assertTrue(np.isfinite(r["p_value"]))

    def test_zero_conversions_both_groups(self):
        r = calc.evaluate_test(1000, 0, 1000, 0, two_sided=True)
        self.assertEqual(r["p_value"], 1.0)
        self.assertFalse(r["significant"])

    def test_outputs_are_finite_for_valid_inputs(self):
        r = calc.evaluate_test(5000, 400, 5000, 450)
        for key in ("z_score", "p_value", "se_control", "se_variant", "se_diff"):
            self.assertTrue(np.isfinite(r[key]), key)


if __name__ == "__main__":
    unittest.main()
