"""
tests/test_sanitizer.py — Unit tests for sanitizer.clean_sensor_readings.

Run with:
    python -m unittest discover -s tests
"""

import math
import unittest

from sanitizer import clean_sensor_readings


class TestCleanSensorReadings(unittest.TestCase):
    """Comprehensive tests for clean_sensor_readings()."""

    # ------------------------------------------------------------------
    # Basic valid inputs
    # ------------------------------------------------------------------

    def test_integers_are_accepted(self) -> None:
        result = clean_sensor_readings([0, 100, 250])
        self.assertEqual(result, [0.0, 100.0, 250.0])

    def test_floats_are_accepted(self) -> None:
        result = clean_sensor_readings([1.5, 99.9, 499.99])
        self.assertAlmostEqual(result[0], 1.5)
        self.assertAlmostEqual(result[1], 99.9)
        self.assertAlmostEqual(result[2], 499.99)

    def test_zero_is_accepted(self) -> None:
        result = clean_sensor_readings([0])
        self.assertEqual(result, [0.0])

    def test_numeric_strings_are_accepted(self) -> None:
        result = clean_sensor_readings(["42", "3.14", "500"])
        self.assertEqual(result, [42.0, 3.14, 500.0])

    # ------------------------------------------------------------------
    # Capping
    # ------------------------------------------------------------------

    def test_values_above_500_are_capped(self) -> None:
        result = clean_sensor_readings([501, 1000, 999.9])
        self.assertEqual(result, [500.0, 500.0, 500.0])

    def test_exactly_500_is_kept(self) -> None:
        result = clean_sensor_readings([500.0])
        self.assertEqual(result, [500.0])

    def test_mixed_capped_and_valid(self) -> None:
        result = clean_sensor_readings([300.0, 600.0, 200.0])
        self.assertEqual(result, [300.0, 500.0, 200.0])

    # ------------------------------------------------------------------
    # Rejection of invalid values
    # ------------------------------------------------------------------

    def test_none_is_rejected(self) -> None:
        result = clean_sensor_readings([None])
        self.assertEqual(result, [])

    def test_invalid_string_is_rejected(self) -> None:
        result = clean_sensor_readings(["abc", "N/A", "??"])
        self.assertEqual(result, [])

    def test_negative_numbers_are_rejected(self) -> None:
        result = clean_sensor_readings([-1, -0.001, -500])
        self.assertEqual(result, [])

    def test_nan_is_rejected(self) -> None:
        result = clean_sensor_readings([float("nan")])
        self.assertEqual(result, [])

    def test_positive_infinity_is_rejected(self) -> None:
        result = clean_sensor_readings([float("inf")])
        self.assertEqual(result, [])

    def test_negative_infinity_is_rejected(self) -> None:
        result = clean_sensor_readings([float("-inf")])
        self.assertEqual(result, [])

    # ------------------------------------------------------------------
    # Booleans
    # ------------------------------------------------------------------

    def test_true_is_rejected(self) -> None:
        """bool is a subclass of int, but True must not become 1.0."""
        result = clean_sensor_readings([True])
        self.assertEqual(result, [])

    def test_false_is_rejected(self) -> None:
        result = clean_sensor_readings([False])
        self.assertEqual(result, [])

    def test_bool_among_valid_values(self) -> None:
        result = clean_sensor_readings([10.0, True, 20.0, False])
        self.assertEqual(result, [10.0, 20.0])

    # ------------------------------------------------------------------
    # Empty / entirely invalid input
    # ------------------------------------------------------------------

    def test_empty_list_returns_empty(self) -> None:
        result = clean_sensor_readings([])
        self.assertEqual(result, [])

    def test_entirely_invalid_input_returns_empty(self) -> None:
        result = clean_sensor_readings([None, "bad", -1, True, float("nan")])
        self.assertEqual(result, [])

    # ------------------------------------------------------------------
    # Mixed valid and invalid
    # ------------------------------------------------------------------

    def test_mixed_values(self) -> None:
        raw = [10.0, None, "bad", -5, 200, True, 600, float("nan"), "50"]
        result = clean_sensor_readings(raw)
        self.assertEqual(result, [10.0, 200.0, 500.0, 50.0])

    def test_order_is_preserved(self) -> None:
        raw = [300.0, 100.0, 50.0]
        result = clean_sensor_readings(raw)
        self.assertEqual(result, [300.0, 100.0, 50.0])

    # ------------------------------------------------------------------
    # Immutability of original list
    # ------------------------------------------------------------------

    def test_original_list_is_not_mutated(self) -> None:
        original = [10, None, "bad", 600, -3, 50]
        original_copy = list(original)
        clean_sensor_readings(original)
        self.assertEqual(original, original_copy)

    # ------------------------------------------------------------------
    # Return type
    # ------------------------------------------------------------------

    def test_all_results_are_floats(self) -> None:
        result = clean_sensor_readings([1, "2", 3.0])
        for val in result:
            self.assertIsInstance(val, float)

    def test_all_results_are_finite_and_non_negative(self) -> None:
        raw = [0, 100, 500, 250.5, "99"]
        result = clean_sensor_readings(raw)
        for val in result:
            self.assertTrue(math.isfinite(val))
            self.assertGreaterEqual(val, 0.0)
            self.assertLessEqual(val, 500.0)

    # ------------------------------------------------------------------
    # Edge / boundary values
    # ------------------------------------------------------------------

    def test_boundary_500_exact(self) -> None:
        self.assertEqual(clean_sensor_readings([500.0]), [500.0])

    def test_boundary_just_above_500(self) -> None:
        self.assertEqual(clean_sensor_readings([500.0001]), [500.0])

    def test_boundary_just_below_zero(self) -> None:
        self.assertEqual(clean_sensor_readings([-0.0001]), [])

    def test_negative_zero_is_accepted(self) -> None:
        """Negative zero (-0.0) compares equal to 0.0 and should be accepted."""
        result = clean_sensor_readings([-0.0])
        self.assertEqual(result, [0.0])

    def test_very_large_numeric_string_is_capped(self) -> None:
        result = clean_sensor_readings(["1e10"])
        self.assertEqual(result, [500.0])


if __name__ == "__main__":
    unittest.main()
