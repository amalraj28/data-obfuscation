"""Whole-circuit basis obfuscation.

The transformation represents each unitary instruction between independently
sampled local bases.  Adjacent instructions share their boundary bases, so the
inserted changes of basis cancel while the overall circuit remains equivalent.
"""

import math
import secrets
import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import Qubit, Operation
from qiskit.circuit.library import UGate, UnitaryGate
from qiskit.quantum_info import Operator
from typing import Iterable
from numpy.typing import NDArray

_PRESERVED_DIRECTIVES = {"barrier", "delay"}
_BASIS_BOUNDARIES = {"measure", "reset"}
_RANDOM = secrets.SystemRandom()
BasisParams = tuple[float, float, float]
ComplexMatrix = NDArray[np.complex128]


def _random_u_params():
    """Sample Haar-distributed single-qubit U-gate parameters."""
    theta = math.acos(1 - 2 * _RANDOM.random())
    phi = _RANDOM.uniform(0, 2 * math.pi)
    lam = _RANDOM.uniform(0, 2 * math.pi)
    return theta, phi, lam


def _operator_matrix(operation: Operation) -> ComplexMatrix:
    return np.asarray(
        Operator(operation).data,
        dtype=np.complex128,
    )


def _transform_between_local_bases(
    gate_matrix: ComplexMatrix,
    input_basis_params: list[BasisParams],
    output_basis_params: list[BasisParams],
) -> ComplexMatrix:
    """Compute ``B_out G B_in†`` without constructing product-basis matrices."""
    num_qubits = len(input_basis_params)
    if len(output_basis_params) != num_qubits:
        raise ValueError("Input and output basis widths must match")

    expected_dimension = 1 << num_qubits

    if gate_matrix.shape != (expected_dimension, expected_dimension):
        raise ValueError("Gate matrix size does not match the basis width")

    tensor = np.asarray(gate_matrix, dtype=complex).reshape((2,) * (2 * num_qubits))
    for qubit, (input_params, output_params) in enumerate(
        zip(input_basis_params, output_basis_params)
    ):
        input_basis = _operator_matrix(UGate(*input_params))
        output_basis = _operator_matrix(UGate(*output_params))
        output_axis = num_qubits - 1 - qubit
        input_axis = 2 * num_qubits - 1 - qubit

        tensor = np.tensordot(
            output_basis,
            tensor,
            axes=([1], [output_axis]),
        )
        tensor = np.moveaxis(tensor, 0, output_axis)
        tensor = np.tensordot(
            tensor,
            input_basis.conjugate().T,
            axes=([input_axis], [0]),
        )
        tensor = np.moveaxis(tensor, -1, input_axis)

    return np.asarray(
        tensor.reshape((expected_dimension, expected_dimension)),
        dtype=np.complex128,
    )


def _append_instruction(circuit: QuantumCircuit, instruction):
    circuit.append(
        instruction.operation,
        instruction.qubits,
        instruction.clbits,
    )


def _is_classical_instruction(operation: Operation):
    return operation.num_clbits > 0 or getattr(operation, "condition", None) is not None


def apply_basis_obfuscation(circuit: QuantumCircuit) -> QuantumCircuit:
    """Return a semantically equivalent circuit in evolving local bases.

    Random bases are sampled with the operating system's secure random source.
    Multi-qubit operations, including wide MCX gates, remain single operations
    represented by dense :class:`~qiskit.circuit.library.UnitaryGate` objects.

    Measurements, resets, and classical instructions close the active bases on
    the wires they touch before being copied.  Unsupported non-unitary quantum
    instructions raise ``ValueError``.
    """
    obfuscated = QuantumCircuit(*circuit.qregs, *circuit.cregs, name=circuit.name)
    obfuscated.global_phase = circuit.global_phase
    obfuscated.metadata = circuit.metadata.copy() if circuit.metadata else {}

    current_basis = {}

    def open_basis(qubit: Qubit):
        params = _random_u_params()
        current_basis[qubit] = params
        obfuscated.append(UGate(*params), [qubit])

    def close_bases(qubits: Iterable[Qubit]):
        qubit_set = set(qubits)
        for qubit in circuit.qubits:
            if qubit not in qubit_set:
                continue
            params = current_basis.pop(qubit, None)
            if params is not None:
                obfuscated.append(UGate(*params).inverse(), [qubit])

    for qubit in circuit.qubits:
        open_basis(qubit)

    for instruction in circuit.data:
        operation = instruction.operation

        if operation.name in _BASIS_BOUNDARIES:
            close_bases(instruction.qubits)
            _append_instruction(obfuscated, instruction)
            continue

        if operation.name in _PRESERVED_DIRECTIVES or operation.num_qubits == 0:
            _append_instruction(obfuscated, instruction)
            continue

        if _is_classical_instruction(operation):
            close_bases(instruction.qubits)
            _append_instruction(obfuscated, instruction)
            continue

        try:
            gate_matrix = _operator_matrix(operation=operation)
        except Exception as error:
            raise ValueError(
                f"Unsupported non-unitary instruction: {operation.name}"
            ) from error

        for qubit in instruction.qubits:
            if qubit not in current_basis:
                open_basis(qubit)

        input_basis_params: list[BasisParams] = [
            current_basis[qubit] for qubit in instruction.qubits
        ]

        output_basis_params: list[BasisParams] = [
            _random_u_params() for _ in instruction.qubits
        ]

        transformed_matrix = _transform_between_local_bases(
            gate_matrix,
            input_basis_params,
            output_basis_params,
        )

        phase = 0.0
        transformed_gate = UnitaryGate(transformed_matrix)

        obfuscated.global_phase += phase
        obfuscated.append(transformed_gate, instruction.qubits)
        for qubit, params in zip(instruction.qubits, output_basis_params):
            current_basis[qubit] = params

    close_bases(circuit.qubits)
    return obfuscated
