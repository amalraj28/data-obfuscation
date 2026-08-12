import unittest

from qiskit import QuantumCircuit, qasm2, qasm3
from qiskit.quantum_info import Operator

from utils.helper import circuit_to_qasm


class TestCircuitToQasm(unittest.TestCase):
    def setUp(self):
        inner = QuantumCircuit(2, name="Inner")
        inner.h(0)
        inner.cx(0, 1)

        self.circuit = QuantumCircuit(2)
        self.circuit.append(inner.to_gate(label="Custom"), [0, 1])
        self.decomposed_circuit = self.circuit.decompose(
            gates_to_decompose=["Custom"]
        )

    def test_exports_decomposed_and_undecomposed_circuits(self):
        for circuit in (self.circuit, self.decomposed_circuit):
            qasm_2 = circuit_to_qasm(circuit, version=2)
            qasm_3 = circuit_to_qasm(circuit, version=3)

            self.assertTrue(Operator(qasm2.loads(qasm_2)).equiv(Operator(circuit)))
            self.assertTrue(Operator(qasm3.loads(qasm_3)).equiv(Operator(circuit)))

    def test_rejects_unsupported_qasm_version(self):
        with self.assertRaises(ValueError):
            circuit_to_qasm(self.circuit, version=1)

if __name__ == "__main__":
    unittest.main()
