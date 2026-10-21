# Data Obfuscation using Decomposition and Grover Amplification

This repository explores basis obfuscation of Grover-search circuits for a
quantum-classical data workflow. The obfuscator changes the local basis at each
gate boundary while preserving the circuit's behavior.

Grover phase flips use the sum register's most significant bit in the oracle
and the input register's most significant bit in the diffuser via H-MCX-H.
No separate phase ancilla is needed: three n-bit inputs use 3n + 4 qubits
(13 qubits for the default three-bit inputs).

## Repository layout

- `algorithms/`: whole-circuit basis obfuscation and supporting algorithms.
- `circuits/`: the three-input adder and Grover circuit construction.
- `utils/`: circuit serialization and mathematical helpers.
- `tests/`: unit and integration tests.
- `results/`: retained experiment summaries and figures.

## Setup

Create and activate a virtual environment, then install the dependencies:

```bash
python -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows, activate the environment with `venv\Scripts\activate` instead.

## Run an experiment

Run the default experiment directly:

```bash
python main.py
```

New outputs are written to the ignored `results/generated/` directory. A
default run produces OpenQASM 3 and a JSON manifest. The
manifest reports metrics from the same circuit that was exported and executed.

The default target is 19. Before obfuscation, the compact Grover circuit is
decomposed once with `decompose(reps=1)`. Remaining composite and wide gates
are represented by dense matrices during obfuscation.

The runner is also a normal Python function:

```python
from main import main

result = main(
    target=5,
    shots=1024,
    obfuscate=True,
    output_dir="results/generated",
    draw=False,
    overwrite=False,
)
```

Set `draw=True` to render both the original and obfuscated circuits. In
unobfuscated mode, only the original circuit is rendered. Images are saved
alongside the QASM and manifest in the output directory.

## Obfuscation API

```python
from algorithms.basis_transformation import apply_basis_obfuscation

obfuscated_circuit = apply_basis_obfuscation(circuit)
```

`apply_basis_obfuscation` uses secure operating-system randomness. There is no
seeded production mode, so repeated calls normally produce different but
semantically equivalent circuits.

Obfuscation also fills idle wires in multi-qubit layers with random single-qubit
unitaries. Their inverse factors are absorbed into the next multi-qubit gate
on the same wire when possible. Otherwise they are emitted before the next
operation on that wire or at circuit end. Multiple padding factors can share
one inverse correction. This preserves circuit behavior without increasing
multi-qubit gate widths, and respects measurements, resets, barriers, and
classical control. Disable padding with
`apply_basis_obfuscation(circuit, pad_idle_wires=False)`.

The existing fusion pass still absorbs only immediately adjacent single-qubit
gates; padding is added afterward. The denser drawing reduces visible idle
patterns but retains multi-qubit connectivity. Optimization can remove the
identity padding, and the drawing's layout affects how full it appears.

Set `fuse_single_qubit_gates=False` to disable fusion.

## Tests

Run the complete suite with:

```bash
python -m unittest discover -s tests -v
```

The suite covers circuit equivalence, wide MCX gates, QASM round trips,
measurements and classical control, experiment reporting, and output
protection.
