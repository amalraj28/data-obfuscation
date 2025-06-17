import math
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from helper import compile_circuit


class QRandom:
    def __init__(self, shots=1024, backend=None):
        self.backend = backend or AerSimulator()
        self.shots = shots  # number of times to run the circuit

    def randint(self, start, end):
        if start > end:
            raise ValueError("start must be <= end")

        if start < 0 or end < 0:
            raise ValueError(
                "Negative values not supported!"
            )  # TODO: Extend functionality for negative values

        n_values = end - start + 1
        num_qubits = max(math.ceil(math.log2(n_values)), 1)

        # Step 1: Create circuit
        qc = QuantumCircuit(num_qubits, num_qubits)
        qc.h(range(num_qubits))  # uniform superposition
        qc.measure(range(num_qubits), range(num_qubits))
        job = compile_circuit(qc)

        while True:
            # Step 2: Run the circuit
            counts = self.backend.run(job, shots=self.shots).result().get_counts()

            # Step 3: Iterate over results
            for bitstring in counts:
                val = int(bitstring, 2)
                if val < n_values:
                    return start + val  # shift into [start, end] range


# Test cases for randint function

# q_random = QRandom()
# for _ in range(100):
#     num = q_random.randint(3, 10)
#     print(num)
#     if num >= 11:
#         raise ValueError("Wrong functionality")


def obfuscate_number(n: int):
    if n < 3:
        raise ValueError("n must be at least 3 to split into 3 positive integers.")

    q_random = QRandom()

    a = q_random.randint(1, n - 2)
    b = q_random.randint(1, n - a - 1)
    c = n - a - b  # Remaining

    return a, b, c


for _ in range(100):
    with open("file.txt", "a") as file:
        file.write(f"{obfuscate_number(13)}\n")
