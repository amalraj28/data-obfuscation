import unittest
import numpy as np

from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Operator
from qiskit_aer import AerSimulator

from algorithms.basis_transformation import apply_basis_obfuscation
from circuits.adder_builder import AdderBuilder
from circuits.grover_search import GroverSearch
from utils.math_utils import optimal_grover_iterations


class TestGroverSearch(unittest.TestCase):
    def setUp(self):
        self.num_bits = 3
        self.target = 4
        self.adder = AdderBuilder(self.num_bits)
        self.grover = GroverSearch(self.adder)
        self.shots = 1024
        self.backend = AerSimulator()

    def test_build_oracle_uses_canonical_circuit(self):
        grover = GroverSearch(AdderBuilder(1))
        oracle_circuit = grover.build_oracle_circuit(1)
        oracle_gate = grover.build_oracle_gate(1)

        self.assertIsInstance(oracle_gate, type(QuantumCircuit().to_gate()))
        self.assertEqual(oracle_gate.num_qubits, grover.num_qubits)
        self.assertTrue(Operator(oracle_gate).equiv(Operator(oracle_circuit)))

    def test_msb_phase_query_marks_only_target(self):
        for num_bits in (1, 3):
            grover = GroverSearch(AdderBuilder(num_bits))
            self.assertEqual(grover.num_qubits, 3 * num_bits + 4)
            for target in range(3 * ((1 << num_bits) - 1) + 1):
                with self.subTest(num_bits=num_bits, target=target):
                    query = grover._build_query_circuit(target)
                    self.assertEqual(query.num_qubits, num_bits + 2)
                    phases = np.ones(1 << query.num_qubits)
                    phases[target] = -1
                    np.testing.assert_allclose(
                        Operator(query).data, np.diag(phases), atol=1e-12
                    )

    def test_oracle_restores_workspace_and_marks_matching_inputs(self):
        grover = GroverSearch(AdderBuilder(1))
        for target in range(4):
            matrix = Operator(grover.build_oracle_circuit(target)).data
            for value in range(8):
                expected = np.zeros(1 << grover.num_qubits)
                expected[value] = -1 if value.bit_count() == target else 1
                np.testing.assert_allclose(matrix[:, value], expected, atol=1e-12)

    def test_diffuser_uses_input_msb_without_ancilla(self):
        grover = GroverSearch(AdderBuilder(1))
        diffuser = grover.build_diffuser_circuit()
        self.assertEqual(diffuser.num_qubits, len(grover.input_qubits))
        dimension = 1 << diffuser.num_qubits
        expected = np.eye(dimension) - 2 * np.ones((dimension, dimension)) / dimension
        np.testing.assert_allclose(Operator(diffuser).data, expected, atol=1e-12)

    def test_complete_grover_supports_basis_obfuscation(self):
        grover = GroverSearch(AdderBuilder(1))
        grover.apply_grover_iterations(1, 1, expand_components=True)

        obfuscated = apply_basis_obfuscation(grover.qc)

        self.assertTrue(Operator(obfuscated).equiv(Operator(grover.qc)))
        self.assertEqual(obfuscated.num_qubits, grover.qc.num_qubits)

    def test_compact_and_expanded_iterations_are_equivalent(self):
        compact = GroverSearch(AdderBuilder(1))
        compact.apply_grover_iterations(1, 1)
        expanded = GroverSearch(AdderBuilder(1))
        expanded.apply_grover_iterations(1, 1, expand_components=True)

        self.assertIn("Oracle", compact.qc.count_ops())
        self.assertIn("Diffuser", compact.qc.count_ops())
        self.assertNotIn("Oracle", expanded.qc.count_ops())
        self.assertNotIn("Diffuser", expanded.qc.count_ops())
        self.assertTrue(Operator(compact.qc).equiv(Operator(expanded.qc)))

    def test_rejects_invalid_target_and_iteration_count(self):
        max_sum = ((1 << self.num_bits) - 1) * 3

        for target in (-1, max_sum + 1):
            with self.assertRaises(ValueError):
                self.grover.apply_grover_iterations(target, 1)
        with self.assertRaises(TypeError):
            self.grover.apply_grover_iterations(1.5, 1)
        with self.assertRaises(ValueError):
            self.grover.apply_grover_iterations(self.target, -1)

    def test_decode_results(self):
        counts = {"101011001": 10, "001010011": 5}
        decoded = self.grover.decode_results(counts)
        self.assertEqual(decoded[0]["freq"], 10)
        self.assertEqual(decoded[0]["x"], 1)
        self.assertEqual(decoded[0]["y"], 3)
        self.assertEqual(decoded[0]["z"], 5)

    def test_integration_grover_search_mid_target(self):
        iterations = optimal_grover_iterations(self.num_bits, self.target)
        self.grover.apply_grover_iterations(self.target, iterations)
        self.grover.measure_inputs()

        counts = (
            self.backend.run(
                transpile(self.grover.qc, self.backend),
                shots=self.shots,
            )
            .result()
            .get_counts()
        )
        decoded = self.grover.decode_results(counts)
        correct_freq = sum(
            result["freq"]
            for result in decoded
            if result["x"] + result["y"] + result["z"] == self.target
        )

        self.assertGreater(correct_freq / self.shots, 0.50)


if __name__ == "__main__":
    unittest.main()
