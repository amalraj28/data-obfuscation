from qiskit.circuit.library import CDKMRippleCarryAdder
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
import matplotlib.pyplot as plt
from qiskit.visualization import plot_histogram

# Add two n-bit numbers
num_bits = 4

adder = CDKMRippleCarryAdder(num_bits, 'half', 'adder')

qc = QuantumCircuit(adder.num_qubits, 0)

# add 7 and 8 --> 0111 and 1000
# First 4 bits are for first number (7), next 4 bits for second number(8)
# qc.x(list(range(8)))

qc.x(range(8))
qc.compose(adder.decompose(), inplace=True)

# qc.draw('mpl')
# plt.show()

qc.measure_all()
simulator = AerSimulator()
compiled_circuit = transpile(qc, simulator)
result = simulator.run(compiled_circuit).result()
counts = result.get_counts()
print(counts)


