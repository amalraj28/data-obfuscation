# Data Obfuscation using Decomposition and Grover Amplification

This repository explores basis obfuscation of Grover-search circuits for a
quantum-classical data workflow. The obfuscator changes the local basis at each
gate boundary while preserving the circuit's behavior.

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
default run produces OpenQASM 3, a text summary, and a JSON manifest. The
manifest reports metrics from the same circuit that was exported and executed.

The default target is 19. Before obfuscation, the compact Grover circuit is
transpiled once to `u` and `cx` gates. This avoids constructing dense matrices
for wide operations and keeps the default run practical on an ordinary
computer.

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

Set `draw=True` to also render the complete circuit. For target 19 this image
is very large and Matplotlib can take several minutes and substantial memory,
so drawing is disabled by default. Set `overwrite=True` only when replacing
files for the same target and mode is intentional.

## Obfuscation API

```python
from algorithms.basis_transformation import apply_basis_obfuscation

obfuscated_circuit = apply_basis_obfuscation(circuit)
```

`apply_basis_obfuscation` uses secure operating-system randomness. There is no
seeded production mode, so repeated calls normally produce different but
semantically equivalent circuits.

Before obfuscation, `main.py` lowers the complete Grover circuit to `u` and
`cx` gates with Qiskit's optimization level 0. This keeps the transformation
matrices small while avoiding optimization-driven changes to the algorithm.

## Tests

Run the complete suite with:

```bash
python -m unittest discover -s tests -v
```

The suite covers circuit equivalence, wide MCX gates, QASM round trips,
measurements and classical control, experiment reporting, and output
protection.
