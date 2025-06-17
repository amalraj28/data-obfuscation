from imports import *

def compile_circuit(qc: QuantumCircuit) -> QuantumCircuit:
    sim = AerSimulator()
    transpiled = transpile(qc, sim)
    return transpiled