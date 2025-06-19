from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, AncillaRegister
from qiskit_aer import AerSimulator
from typing import List, Tuple
from helper import compile_circuit


def solution_set(n: int, x: int, y: int, z: int) -> List[Tuple[int, int, int]]:
    solutions = []
    for i in range(16):
        for j in range(16):
            for k in range(16):
                if a * i + b * j + c * k == n:
                    solutions.append((i, j, k))
    return solutions


def apply_oracle(
    qc: QuantumCircuit, qr_x, qr_y, qr_z, anc, solutions: List[Tuple[int, int, int]]
):
    num_bits = len(qr_x)
    for x, y, z in solutions:
        bin_x = format(x, f"0{num_bits}b")
        bin_y = format(y, f"0{num_bits}b")
        bin_z = format(z, f"0{num_bits}b")

        # Apply X gates to match |x⟩|y⟩|z⟩
        for i, b in enumerate(bin_x):
            if b == "0":
                qc.x(qr_x[i])
        for i, b in enumerate(bin_y):
            if b == "0":
                qc.x(qr_y[i])
        for i, b in enumerate(bin_z):
            if b == "0":
                qc.x(qr_z[i])

        # Apply multi-controlled X on ancilla
        controls = list(qr_x) + list(qr_y) + list(qr_z)
        qc.mcx(controls, anc[0])  # MCX available in Qiskit natively

        # Uncompute X gates
        for i, b in enumerate(bin_x):
            if b == "0":
                qc.x(qr_x[i])
        for i, b in enumerate(bin_y):
            if b == "0":
                qc.x(qr_y[i])
        for i, b in enumerate(bin_z):
            if b == "0":
                qc.x(qr_z[i])


def apply_diffusion(qc: QuantumCircuit, qr_x, qr_y, qr_z):
    all_qubits = list(qr_x) + list(qr_y) + list(qr_z)

    # Step 1: Hadamard
    for q in all_qubits:
        qc.h(q)

    # Step 2: X
    for q in all_qubits:
        qc.x(q)

    # Step 3: Multi-controlled Z (MCX with H sandwich)
    qc.h(qr_z[-1])  # Target qubit
    qc.mcx(all_qubits[:-1], qr_z[-1])
    qc.h(qr_z[-1])

    # Step 4: X
    for q in all_qubits:
        qc.x(q)

    # Step 5: Hadamard
    for q in all_qubits:
        qc.h(q)


a = 1
b = 2
c = 3
n = 90

solutions = solution_set(n, a, b, c)

# Number of bits to represent each of x, y, z
num_bits = 4

# Quantum registers for x, y, z (each 4 qubits)
qr_x = QuantumRegister(num_bits, name="x")
qr_y = QuantumRegister(num_bits, name="y")
qr_z = QuantumRegister(num_bits, name="z")

# Ancilla qubit for phase kickback
anc = AncillaRegister(1, name="anc")

# Classical register to measure x, y, z (12 bits)
cr = ClassicalRegister(3 * num_bits, name="c")

# Create quantum circuit
qc = QuantumCircuit(qr_x, qr_y, qr_z, anc, cr)

for i in range(num_bits):
    qc.h(qr_x[i])
    qc.h(qr_y[i])
    qc.h(qr_z[i])

# Prepare ancilla in \ket{-} state
qc.x(anc[0])
qc.h(anc[0])

apply_oracle(qc, qr_x, qr_y, qr_z, anc, solutions)
apply_diffusion(qc, qr_x, qr_y, qr_z)

# Reapply Grover operator multiple times
num_iterations = 6  # You can try tuning this

for _ in range(num_iterations):
    apply_oracle(qc, qr_x, qr_y, qr_z, anc, solutions)
    apply_diffusion(qc, qr_x, qr_y, qr_z)

# Measure each qubit into classical register
for i in range(num_bits):
    qc.measure(qr_x[i], cr[i])
    qc.measure(qr_y[i], cr[num_bits + i])
    qc.measure(qr_z[i], cr[2 * num_bits + i])

simulator = AerSimulator()
compiled_qc = compile_circuit(qc, backend=simulator, optimization_level=3)
result = simulator.run(compiled_qc, shots=1024).result()
counts = result.get_counts()
print(len(counts), "results found")
print(len(solutions), "solutions expected")

# import matplotlib.pyplot as plt
# from qiskit.visualization import plot_histogram
# plot_histogram(counts)
# plt.show()

# Get the most frequent result
top_result = max(counts, key=counts.get)
bitstring = top_result[::-1]  # Reverse because Qiskit returns little-endian

print(f"Most frequent bitstring: {top_result}")
# Extract x, y, z binary strings
x_bin = bitstring[0:num_bits]
y_bin = bitstring[num_bits : 2 * num_bits]
z_bin = bitstring[2 * num_bits : 3 * num_bits]

# Convert to integers
x_val = int(x_bin, 2)
y_val = int(y_bin, 2)
z_val = int(z_bin, 2)

print(f"\nMost likely solution:")
print(f"x = {x_val}, y = {y_val}, z = {z_val}")
print(f"Check: {a}*{x_val} + {b}*{y_val} + {c}*{z_val} = {a*x_val + b*y_val + c*z_val}")
print(f"Target n = {n}")
