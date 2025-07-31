# circuits/circuit_initializer.py
from qiskit import QuantumCircuit


class CircuitInitializer:
    """
    Generic initializer for quantum circuits.
    Handles:
      - Input validation
      - Initializing qubits based on provided mapping
    """

    @staticmethod
    def validate_inputs(values: dict[str, int], mapping: dict[str, list[int]]):
        """
        Validate input values against mapping constraints.
        :param values: {"x": int, "y": int, ...}
        :param mapping: {"x": [indices], "y": [indices], ...}
        :raises ValueError: if validation fails
        """
        for reg, val in values.items():
            if reg not in mapping:
                raise ValueError(f"No mapping provided for register '{reg}'")
            if val < 0:
                raise ValueError(f"Value for '{reg}' cannot be negative")

            # Ensure value fits in allocated qubits
            num_qubits = len(mapping[reg])
            if val >= (1 << num_qubits):
                raise ValueError(
                    f"Value {val} does not fit in {num_qubits} qubits for '{reg}'"
                )

    @staticmethod
    def initialize(qc: QuantumCircuit, values: dict, mapping: dict):
        """
        Apply X gates based on values and mapping.
        Assumes validation is done before calling.
        """
        CircuitInitializer.validate_inputs(values, mapping)
        for reg, val in values.items():
            for i, qubit in enumerate(mapping[reg]):
                if (val >> i) & 1:
                    qc.x(qubit)
