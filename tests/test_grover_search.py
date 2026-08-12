import unittest

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

    def test_query_uses_plain_explicit_x_mask(self):
        num_sum_qubits = self.num_bits + 2
        zero_bits = format(self.target, f"0{num_sum_qubits}b").count("0")
        query = self.grover._build_query_circuit(self.target)

        self.assertEqual(query.count_ops().get("x"), 2 * zero_bits)
        self.assertEqual(query.count_ops().get("mcx"), 1)

    def test_phase_ancilla_is_initialized_once(self):
        self.grover.apply_grover_iterations(
            self.target,
            2,
            expand_components=True,
        )
        operations = self.grover.qc.count_ops()

        self.assertEqual(operations.get("h"), len(self.grover.input_qubits) * 5 + 1)
        self.assertEqual(operations.get("z"), 1)
        query = self.grover._build_query_circuit(self.target)
        self.assertNotIn("h", query.count_ops())
        self.assertNotIn("z", query.count_ops())

    def test_complete_grover_supports_basis_obfuscation(self):
        grover = GroverSearch(AdderBuilder(1))
        grover.apply_grover_iterations(1, 1, expand_components=True)

        obfuscated = apply_basis_obfuscation(grover.qc)

        self.assertTrue(Operator(obfuscated).equiv(Operator(grover.qc)))
        self.assertEqual(
            len(obfuscated.data),
            len(grover.qc.data) + 2 * grover.qc.num_qubits,
        )

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

        counts = self.backend.run(
            transpile(self.grover.qc, self.backend),
            shots=self.shots,
        ).result().get_counts()
        decoded = self.grover.decode_results(counts)
        correct_freq = sum(
            result["freq"]
            for result in decoded
            if result["x"] + result["y"] + result["z"] == self.target
        )

        self.assertGreater(correct_freq / self.shots, 0.50)


if __name__ == "__main__":
    unittest.main()
