from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from qiskit.circuit.library import CDKMRippleCarryAdder
from qiskit_aer import AerSimulator


class TripleAdder:
    def __init__(self, num_bits: int):
        self.num_bits = num_bits
        self._build_circuit()

    def _build_circuit(self):
        n = self.num_bits

        # Define quantum registers
        self.qr_num1 = QuantumRegister(n, "num1")
        self.qr_num2 = QuantumRegister(n, "num2")
        self.qr_cout0 = QuantumRegister(1, "cout0")
        self.qr_num3 = QuantumRegister(n, "num3")
        self.qr_anc0 = QuantumRegister(1, "anc0")
        self.qr_cout1 = QuantumRegister(1, "cout1")
        self.qr_anc1 = QuantumRegister(1, "anc1")
        self.cr = ClassicalRegister(n + 2, "cr")

        self.qc = QuantumCircuit(
            self.qr_num1,
            self.qr_num2,
            self.qr_cout0,
            self.qr_num3,
            self.qr_anc0,
            self.qr_cout1,
            self.qr_anc1,
            self.cr,
        )

    def initialize_inputs(self, *args, randomize: bool = True):
        if randomize:
            for reg in [self.qr_num1, self.qr_num2, self.qr_num3]:
                self.qc.h(reg)
            return

        def apply_binary(qreg, value, bits):
            for i in range(bits):
                if (value >> i) & 1:
                    self.qc.x(qreg[i])

        print(args)

        apply_binary(self.qr_num1, args[0], self.num_bits)
        apply_binary(self.qr_num2, args[1], self.num_bits)
        apply_binary(self.qr_num3, args[2], self.num_bits)

    def build_adders(self):
        n = self.num_bits

        # First adder: num1 + num2 -> num2 (overwritten)
        adder1 = CDKMRippleCarryAdder(n, kind="half")
        self.qc.compose(
            adder1,
            qubits=self.qr_num1[:]
            + self.qr_num2[:]
            + self.qr_cout0[:]
            + self.qr_anc0[:],
            inplace=True,
        )

        # Second adder: result + num3 -> num3 (overwritten)
        adder2 = CDKMRippleCarryAdder(n + 1, kind="half")
        self.qc.compose(
            adder2,
            qubits=(
                self.qr_num2[:]
                + self.qr_cout0[:]
                + self.qr_num3[:]
                + self.qr_anc0[:]
                + self.qr_cout1[:]
                + self.qr_anc1[:]
            ),
            inplace=True,
        )

    def measure_result(self):
        self.qc.measure(
            [*self.qr_num3, *self.qr_anc0, *self.qr_cout1],
            self.cr,
        )

    def get_circuit(self):
        return self.qc

    def run(self, shots=1024):
        backend = AerSimulator()
        compiled = transpile(self.qc, backend)
        result = backend.run(compiled, shots=shots).result()
        counts = result.get_counts()
        return counts

    def decode_results(self, counts):
        decoded = []
        for bitstring, freq in counts.items():
            val = int(bitstring, 2)
            decoded.append((val, freq))
        decoded.sort(reverse=True, key=lambda x: x[1])
        return decoded


adder = TripleAdder(num_bits=3)
adder.initialize_inputs(2, 4, 2, randomize=False)
adder.build_adders()
adder.measure_result()

counts = adder.run()
results = adder.decode_results(counts)

for value, freq in results:
    print(f"Sum = {value}, Frequency = {freq}")
