from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator


def compile_circuit(
    qc: QuantumCircuit, backend=None, optimization_level=3
) -> QuantumCircuit:
    if backend is None:
        backend = AerSimulator()
    return transpile(qc, backend, optimization_level=optimization_level)
