# Encoding in subset sum problem

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from qiskit_aer import AerSimulator
from qiskit.visualization import plot_histogram
import matplotlib.pyplot as plt
from typing import List


def find_valid_bitmasks(S: List[int], target: int) -> List[str]:
    valid = []
    k = len(S)
    for i in range(2**k):
        bits = format(i, f"0{k}b")
        subset_sum = sum(S[j] for j in range(k) if bits[j] == "1")
        if subset_sum == target:
            valid.append(bits)
    return valid


def apply_subset_oracle(qc: QuantumCircuit, q_subset, anc, valid_bitmasks: List[str]):
    """Apply phase flip to ancilla if subset represented by q_subset sums to target."""
    k = len(q_subset)
    for bitmask in valid_bitmasks:
        # Flip qubits to match control state
        for i, b in enumerate(bitmask):
            if b == '0':
                qc.x(q_subset[i])
        
        # Apply multi-controlled X gate (Z via ancilla phase kickback)
        qc.mcx(q_subset, anc[0])
        
        # Undo flips
        for i, b in enumerate(bitmask):
            if b == '0':
                qc.x(q_subset[i])


def apply_diffusion(qc: QuantumCircuit, q_subset: QuantumRegister):
    """Grover diffusion operator (inversion about mean)"""
    k = len(q_subset)
    qc.h(q_subset)
    qc.x(q_subset)
    qc.h(q_subset[-1])
    qc.mcx(q_subset[:-1], q_subset[-1])
    qc.h(q_subset[-1])
    qc.x(q_subset)
    qc.h(q_subset)


# Parameters
S = list(range(10))
target = 12
k = len(S)

# Step 1: Find valid subsets
valid_bitmasks = find_valid_bitmasks(S, target)
print("Valid subsets:", valid_bitmasks)

# Step 2: Setup quantum circuit
q_subset = QuantumRegister(k, "q")
anc = QuantumRegister(1, "anc")
cr = ClassicalRegister(k, "c")
qc = QuantumCircuit(q_subset, anc, cr)

# Step 3: Initialize superposition
qc.h(q_subset)

# Prepare ancilla in |-⟩ for phase kickback
qc.x(anc[0])
qc.h(anc[0])

# Step 4: Apply Grover iterations
num_iterations = 1  # Can be adjusted
for _ in range(num_iterations):
    apply_subset_oracle(qc, q_subset, anc, valid_bitmasks)
    apply_diffusion(qc, q_subset)

# Step 5: Measure
qc.measure(q_subset, cr)

# Step 6: Simulate
simulator = AerSimulator()
compiled = transpile(qc, simulator)
result = simulator.run(compiled, shots=1024).result()
counts = result.get_counts()

# Plot
plot_histogram(counts)
plt.title("Subset Sum Obfuscation Output")
plt.show()

# Decode one result
top_result = max(counts, key=counts.get)
subset = [S[i] for i in range(k) if top_result[::-1][i] == "1"]
print(f"Top bitstring: {top_result}")
print(f"Subset selected: {subset}, Sum = {sum(subset)} (Target = {target})")
