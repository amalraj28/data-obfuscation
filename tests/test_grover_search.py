import unittest
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

from circuits.adder_builder import AdderBuilder
from algorithms.grover_search import GroverSearch
from utils.math_utils import optimal_grover_iterations


class TestGroverSearch(unittest.TestCase):
    def setUp(self):
        self.num_bits = 3
        self.target = 4
        self.adder = AdderBuilder(self.num_bits)
        self.grover = GroverSearch(self.adder)
        self.shots = 1024
        self.backend = AerSimulator()

    def test_build_oracle(self):
        oracle_gate = self.grover.build_oracle(self.target)
        self.assertIsInstance(oracle_gate, type(QuantumCircuit().to_gate()))
        self.assertEqual(oracle_gate.num_qubits, self.grover.num_qubits)

    def test_build_diffuser(self):
        diffuser_gate = self.grover.build_diffuser()
        self.assertEqual(diffuser_gate.num_qubits, len(self.grover.input_qubits) + 1)

    def test_apply_grover_iterations_structure(self):
        iterations = 2
        self.grover.apply_grover_iterations(self.target, iterations)
        self.assertGreater(len(self.grover.qc.data), 0)

    def test_decode_results(self):
        counts = {"000111000": 10, "001010011": 5}
        decoded = self.grover.decode_results(counts)
        self.assertEqual(decoded[0]["freq"], 10)
        self.assertIn("x", decoded[0])
        self.assertIn("y", decoded[0])
        self.assertIn("z", decoded[0])

    def test_integration_grover_search_mid_target(self):
        iterations = optimal_grover_iterations(self.num_bits, self.target)
        self.grover.apply_grover_iterations(self.target, iterations)
        self.grover.measure_inputs()

        compiled = transpile(self.grover.qc, self.backend)
        result = self.backend.run(compiled, shots=self.shots).result()
        counts = result.get_counts()

        decoded = self.grover.decode_results(counts)
        correct_freq = sum(
            res["freq"] for res in decoded
            if sum(v for k, v in res.items() if k != "freq") == self.target
        )

        self.assertGreater(
            correct_freq / self.shots, 0.50,
            f"Grover failed: only {(correct_freq/self.shots)*100:.2f}% success for target {self.target}"
        )

    def test_integration_grover_search_edge_cases(self):
        # Edge cases: target = 0 and target = max_sum
        max_sum = ((1 << self.num_bits) - 1) * 3

        for edge_target in [0, max_sum]:
            grover_edge = GroverSearch(self.adder)
            iterations = optimal_grover_iterations(self.num_bits, edge_target)
            grover_edge.apply_grover_iterations(edge_target, iterations)
            grover_edge.measure_inputs()

            compiled = transpile(grover_edge.qc, self.backend)
            result = self.backend.run(compiled, shots=self.shots).result()
            counts = result.get_counts()

            decoded = grover_edge.decode_results(counts)
            correct_freq = sum(
                res["freq"] for res in decoded
                if sum(v for k, v in res.items() if k != "freq") == edge_target
            )

            self.assertGreater(
                correct_freq / self.shots, 0.50,
                f"Edge case {edge_target} failed: only {(correct_freq/self.shots)*100:.2f}% success"
            )


if __name__ == "__main__":
    unittest.main()
