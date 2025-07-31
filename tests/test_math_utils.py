import unittest
from utils.math_utils import count_solutions, optimal_grover_iterations


class TestMathUtils(unittest.TestCase):
    def test_invalid_inputs_raise_error(self):
        invalid_cases = [
            (-5, 2, 3),  # negative num_bits
            (5, 2, -3),  # negative n
            (5, -2, -3),  # zero num_bits
            (-5, 2, -3),  # zero num_vars
            (5, -2, 3),
            (0, 5),
            (0, 0, 0),
            (1, 5, 0),
        ]

        for case in invalid_cases:
            with self.assertRaises(ValueError):
                count_solutions(*case)

    def test_count_solutions_basic(self):
        self.assertEqual(count_solutions(4, 46), 0)
        self.assertEqual(count_solutions(5, 1, 5), 5)
        self.assertEqual(count_solutions(3, 10), 48)
        self.assertEqual(count_solutions(4, 0), 1)
        self.assertEqual(count_solutions(4, 1), 3)
        self.assertEqual(count_solutions(4, 2), 6)

    def test_count_solutions_with_upper_bound(self):
        # When n > 2^k but still valid
        self.assertEqual(count_solutions(4, 20), 186)  # Precomputed expected value
        # Edge case: n larger than max possible sum (should be 0)
        self.assertEqual(count_solutions(4, 1000), 0)

    def test_optimal_grover_iterations(self):
        # Basic case: target sum = 0
        self.assertEqual(optimal_grover_iterations(4, 0), 50)  # Only one solution
        # Another case: n=5 with 3 variables
        result = optimal_grover_iterations(4, 5)
        self.assertTrue(isinstance(result, int))
        self.assertGreaterEqual(result, 0)

if __name__ == "__main__":
    unittest.main()
