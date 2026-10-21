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
from qiskit.converters import circuit_to_dag
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


def _fuse_neighboring_single_qubit_gates(circuit: QuantumCircuit) -> QuantumCircuit:
    """Absorb only the immediately adjacent single-qubit gate on each wire.

    Adjacency is determined before fusion, so removing a gate never makes a
    second gate eligible. A gate adjacent to two multi-qubit gates chooses one
    direction at random. Only disjoint-wire instructions may be crossed.
    """
    before = {}
    after = {}
    removed = set()

    def assign(run, left, right, qubit):
        if not run or (left is None and right is None):
            return
        assignments = []
        if len(run) == 1 and left is not None and right is not None:
            if _RANDOM.randrange(2) == 0:
                assignments.append((run[0], left, after))
            else:
                assignments.append((run[0], right, before))
        else:
            if left is not None:
                assignments.append((run[0], left, after))
            if right is not None:
                assignments.append((run[-1], right, before))
        for index, anchor, destination in assignments:
            destination.setdefault(anchor, {})[qubit] = _operator_matrix(
                circuit.data[index].operation
            )
            removed.add(index)

    for qubit in circuit.qubits:
        left = None
        run = []
        for index, instruction in enumerate(circuit.data):
            if qubit not in instruction.qubits:
                continue
            operation = instruction.operation
            # This pass runs after obfuscation, so only generated unitaries
            # and basis changes are eligible; directives are hard boundaries.
            unitary = isinstance(
                operation, (UnitaryGate, UGate)
            ) and not _is_classical_instruction(operation)
            if unitary and operation.num_qubits == 1:
                run.append(index)
                continue
            right = index if unitary and operation.num_qubits > 1 else None
            assign(run, left, right, qubit)
            run = []
            left = right
        assign(run, left, None, qubit)

    fused = circuit.copy_empty_like()
    for index, instruction in enumerate(circuit.data):
        if index in removed:
            continue
        if index not in before and index not in after:
            _append_instruction(fused, instruction)
            continue
        width = len(instruction.qubits)
        tensor = _operator_matrix(instruction.operation).reshape((2,) * (2 * width))
        for qubit_index, qubit in enumerate(instruction.qubits):
            if qubit in after.get(index, {}):
                axis = width - 1 - qubit_index
                tensor = np.tensordot(after[index][qubit], tensor, axes=([1], [axis]))
                tensor = np.moveaxis(tensor, 0, axis)
            if qubit in before.get(index, {}):
                axis = 2 * width - 1 - qubit_index
                tensor = np.tensordot(tensor, before[index][qubit], axes=([axis], [0]))
                tensor = np.moveaxis(tensor, -1, axis)
        fused.append(
            UnitaryGate(tensor.reshape((1 << width, 1 << width))), instruction.qubits
        )
    return fused


def _pad_idle_wires(circuit: QuantumCircuit) -> QuantumCircuit:
    padded = circuit.copy_empty_like()
    pending = {}

    def close(qubit):
        matrix = pending.pop(qubit, None)
        if matrix is not None:
            padded.append(UnitaryGate(matrix.conjugate().T), [qubit])

    for layer in circuit_to_dag(circuit).layers():
        nodes = list(layer["graph"].op_nodes())
        busy = {qubit for node in nodes for qubit in node.qargs}
        has_multi = any(
            isinstance(node.op, UnitaryGate) and node.op.num_qubits > 1
            and not _is_classical_instruction(node.op)
            for node in nodes
        )
        for node in nodes:
            operation = node.op
            can_absorb = (
                isinstance(operation, UnitaryGate)
                and operation.num_qubits > 1
                and not _is_classical_instruction(operation)
            )
            if can_absorb and any(qubit in pending for qubit in node.qargs):
                width = len(node.qargs)
                tensor = _operator_matrix(operation).reshape((2,) * (2 * width))
                for index, qubit in enumerate(node.qargs):
                    matrix = pending.pop(qubit, None)
                    if matrix is None:
                        continue
                    axis = 2 * width - 1 - index
                    tensor = np.tensordot(
                        tensor, matrix.conjugate().T, axes=([axis], [0])
                    )
                    tensor = np.moveaxis(tensor, -1, axis)
                operation = UnitaryGate(tensor.reshape((1 << width, 1 << width)))
            else:
                for qubit in node.qargs:
                    close(qubit)
            padded.append(operation, node.qargs, node.cargs)

        if has_multi:
            for qubit in circuit.qubits:
                if qubit in busy:
                    continue
                matrix = _operator_matrix(UGate(*_random_u_params()))
                padded.append(UnitaryGate(matrix), [qubit])
                pending[qubit] = matrix @ pending.get(qubit, np.eye(2))

    for qubit in circuit.qubits:
        close(qubit)
    return padded


def apply_basis_obfuscation(
    circuit: QuantumCircuit, *, fuse_single_qubit_gates: bool = False,
    pad_idle_wires: bool = False,
) -> QuantumCircuit:
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

        transformed_gate = UnitaryGate(transformed_matrix)

        obfuscated.append(transformed_gate, instruction.qubits)
        for qubit, params in zip(instruction.qubits, output_basis_params):
            current_basis[qubit] = params

    close_bases(circuit.qubits)
    obfuscated = (
        _fuse_neighboring_single_qubit_gates(obfuscated)
        if fuse_single_qubit_gates else obfuscated
    )
    if pad_idle_wires:
        obfuscated = _pad_idle_wires(obfuscated)

    return obfuscated
