from typing import Literal

from qiskit import QuantumCircuit, qasm2, qasm3, transpile
from qiskit_aer import AerSimulator


def compile_circuit(
    qc: QuantumCircuit, backend=None, optimization_level=3
) -> QuantumCircuit:
    if backend is None:
        backend = AerSimulator()
    return transpile(qc, backend, optimization_level=optimization_level)


def circuit_to_qasm(
    circuit: QuantumCircuit,
    version: Literal[2, 3] = 3,
) -> str:
    """Serialize a decomposed or undecomposed circuit as OpenQASM text."""
    if version == 2:
        return qasm2.dumps(circuit)
    if version == 3:
        return qasm3.dumps(circuit)
    raise ValueError("QASM version must be 2 or 3")
