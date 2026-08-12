from qiskit import QuantumCircuit, transpile
from qiskit.circuit import Gate
from qiskit_aer import AerSimulator

from circuits.adder_interface import AdderInterface


class GroverSearch:
    def __init__(
        self,
        adder: AdderInterface,
    ):
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

    def _validate_target(self, target: int) -> None:
        max_sum = 3 * ((1 << self.num_bits) - 1)
        if not isinstance(target, int) or isinstance(target, bool):
            raise TypeError("target must be an integer")
        if not 0 <= target <= max_sum:
            raise ValueError(f"target must be between 0 and {max_sum}")

    def _build_query_circuit(self, target: int) -> QuantumCircuit:
        """
        Builds the query subcircuit that flips the Grover ancilla when the
        sum of x, y, z equals the target value.
        """
        num_sum_qubits = self.num_bits + 2
        num_ancillas = 1
        total_qubits = num_sum_qubits + num_ancillas
        query = QuantumCircuit(total_qubits, 0, name="query")

        self._validate_target(target)

        target_bin = format(target, f"0{num_sum_qubits}b")[::-1]

        x_qubits = {i for i in range(num_sum_qubits) if target_bin[i] == "0"}

        mcx_circuit = QuantumCircuit(total_qubits, 0)
        for qubit in x_qubits:
            mcx_circuit.x(qubit)
        mcx_circuit.mcx(
            list(range(num_sum_qubits)),
            total_qubits - num_ancillas,
        )
        for qubit in x_qubits:
            mcx_circuit.x(qubit)

        query.compose(mcx_circuit, inplace=True)

        return query

    def build_oracle_circuit(
        self,
        target: int,
    ) -> QuantumCircuit:
        """Build an oracle circuit whose internal operations remain visible."""
        oracle = QuantumCircuit(
            self.num_qubits,
            name="Oracle",
        )
        adder_qubits = list(range(self.adder_gate.num_qubits))
        sum_qubits = self.adder.get_result_qubits()
        query_qubits = sum_qubits + [self.grover_ancilla]

        adder_circuit = self.adder_gate.definition
        if adder_circuit is None:
            raise ValueError("Adder gate has no circuit definition")

        oracle.compose(
            adder_circuit,
            qubits=adder_qubits,
            inplace=True,
        )
        oracle.compose(
            self._build_query_circuit(target),
            qubits=query_qubits,
            inplace=True,
        )
        oracle.compose(
            adder_circuit.inverse(),
            qubits=adder_qubits,
            inplace=True,
        )

        return oracle

    def build_oracle_gate(
        self,
        target: int,
    ) -> Gate:
        """Build the oracle as a compact gate for unobfuscated circuits."""
        return self.build_oracle_circuit(target).to_gate(label="Oracle")

    def build_diffuser_circuit(self) -> QuantumCircuit:
        """Build a diffuser circuit whose internal operations remain visible."""
        num_qubits = len(self.input_qubits)
        total_qubits = num_qubits + 1
        diffuser = QuantumCircuit(total_qubits, 0, name="Diffuser")

        diffuser.h(range(num_qubits))
        diffuser.x(range(num_qubits))
        diffuser.mcx(list(range(num_qubits)), total_qubits - 1)
        diffuser.x(range(num_qubits))
        diffuser.h(range(num_qubits))

        return diffuser

    def build_diffuser_gate(self) -> Gate:
        """Build the diffuser as a compact gate for unobfuscated circuits."""
        return self.build_diffuser_circuit().to_gate(label="Diffuser")

    def apply_grover_iterations(
        self,
        target: int,
        iterations: int,
        expand_components: bool = False,
    ) -> None:
        self._validate_target(target)
        if not isinstance(iterations, int) or isinstance(iterations, bool):
            raise TypeError("iterations must be an integer")
        if iterations < 0:
            raise ValueError("iterations must be non-negative")

        # Superposition initialization
        self.qc.h(self.input_qubits)
        # Prepare the phase-kickback ancilla once; every oracle and diffuser
        # preserves it in |->.
        self.qc.h(self.grover_ancilla)
        self.qc.z(self.grover_ancilla)

        diffuser_qubits = self.input_qubits + [self.grover_ancilla]

        if expand_components:
            oracle_circuit = self.build_oracle_circuit(target)
            diffuser_circuit = self.build_diffuser_circuit()
            for _ in range(iterations):
                self.qc.compose(oracle_circuit, inplace=True)
                self.qc.compose(
                    diffuser_circuit,
                    qubits=diffuser_qubits,
                    inplace=True,
                )
            return

        oracle_gate = self.build_oracle_gate(target)
        diffuser_gate = self.build_diffuser_gate()
        for _ in range(iterations):
            self.qc.append(oracle_gate, range(self.num_qubits))
            self.qc.append(diffuser_gate, diffuser_qubits)

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
                bits_for_reg = "".join(
                    bitstring[-1 - index] for index in reversed(indices)
                )
                result[reg_name] = int(bits_for_reg, 2)
            result["freq"] = freq
            decoded.append(result)

        # Sort by frequency descending
        return sorted(
            decoded,
            key=lambda d: d["freq"],
            reverse=True,
        )
