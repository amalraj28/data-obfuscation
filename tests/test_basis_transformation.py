import unittest

from qiskit import QuantumCircuit, qasm3, transpile
from qiskit.circuit import Instruction
from qiskit.circuit.library import UnitaryGate
from qiskit.quantum_info import Operator
from qiskit_aer import AerSimulator

from algorithms.basis_transformation import apply_basis_obfuscation
from utils.helper import circuit_to_qasm


class TestBasisTransformation(unittest.TestCase):
    def assert_equivalent(self, original, obfuscated):
        self.assertTrue(Operator(obfuscated).equiv(Operator(original)))

    def test_obfuscates_single_multi_and_wide_mcx_gates(self):
        circuit = QuantumCircuit(4)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.mcx([0, 1, 2], 3)

        obfuscated = apply_basis_obfuscation(circuit)

        self.assert_equivalent(circuit, obfuscated)
        transformed_mcx = [
            item.operation
            for item in obfuscated.data
            if item.operation.num_qubits == 4
        ]
        self.assertEqual(len(transformed_mcx), 1)
        self.assertIsInstance(transformed_mcx[0], UnitaryGate)
        self.assertEqual(transformed_mcx[0].num_qubits, 4)
        self.assertTrue(all(item.operation.label is None for item in obfuscated.data))

    def test_uses_fresh_secure_random_bases(self):
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        first = apply_basis_obfuscation(circuit)
        second = apply_basis_obfuscation(circuit)

        self.assert_equivalent(circuit, first)
        self.assert_equivalent(circuit, second)
        self.assertNotEqual(qasm3.dumps(first), qasm3.dumps(second))

    def test_preserves_barrier_metadata_and_global_phase(self):
        circuit = QuantumCircuit(2, name="source", metadata={"purpose": "test"})
        circuit.global_phase = 0.37
        circuit.h(0)
        circuit.barrier()
        circuit.cx(0, 1)

        obfuscated = apply_basis_obfuscation(circuit)

        self.assert_equivalent(circuit, obfuscated)
        self.assertEqual(obfuscated.name, circuit.name)
        self.assertEqual(obfuscated.metadata, circuit.metadata)
        self.assertEqual(obfuscated.count_ops().get("barrier"), 1)

    def test_preserves_measurement_reset_and_classical_control(self):
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.reset(0)
        circuit.x(0)
        circuit.measure(0, 0)
        with circuit.if_test((circuit.clbits[0], True)):
            circuit.x(0)
        circuit.measure(0, 0)

        obfuscated = apply_basis_obfuscation(circuit)
        backend = AerSimulator()
        counts = backend.run(
            transpile(obfuscated, backend),
            shots=128,
        ).result().get_counts()

        self.assertEqual(counts, {"0": 128})
        self.assertEqual(obfuscated.count_ops().get("reset"), 1)
        self.assertEqual(obfuscated.count_ops().get("measure"), 2)
        self.assertEqual(obfuscated.count_ops().get("if_else"), 1)

    def test_rejects_unsupported_non_unitary_instruction(self):
        circuit = QuantumCircuit(1)
        circuit.append(Instruction("unsupported", 1, 0, []), [0])

        with self.assertRaisesRegex(
            ValueError,
            "Unsupported non-unitary instruction: unsupported",
        ):
            apply_basis_obfuscation(circuit)

    def test_wide_gate_qasm_round_trip(self):
        circuit = QuantumCircuit(4)
        circuit.mcx([0, 1, 2], 3)
        obfuscated = apply_basis_obfuscation(circuit)

        qasm = circuit_to_qasm(obfuscated)
        restored = qasm3.loads(qasm)

        self.assertGreater(len(qasm), 10_000)
        self.assertTrue(Operator(restored).equiv(Operator(obfuscated)))


if __name__ == "__main__":
    unittest.main()
