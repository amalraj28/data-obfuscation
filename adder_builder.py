# circuits/adder_builder.py
from qiskit import QuantumCircuit
from qiskit.circuit import Gate
from qiskit.circuit.library import CDKMRippleCarryAdder
from adder_interface import AdderInterface

class AdderBuilder(AdderInterface):
    """
    Builds a composite gate for adding three k-bit numbers (x, y, z).
    Uses two CDKMRippleCarryAdders internally:
      - Adds x + y -> y
      - Then adds y + z -> z
    """

    def __init__(self, num_bits: int):
        self.num_bits = num_bits
    
    def build_adder_gate(self) -> Gate:
        return self.build_triple_adder_gate()

    def build_triple_adder_gate(self) -> Gate:
        """Creates a composite gate for adding three numbers."""
        n = self.num_bits

        # Total qubits = 3*n for x,y,z + 4 ancillas (cout0, anc0, cout1, anc1)
        total_qubits = 3 * n + 4
        qc = QuantumCircuit(total_qubits, name="TripleAdder")

        # Allocate slices
        qr_num1 = list(range(0, n))  # x
        qr_num2 = list(range(n, 2 * n))  # y
        qr_num3 = list(range(2 * n, 3 * n))  # z
        qr_cout0 = [3 * n]  # first carry- out
        qr_anc0 = [3 * n + 1]
        qr_cout1 = [3 * n + 2]
        qr_anc1 = [3 * n + 3]

        # First adder: x + y -> y
        adder1 = CDKMRippleCarryAdder(n, kind="half")
        qc.compose(
            adder1,
            qubits=qr_num1 + qr_num2 + qr_cout0 + qr_anc0,
            inplace=True,
        )

        # Second adder: (x+y) + z -> z
        adder2 = CDKMRippleCarryAdder(n + 1, kind="half")
        qc.compose(
            adder2,
            qubits=qr_num2 + qr_cout0 + qr_num3 + qr_anc0 + qr_cout1 + qr_anc1,
            inplace=True,
        )

        # Convert to gate
        return qc.to_gate(label="TripleAdder")

    def get_mapping(self) -> dict:
        """
        Returns mapping of logical registers to physical qubit indices:
        {"x": [...], "y": [...], "z": [...]}
        """
        n = self.num_bits
        return {
            "x": list(range(0, n)),
            "y": list(range(n, 2 * n)),
            "z": list(range(2 * n, 3 * n)),
        }

    def get_result_qubits(self):
        """
        Returns indices of the qubits that represent the final sum:
        z-register and the second carry bit (cout1).
        """
        n = self.num_bits
        return list(range(2 * n, 3 * n)) + [3 * n + 1] + [3 * n + 2]
