import unittest

from qiskit import QuantumCircuit, qasm3, transpile
from qiskit.circuit import Instruction
from qiskit.circuit.library import UnitaryGate
from qiskit.quantum_info import Operator, random_unitary
from qiskit_aer import AerSimulator

from algorithms.basis_transformation import apply_basis_obfuscation, _pad_idle_wires
from utils.helper import circuit_to_qasm


class TestBasisTransformation(unittest.TestCase):
    def assert_equivalent(self, original, obfuscated):
        self.assertTrue(Operator(obfuscated).equiv(Operator(original)))

    def test_padding_fills_idle_wires_and_absorbs_inverse(self):
        circuit = QuantumCircuit(4)
        circuit.global_phase = 0.31
        for index, wires in enumerate(([1, 0], [2, 1], [3, 2])):
            circuit.unitary(random_unitary(4, seed=index), wires)

        padded = _pad_idle_wires(circuit)

        self.assert_equivalent(circuit, padded)
        multi = [item for item in padded.data if len(item.qubits) > 1]
        self.assertEqual([item.qubits for item in multi],
                         [item.qubits for item in circuit.data])
        self.assertGreater(len(padded.data), len(circuit.data))
        self.assertFalse(Operator(multi[1].operation).equiv(
            Operator(circuit.data[1].operation)))
        self.assertTrue(all(isinstance(item.operation, UnitaryGate)
                            and item.operation.label is None for item in padded.data))
        for qubit in circuit.qubits:
            self.assertTrue(any(item.qubits == (qubit,) for item in padded.data))

    def test_padding_closes_before_barriers_and_single_qubit_gates(self):
        circuit = QuantumCircuit(3)
        circuit.unitary(random_unitary(4, seed=1), [0, 1])
        circuit.barrier()
        circuit.x(2)
        circuit.unitary(random_unitary(4, seed=2), [1, 2])
        padded = _pad_idle_wires(circuit)
        self.assert_equivalent(circuit, padded)
        barrier = next(i for i, item in enumerate(padded.data)
                       if item.operation.name == "barrier")
        prefix = QuantumCircuit(3)
        for item in padded.data[:barrier]:
            prefix.append(item.operation, item.qubits)
        expected = QuantumCircuit(3)
        expected.append(circuit.data[0].operation, [0, 1])
        self.assert_equivalent(expected, prefix)

    def test_padding_preserves_measurement_reset_and_control(self):
        circuit = QuantumCircuit(3, 1)
        circuit.unitary(random_unitary(4, seed=7), [0, 1])
        circuit.measure(2, 0)
        circuit.reset(0)
        with circuit.if_test((circuit.clbits[0], True)):
            circuit.x(1)
        circuit.measure(0, 0)
        padded = _pad_idle_wires(circuit)
        backend = AerSimulator()
        counts = backend.run(transpile(padded, backend), shots=64).result().get_counts()
        self.assertEqual(counts, {"0": 64})
        self.assertEqual(padded.count_ops().get("if_else"), 1)

    def test_padding_can_be_disabled_and_changes_between_calls(self):
        circuit = QuantumCircuit(3)
        circuit.cx(0, 1)
        circuit.cx(1, 2)
        circuit.cx(0, 1)
        circuit.cx(1, 2)
        plain = apply_basis_obfuscation(circuit, pad_idle_wires=False)
        first = apply_basis_obfuscation(circuit)
        second = apply_basis_obfuscation(circuit)
        self.assertGreater(len(first.data), len(plain.data))
        self.assertNotEqual(qasm3.dumps(first), qasm3.dumps(second))
        self.assert_equivalent(circuit, first)
        self.assert_equivalent(circuit, second)

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
