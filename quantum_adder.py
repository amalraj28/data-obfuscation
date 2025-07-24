from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from qiskit.circuit.library import CDKMRippleCarryAdder
from qiskit_aer import AerSimulator
import matplotlib.pyplot as plt
from qiskit.visualization import plot_histogram


class TripleAdder:
    def __init__(self, num_bits: int):
        self.num_bits = num_bits
        self._build_circuit()

    def _build_circuit(self):
        n = self.num_bits

        # Define quantum registers
        self.qr_num1 = QuantumRegister(n, "num1")  # -->
        self.qr_num2 = QuantumRegister(n, "num2")  # -->
        self.qr_cout0 = QuantumRegister(1, "cout0")
        self.qr_num3 = QuantumRegister(n, "num3")  # -->
        self.qr_anc0 = QuantumRegister(1, "anc0")
        self.qr_cout1 = QuantumRegister(1, "cout1")
        self.qr_anc1 = QuantumRegister(1, "anc1")
        self.cr = ClassicalRegister(n + 2, "cr")
        self.cr_x = ClassicalRegister(3, "crx")
        self.cr_y = ClassicalRegister(3, "cry")
        self.cr_z = ClassicalRegister(3, "crz")
        self.qr_ancilla_grover = QuantumRegister(1, "anc_grover")

        self.qc = QuantumCircuit(
            self.qr_num1,
            self.qr_num2,
            self.qr_cout0,
            self.qr_num3,
            self.qr_anc0,
            self.qr_cout1,
            self.qr_anc1,
            self.qr_ancilla_grover,
            # self.cr,
            self.cr_x,
            self.cr_y,
            self.cr_z,
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
        self.adder1 = CDKMRippleCarryAdder(n, kind="half")
        self.qc.compose(
            self.adder1,
            qubits=self.qr_num1[:]
            + self.qr_num2[:]
            + self.qr_cout0[:]
            + self.qr_anc0[:],
            inplace=True,
        )

        # Second adder: result + num3 -> num3 (overwritten)
        self.adder2 = CDKMRippleCarryAdder(n + 1, kind="half")
        self.qc.compose(
            self.adder2,
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



choice = input("Do you wish to delete temp.txt (Y/N)?: ")

if choice.lower() == 'y':
    import os
    os.remove("temp.txt")

num_bits = 3
adder = TripleAdder(num_bits=num_bits)
adder.initialize_inputs(2, 0, 2, randomize=True)

for _ in range(12):
    adder.build_adders()

    # ********************* Insert Grover Oracle here **********************

    target = 15
    target_bin = format(target, f"0{num_bits+2}b")[::-1]
    # print(target_bin)
    sum_bits = adder.qr_num3[:] + adder.qr_anc0[:] + adder.qr_cout1[:]

    # for _ in range(2):

    adder.qc.h(adder.qr_ancilla_grover[:])
    adder.qc.z(adder.qr_ancilla_grover[:])

    for i in range(len(target_bin) - 1, -1, -1):
        if target_bin[i] == "0":
            adder.qc.x(sum_bits[i])

    adder.qc.mcx(sum_bits, adder.qr_ancilla_grover[:])

    for i in range(len(target_bin) - 1, -1, -1):
        if target_bin[i] == "0":
            adder.qc.x(sum_bits[i])


    # adder.qc.z(adder.qr_ancilla_grover[:])
    # adder.qc.h(adder.qr_ancilla_grover[:])
    adder.qc.compose(
        adder.adder2.inverse(),
        qubits=(
            adder.qr_num2[:]
            + adder.qr_cout0[:]
            + adder.qr_num3[:]
            + adder.qr_anc0[:]
            + adder.qr_cout1[:]
            + adder.qr_anc1[:]
        ),
        inplace=True,
    )

    adder.qc.compose(
        adder.adder1.inverse(),
        qubits=(
            adder.qr_num1[:] + adder.qr_num2[:] + adder.qr_cout0[:] + adder.qr_anc0[:]
        ),
        inplace=True,
    )
    # *************************** Oracle ends ******************************

    # ********************* Insert Grover diffuser here ********************
    qubits = adder.qr_num1[:] + adder.qr_num2[:] + adder.qr_num3[:]
    adder.qc.h(qubits)
    adder.qc.x(qubits)
    # adder.qc.h(qubits[-1])
    adder.qc.mcx(qubits[:], adder.qr_ancilla_grover[:])
    # adder.qc.h(qubits[-1])
    adder.qc.x(qubits)
    adder.qc.h(qubits)
# *************************** Diffuser ends ****************************

adder.qc.measure(adder.qr_num1[:], adder.cr_x[:])
adder.qc.measure(adder.qr_num2[:], adder.cr_y[:])
adder.qc.measure(adder.qr_num3[:], adder.cr_z[:])
# adder.qc.draw("mpl")
# plt.show()

counts = adder.run(shots=10000)
tot = 0

# plot_histogram(counts, filename='temp.png')
# plt.show()

counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)


for value, freq in counts:
    x, y, z = [int(val, 2) for val in value.split()]
    tot += freq
    with open("temp.txt", "a") as file:
        file.write(
            f"x = {x}, y = {y}, z = {z}, Sum = {x + y + z}, Frequency = {freq}\n"
        )
print(f"Frequency = {tot}")

    