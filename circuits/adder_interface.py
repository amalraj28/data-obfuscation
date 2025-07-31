from typing import Protocol
from qiskit.circuit import Gate


class AdderInterface(Protocol):
    def build_adder_gate(self) -> Gate:
        """Return a Qiskit Gate implementing the adder logic."""
        ...

    def get_mapping(self) -> dict:
        """Return mapping of logical registers to physical qubits."""
        ...

    def get_result_qubits(self) -> list[int]:
        """Return indices of qubits representing the sum result."""
        ...
