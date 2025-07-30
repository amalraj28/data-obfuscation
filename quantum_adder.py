from qiskit import QuantumCircuit, transpile, QuantumRegister, ClassicalRegister
from qiskit.circuit.library import CDKMRippleCarryAdder
from qiskit_aer import AerSimulator
import os
from math_utils import optimal_grover_iterations


class TripleAdder:
    def __init__(self, num_bits: int):
        self.num_bits = num_bits
        self._build_circuit()

    def _build_circuit(self):
        n = self.num_bits

        # Define quantum registers
        self.qr_num1 = QuantumRegister(n, "num1")  # --> input 1
        self.qr_num2 = QuantumRegister(n, "num2")  # --> input 2
        self.qr_cout0 = QuantumRegister(1, "cout0")
        self.qr_num3 = QuantumRegister(n, "num3")  # --> input 3
        self.qr_anc0 = QuantumRegister(1, "anc0")
        self.qr_cout1 = QuantumRegister(1, "cout1")
        self.qr_anc1 = QuantumRegister(1, "anc1")
        self.cr = ClassicalRegister(n + 2, "cr")
        self.cr_x = ClassicalRegister(n, "crx")
        self.cr_y = ClassicalRegister(n, "cry")
        self.cr_z = ClassicalRegister(n, "crz")
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

    def append_measure_to_inputs(self):
        self.qc.measure(self.qr_num1[:], self.cr_x[:])
        self.qc.measure(self.qr_num2[:], self.cr_y[:])
        self.qc.measure(self.qr_num3[:], self.cr_z[:])

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

    def build_inverse_adder(self):
        self.qc.compose(
            self.adder2.inverse(),
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

        self.qc.compose(
            self.adder1.inverse(),
            qubits=(
                self.qr_num1[:] + self.qr_num2[:] + self.qr_cout0[:] + self.qr_anc0[:]
            ),
            inplace=True,
        )

    def get_input_qubits(self) -> list[QuantumRegister]:
        return self.qr_num1[:] + self.qr_num2[:] + self.qr_num3[:]


class GroverSearch(TripleAdder):
    def __init__(self, num_bits: int):
        super().__init__(num_bits)
        self.num_bits = num_bits
        self.initialize_inputs()

    def apply_grover_op(self, num_iterations: int, target: int = 15):
        self.target = target
        for _ in range(num_iterations):
            self.__generate_oracle(target)
            diffuser = self.__generate_diffuser()
            self.qc.compose(
                diffuser,
                qubits=self.get_input_qubits() + self.qr_ancilla_grover[:],
                inplace=True,
            )

    def __generate_oracle(self, target: int = 15):
        self.build_adders()

        query = self.__generate_query_circuit(target=target)

        self.qc.compose(
            query,
            qubits=self.qr_num3[:]
            + self.qr_anc0[:]
            + self.qr_cout1[:]
            + self.qr_ancilla_grover[:],
            inplace=True,
        )

        self.build_inverse_adder()

    def __generate_diffuser(self):
        num_qubits = 3 * self.num_bits
        num_ancillas = 1
        total_qubits = num_qubits + num_ancillas

        diffuser = QuantumCircuit(total_qubits, 0, name="diffuser")
        diffuser.h(range(num_qubits))
        diffuser.x(range(num_qubits))
        diffuser.mcx(list(range(num_qubits)), total_qubits - 1)
        diffuser.x(range(num_qubits))
        diffuser.h(range(num_qubits))

        return diffuser

    def __generate_query_circuit(self, target: int = 15) -> QuantumCircuit:
        num_sum_qubits = self.num_bits + 2
        num_ancillas = 1
        total_qubits = num_sum_qubits + num_ancillas
        query = QuantumCircuit(total_qubits, 0, name="query")

        query.h(total_qubits - 1)
        query.z(total_qubits - 1)

        target_bin = format(target, f"0{num_sum_qubits}b")[::-1]

        for i in range(num_sum_qubits - 1, -1, -1):
            if target_bin[i] == "0":
                query.x(i)

        query.mcx(list(range(num_sum_qubits)), total_qubits - 1)

        for i in range(num_sum_qubits - 1, -1, -1):
            if target_bin[i] == "0":
                query.x(i)

        return query


if __name__ == "__main__":
    if os.path.exists("temp.txt"):
        os.remove("temp.txt")

    num_bits = 4
    N = (2**num_bits) ** 3

    max_value = ((2**num_bits) - 1) * 3

    for target in range(max_value + 1):
        num_iterations = optimal_grover_iterations(num_bits, target)
        circ = GroverSearch(num_bits=num_bits)
        circ.apply_grover_op(num_iterations, target=target)
        circ.append_measure_to_inputs()
        counts = circ.run(shots=10000)
        tot = 0

        counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)

        for value, freq in counts:
            x, y, z = [int(val, 2) for val in value.split()]
            tot += freq if x + y + z == target else 0
            # with open("temp.txt", "a") as file:
            #     file.write(
            #         f"x = {x}, y = {y}, z = {z}, Sum = {x + y + z}, Frequency = {freq}\n"
            #     )
        print(
            f"Frequency when target is {target} = {tot} (Number of iterations = {num_iterations})"
        )
