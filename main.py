# x,y,z with custom bits

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, AncillaRegister
from qiskit_aer import AerSimulator
from typing import List, Tuple
from helper import compile_circuit
import matplotlib.pyplot as plt
from qiskit.visualization import plot_histogram
import math


def solution_set(
    n: int, a: int, b: int, c: int, bits_x: int, bits_y: int, bits_z: int
) -> List[Tuple[int, int, int]]:
    solutions = []
    for x in range(2**bits_x):
        for y in range(2**bits_y):
            for z in range(2**bits_z):
                if a * x + b * y + c * z == n:
                    solutions.append((x, y, z))
    return solutions


def apply_oracle(
    qc: QuantumCircuit, qr_x, qr_y, qr_z, anc, solutions: List[Tuple[int, int, int]]
):
    bits_x, bits_y, bits_z = len(qr_x), len(qr_y), len(qr_z)
    for x, y, z in solutions:
        bin_x = format(x, f"0{bits_x}b")
        bin_y = format(y, f"0{bits_y}b")
        bin_z = format(z, f"0{bits_z}b")

        # Apply X gates to flip bits that are 0 (prepare matching state)
        for i, b in enumerate(bin_x):
            if b == "0":
                qc.x(qr_x[i])
        for i, b in enumerate(bin_y):
            if b == "0":
                qc.x(qr_y[i])
        for i, b in enumerate(bin_z):
            if b == "0":
                qc.x(qr_z[i])

        # Combine all control qubits
        controls = list(qr_x) + list(qr_y) + list(qr_z)
        qc.mcx(controls, anc[0])  # Flip ancilla phase if match

        # Uncompute to reset
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
    target = all_qubits[-1]  # Safely choose last actual qubit as target

    # Step 1: Hadamard
    for q in all_qubits:
        qc.h(q)

    # Step 2: X
    for q in all_qubits:
        qc.x(q)

    # Step 3: Multi-controlled Z (using MCX with H sandwich)
    qc.h(target)
    qc.mcx(all_qubits[:-1], target)
    qc.h(target)

    # Step 4: X
    for q in all_qubits:
        qc.x(q)

    # Step 5: Hadamard
    for q in all_qubits:
        qc.h(q)


# Step 1: Define coefficients and target value
# a, b, c are coefficients for x, y, z respectively (ax + by + cz = n)
# n is the target value

a = 2
b = 3
c = 4
n = 1000

# Ensure that a, b, c are non-negative integers
assert a > 0 and b > 0 and c > 0 and n > 0, "a, b, c and n must be positive integers."
assert n % math.gcd(a, b, c) == 0, "No solutions exist for the given coefficients and target value."

# Step 2: Define the number of bits for x, y, z
num_bits_x = 3
num_bits_y = 2
num_bits_z = 2
total_bits = num_bits_x + num_bits_y + num_bits_z

# Step 3: Derive solution set
# This will find all (x, y, z) such that ax + by + cz = n
solutions = solution_set(n, a, b, c, num_bits_x, num_bits_y, num_bits_z)
print(solutions)

assert len(solutions) != 0, "No solutions found for the given coefficients and target value."

# Step 4: Create all necessary quantum registers
qr_x = QuantumRegister(num_bits_x, name="x")
qr_y = QuantumRegister(num_bits_y, name="y")
qr_z = QuantumRegister(num_bits_z, name="z")

# Ancilla qubit for phase kickback
anc = AncillaRegister(1, name="anc")

# Classical register to measure x, y, z (12 bits)
cr = ClassicalRegister(total_bits, name="c")

# Step 5: Initialize quantum circuit
qc = QuantumCircuit(qr_x, qr_y, qr_z, anc, cr)

for i in range(num_bits_x):
    qc.h(qr_x[i])

for i in range(num_bits_y):
    qc.h(qr_y[i])

for i in range(num_bits_z):
    qc.h(qr_z[i])

# Prepare ancilla in \ket{-} state
qc.x(anc[0])
qc.h(anc[0])

# Step 6: Apply Grover's operator: Oracle + Diffusion
num_iterations = 6  # You can try tuning this

for _ in range(num_iterations):
    apply_oracle(qc, qr_x, qr_y, qr_z, anc, solutions)
    apply_diffusion(qc, qr_x, qr_y, qr_z)

# Step 7: Measure each qubit into classical register
for i in range(num_bits_x):
    qc.measure(qr_x[i], cr[i])
for i in range(num_bits_y):
    qc.measure(qr_y[i], cr[num_bits_x + i])
for i in range(num_bits_z):
    qc.measure(qr_z[i], cr[num_bits_x + num_bits_y + i])

qc.draw("mpl")  # Optional: visualize the final circuit
plt.show()

# Step 8: Compile and run the circuit
simulator = AerSimulator()
compiled_qc = compile_circuit(qc, backend=simulator, optimization_level=3)
result = simulator.run(compiled_qc, shots=1024).result()
counts = result.get_counts()
print(len(counts), "results found")
print(len(solutions), "solutions expected")

# Step 9: Plot the results (optional)
plot_histogram(counts)
plt.show()

# Get the most frequent result
top_result = max(counts, key=counts.get)
bitstring = top_result[::-1]  # Reverse because Qiskit returns little-endian

print(f"Most frequent bitstring: {top_result}")
# Extract x, y, z binary strings
x_bin = bitstring[0:num_bits_x]
y_bin = bitstring[num_bits_x : num_bits_x + num_bits_y]
z_bin = bitstring[num_bits_x + num_bits_y : total_bits]

# Convert to integers
x_val = int(x_bin, 2)
y_val = int(y_bin, 2)
z_val = int(z_bin, 2)

print(f"\nMost likely solution:")
print(f"x = {x_val}, y = {y_val}, z = {z_val}")
assert a * x_val + b * y_val + c * z_val == n, "Solution does not satisfy the equation!"
print(f"{a}*{x_val} + {b}*{y_val} + {c}*{z_val} = {a*x_val + b*y_val + c*z_val}")
