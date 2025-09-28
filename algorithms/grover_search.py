from qiskit import QuantumCircuit, transpile
from qiskit.circuit import Gate
from qiskit_aer import AerSimulator
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from circuits.adder_interface import AdderInterface

class GroverSearch:
    def __init__(self, adder: AdderInterface):
        self.adder = adder
        self.adder_gate = self.adder.build_adder_gate()

        # Mapping of registers (x, y, z)
        self.mapping = self.adder.get_mapping()
        self.num_bits = len(self.mapping["x"])

        # Total qubits: adder + 1 Grover ancilla
        self.num_qubits = self.adder_gate.num_qubits + 1
        self.input_qubits = self.mapping["x"] + self.mapping["y"] + self.mapping["z"]
        self.grover_ancilla = self.num_qubits - 1
        self.qc = QuantumCircuit(self.num_qubits, len(self.input_qubits))

    def __build_query(self, target: int):
        """
        Builds the query subcircuit that flips the Grover ancilla when the
        sum of x, y, z equals the target value.
        """
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

        return query.to_gate(label="Query")

    def build_oracle(self, target: int) -> Gate:
        """
        Builds the oracle as per original design:
        - Apply adder
        - Apply query circuit for target sum
        - Uncompute adder
        """
        oracle = QuantumCircuit(self.num_qubits, name="Oracle")

        # Apply adder
        oracle.append(self.adder_gate, range(self.adder_gate.num_qubits))

        # Build query circuit
        query = self.__build_query(target)

        # Attach query on z-register + ancillas + grover ancilla
        sum_qubits = self.adder.get_result_qubits()
        oracle.compose(query, qubits=sum_qubits + [self.grover_ancilla], inplace=True)

        # Uncompute adder
        oracle.append(self.adder_gate.inverse(), range(self.adder_gate.num_qubits))

        return oracle.to_gate(label="Oracle")

    def build_diffuser(self) -> Gate:
        """
        Diffuser as in your code: apply H, X, MCX, undo.
        Applies only to input qubits + grover ancilla.
        """
        num_qubits = len(self.input_qubits)
        total_qubits = num_qubits + 1
        diffuser = QuantumCircuit(total_qubits, 0, name="diffuser")

        diffuser.h(range(num_qubits))
        diffuser.x(range(num_qubits))
        diffuser.mcx(list(range(num_qubits)), total_qubits - 1)
        diffuser.x(range(num_qubits))
        diffuser.h(range(num_qubits))

        return diffuser.to_gate(label="Diffuser")

    def apply_grover_iterations(self, target: int, iterations: int):
        # Superposition initialization
        self.qc.h(self.input_qubits)

        for _ in range(iterations):
            oracle = self.build_oracle(target)
            diffuser = self.build_diffuser()
            self.qc.append(oracle, range(self.num_qubits))
            self.qc.append(diffuser, self.input_qubits + [self.grover_ancilla])

    def measure_inputs(self):
        self.qc.measure(self.input_qubits, range(len(self.input_qubits)))

    def run(self, shots=1024):
        backend = AerSimulator()
        compiled = transpile(self.qc, backend)
        result = backend.run(compiled, shots=shots).result()
        return result.get_counts()

    def decode_results(self, counts: dict[str, int]) -> list[dict]:
        """
        Decodes measured bitstrings into a structured format using the adder's mapping.
        
        :param counts: Dictionary from Qiskit get_counts() {bitstring: frequency}
        :return: List of dictionaries, each like:
                {"x": val_x, "y": val_y, "z": val_z, "freq": frequency}
                Sorted by frequency in descending order.
        """
        mapping = self.mapping  # e.g., {"x": [0,1,2], "y": [3,4,5], "z": [6,7,8]}
        decoded = []

        for bitstring, freq in counts.items():
            result = {}
            for reg_name, indices in mapping.items():
                # Extract bits for this register
                bits_for_reg = ''.join(bitstring[i] for i in indices)
                result[reg_name] = int(bits_for_reg, 2)
            result["freq"] = freq
            decoded.append(result)

        # Sort by frequency descending
        return sorted(decoded, key=lambda d: d["freq"], reverse=True)
