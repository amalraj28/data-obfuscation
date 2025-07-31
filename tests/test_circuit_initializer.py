# tests/test_circuit_initializer.py
import unittest
from qiskit import QuantumCircuit
from circuits.circuit_initializer import CircuitInitializer


class TestCircuitInitializer(unittest.TestCase):

    def test_valid_initialization(self):
        qc = QuantumCircuit(6)
        values = {"x": 3, "y": 2}  # x=011, y=010
        mapping = {"x": [0, 1, 2], "y": [3, 4, 5]}
        CircuitInitializer.initialize(qc, values, mapping)

        # Collect indices of qubits that have X gates applied
        applied_gates = [
            qc.find_bit(qarg[0]).index
            for op, qarg, _ in qc.data
            if op.name == "x"
        ]
        self.assertEqual(sorted(applied_gates), [0, 1, 4])  # 0,1 for x; 4 for y

    def test_negative_value_raises_error(self):
        values = {"x": -1}
        mapping = {"x": [0, 1, 2]}
        with self.assertRaises(ValueError):
            CircuitInitializer.validate_inputs(values, mapping)

    def test_value_out_of_range_raises_error(self):
        values = {"x": 8}  # Needs 4 bits, only 3 provided
        mapping = {"x": [0, 1, 2]}
        with self.assertRaises(ValueError):
            CircuitInitializer.validate_inputs(values, mapping)

    def test_missing_mapping_raises_error(self):
        values = {"x": 3}
        mapping = {}
        with self.assertRaises(ValueError):
            CircuitInitializer.validate_inputs(values, mapping)


if __name__ == "__main__":
    unittest.main()
