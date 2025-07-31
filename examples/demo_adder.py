from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from circuits.adder_builder import AdderBuilder
from circuits.circuit_initializer import CircuitInitializer

# 1. Set number of bits and input values
num_bits = 5
x_val, y_val, z_val = 8, 3, 2  # Example values
values = {"x": x_val, "y": y_val, "z": z_val}
expected_sum = sum(values.values())

# 2. Create the adder and get the gate
adder = AdderBuilder(num_bits)
adder_gate = adder.build_triple_adder_gate()

# 3. Get mapping and result qubits
mapping = adder.get_mapping()
result_qubits = adder.get_result_qubits()

# 4. Build the QuantumCircuit with enough qubits and classical bits
qc = QuantumCircuit(adder_gate.num_qubits, len(result_qubits))

# 5. Initialize x, y, z using CircuitInitializer
CircuitInitializer.initialize(qc, values, mapping)

# 6. Append the triple-adder gate
qc.append(adder_gate, range(adder_gate.num_qubits))

# 7. Measure result qubits
qc.measure(result_qubits, range(len(result_qubits)))

# 8. Run simulation
backend = AerSimulator()
compiled = transpile(qc, backend)
result = backend.run(compiled, shots=1024).result()
counts = result.get_counts()
measured_bin = max(counts, key=counts.get)
measured_sum = int(measured_bin, 2)

# 9. Display results
print(f"Inputs: x={x_val}, y={y_val}, z={z_val}")
print(f"Expected Sum: {expected_sum}")
print(f"Measured Sum: {measured_sum}")
print(f"Counts: {counts}")
# print(qc.draw())
