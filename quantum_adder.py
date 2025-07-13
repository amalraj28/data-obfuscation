from qiskit.circuit.library import CDKMRippleCarryAdder
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
import matplotlib.pyplot as plt
from qiskit.visualization import plot_histogram

# Add two n-bit numbers
num_bits = 4

adder = CDKMRippleCarryAdder(num_bits, "half", "adder")

qc = QuantumCircuit(adder.num_qubits, num_bits + 1)

# add 7 and 8 --> 0111 and 1000
# First 4 bits are for first number (7), next 4 bits for second number(8)
# qc.x(list(range(8)))

qc.x(range(8))
qc.compose(adder.decompose(), inplace=True)

# qc.draw('mpl')
# plt.show()

qc.measure(range(num_bits, 2 * num_bits + 1), range(num_bits + 1))
simulator = AerSimulator()
compiled_circuit = transpile(qc, simulator)
result = simulator.run(compiled_circuit).result()
counts = result.get_counts()
print(int(list(counts.keys())[0], 2))


class CuccaroAdder:
    def __init__(self, num_bits: int, kind: str = "half", name: str = "adder"):
        self.num_bits = num_bits
        self.adder = CDKMRippleCarryAdder(num_bits, kind, name)
    
    def __convert_to_binary(self, number: int) -> str:
        # Convert an integer to a binary string of fixed length
        return format(number, f'0{self.num_bits}b')

    def generate(self, a: int, b: int) -> QuantumCircuit:
        assert a < 2**self.num_bits and b < 2 ** self.num_bits, "Input numbers exceed bit limit"
        
        qc = QuantumCircuit(self.adder.num_qubits, self.num_bits + 1)
        
        a_bin = self.__convert_to_binary(a)
        b_bin = self.__convert_to_binary(b)
        qc.initialize(a_bin, range(self.num_bits))
        qc.initialize(b_bin, range(self.num_bits, 2 * self.num_bits))
        qc.compose(self.adder, inplace=True)
        self.__set_qc(qc)
        return qc
    
    def __set_qc(self, qc: QuantumCircuit) -> None:
        self.qc = qc
    
    def __get_qc(self) -> QuantumCircuit:
        if not hasattr(self, 'qc'):
            raise AttributeError("Quantum circuit has not been set.")
        return self.qc
    
    def add_measure(self) -> QuantumCircuit:
        qc = self.__get_qc()
        qc.measure(range(self.num_bits, 2 * self.num_bits + 1), range(self.num_bits + 1))
        return qc

def compile_and_execute(qc: QuantumCircuit, shots: int=1024):
    sim = AerSimulator()
    transpiled = transpile(qc, sim)
    res = sim.run(transpiled, shots=shots).result()
    return transpiled, res

adder = CuccaroAdder(num_bits)
qc = adder.generate(15,15)
qc = adder.add_measure()

_, res = compile_and_execute(qc)
print(res.get_counts())

