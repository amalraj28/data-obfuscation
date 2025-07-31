import unittest
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from adder_builder import AdderBuilder
from circuit_initializer import CircuitInitializer


class TestAdderBuilder(unittest.TestCase):

    def setUp(self):
        """Common setup for all tests."""
        self.sim = AerSimulator()

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

    def _measure_and_run(self, qc, measure_qubits, classical_bits):
        """Helper to add measurements and run the simulation."""
        qc.measure(measure_qubits, classical_bits)
        compiled = transpile(qc, self.sim)
        result = self.sim.run(compiled, shots=1024).result()
        counts = result.get_counts()
        measured_bin = max(counts, key=counts.get)
        return int(measured_bin, 2)

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
        measured_sum = self._measure_and_run(qc, result_qubits, range(len(result_qubits)))

        self.assertEqual(
            measured_sum, expected_sum, f"Expected {expected_sum}, got {measured_sum}"
        )


if __name__ == "__main__":
    unittest.main()
