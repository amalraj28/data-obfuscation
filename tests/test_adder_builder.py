import unittest
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from adder_builder import AdderBuilder
from circuit_initializer import CircuitInitializer


class TestAdderBuilder(unittest.TestCase):
    def setUp(self):
        """Common setup for all tests."""
        self.sim = AerSimulator()

    def _measure_and_run(self, qc, measure_qubits, classical_bits, shots=256):
        """Helper to add measurements and run the simulation."""
        qc.measure(measure_qubits, classical_bits)
        compiled = transpile(qc, self.sim)
        result = self.sim.run(compiled, shots=shots).result()
        counts = result.get_counts()
        measured_bin = max(counts, key=counts.get)
        return int(measured_bin, 2)

    def test_qubit_count(self):
        adder_builder = AdderBuilder(4)
        gate = adder_builder.build_triple_adder_gate()
        expected_qubits = 3 * 4 + 4  # 3*n + 4 ancillas
        self.assertEqual(gate.num_qubits, expected_qubits)

    def test_inverse_gate_exists(self):
        adder_builder = AdderBuilder(4)
        gate = adder_builder.build_triple_adder_gate()
        inverse_gate = gate.inverse()
        self.assertEqual(inverse_gate.num_qubits, gate.num_qubits)

    def test_mapping_structure(self):
        num_bits = 3
        adder_builder = AdderBuilder(num_bits)
        mapping = adder_builder.get_mapping()
        self.assertEqual(len(mapping["x"]), num_bits)
        self.assertEqual(len(mapping["y"]), num_bits)
        self.assertEqual(len(mapping["z"]), num_bits)

    def test_adder_functionality(self):
        num_bits = 3
        adder_builder = AdderBuilder(num_bits)
        adder_gate = adder_builder.build_triple_adder_gate()
        mapping = adder_builder.get_mapping()
        result_qubits = adder_builder.get_result_qubits()
        total_qubits = adder_gate.num_qubits

        # Values to add
        x_val, y_val, z_val = 2, 5, 3
        expected_sum = x_val + y_val + z_val
        values = {"x": x_val, "y": y_val, "z": z_val}

        # Build quantum circuit
        qc = QuantumCircuit(total_qubits, len(result_qubits))

        # Use CircuitInitializer
        CircuitInitializer.initialize(qc, values, mapping)

        # Apply TripleAdder gate
        qc.append(adder_gate, range(total_qubits))

        # Measure and run
        measured_sum = self._measure_and_run(
            qc, result_qubits, range(len(result_qubits))
        )
        self.assertEqual(
            measured_sum, expected_sum, f"Expected {expected_sum}, got {measured_sum}"
        )

    def test_adder_functionality_edge_cases(self):
        num_bits = 3
        adder_builder = AdderBuilder(num_bits)
        adder_gate = adder_builder.build_triple_adder_gate()
        mapping = adder_builder.get_mapping()
        result_qubits = adder_builder.get_result_qubits()
        total_qubits = adder_gate.num_qubits

        edge_cases = [
            {"x": 0, "y": 0, "z": 0},  # Min values
            {
                "x": (1 << num_bits) - 1,
                "y": (1 << num_bits) - 1,
                "z": (1 << num_bits) - 1,
            },  # Max values
            {"x": 0, "y": 3, "z": 7},  # Mixed values
        ]

        for values in edge_cases:
            expected_sum = sum(values.values())
            qc = QuantumCircuit(total_qubits, len(result_qubits))
            CircuitInitializer.initialize(qc, values, mapping)
            qc.append(adder_gate, range(total_qubits))

            measured_sum = self._measure_and_run(
                qc, result_qubits, range(len(result_qubits))
            )
            self.assertEqual(measured_sum, expected_sum, f"Edge case failed: {values}")

    def test_invalid_values_raise_error(self):
        num_bits = 3
        mapping = {"x": [0, 1, 2], "y": [3, 4, 5], "z": [6, 7, 8]}

        invalid_cases = [
            {"x": -1, "y": 2, "z": 3},  # Negative value
            {"x": 8, "y": 0, "z": 0},  # x exceeds max for 3 bits
        ]

        for values in invalid_cases:
            with self.assertRaises(ValueError):
                CircuitInitializer.validate_inputs(values, mapping)


if __name__ == "__main__":
    unittest.main()
