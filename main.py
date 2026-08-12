import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path

from qiskit import transpile, QuantumCircuit
from qiskit_aer import AerSimulator

from algorithms.basis_transformation import apply_basis_obfuscation
from circuits.adder_builder import AdderBuilder
from circuits.grover_search import GroverSearch
from utils.helper import circuit_to_qasm
from utils.math_utils import optimal_grover_iterations

DEFAULT_TARGET = 19
DEFAULT_SHOTS = 1024
DEFAULT_OBFUSCATE = True
DEFAULT_OUTPUT_DIR = Path("results/generated")
OBFUSCATION_BASIS_GATES = ["u", "cx"]


def _execute(
    circuit: QuantumCircuit,
    shots: int,
) -> tuple[dict[str, int], float]:
    backend = AerSimulator()
    compiled = transpile(circuit, backend)
    start_time = time.perf_counter()
    result = backend.run(compiled, shots=shots)
    end_time = time.perf_counter()
    counts: dict[str, int] = result.result().get_counts()
    return counts, end_time - start_time


def _output_paths(
    output_dir: Path,
    target: int,
    mode: str,
) -> dict[str, Path]:
    stem = f"target_{target}_{mode}"
    return {
        "qasm": output_dir / f"{stem}_circuit.qasm",
        "figure": output_dir / f"{stem}_circuit.png",
        "result": output_dir / f"{stem}_result.txt",
        "manifest": output_dir / f"{stem}_manifest.json",
    }


def _ensure_outputs_available(
    paths: dict[str, Path],
    draw: bool,
    overwrite: bool,
) -> None:
    required = [paths["qasm"], paths["result"], paths["manifest"]]
    if draw:
        required.append(paths["figure"])

    existing = [path for path in required if path.exists()]
    if existing and not overwrite:
        names = ", ".join(path.name for path in existing)
        raise FileExistsError(f"Output already exists: {names}")


def _prepare_for_obfuscation(circuit: QuantumCircuit) -> QuantumCircuit:
    return transpile(
        circuit,
        basis_gates=OBFUSCATION_BASIS_GATES,
        optimization_level=0,
    )


def main(
    target: int = DEFAULT_TARGET,
    shots: int = DEFAULT_SHOTS,
    obfuscate: bool = DEFAULT_OBFUSCATE,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    draw: bool = False,
    overwrite: bool = False,
):
    """Run one experiment and return its circuits, counts, metrics, and paths."""
    if not isinstance(target, int) or isinstance(target, bool):
        raise TypeError("target must be an integer")
    if target < 0:
        raise ValueError("target must be non-negative")
    if not isinstance(shots, int) or isinstance(shots, bool):
        raise TypeError("shots must be an integer")
    if shots <= 0:
        raise ValueError("shots must be positive")

    output_dir = Path(output_dir)
    mode = "obfuscated" if obfuscate else "unobfuscated"
    paths = _output_paths(output_dir, target, mode)
    _ensure_outputs_available(paths, draw, overwrite)

    num_bits = max(1, math.ceil(math.log2(target / 3 + 1)))
    grover = GroverSearch(AdderBuilder(num_bits))
    iterations = optimal_grover_iterations(num_bits, target)
    grover.apply_grover_iterations(target, iterations)
    grover.measure_inputs()

    original_circuit = grover.qc
    output_circuit = (
        apply_basis_obfuscation(
            _prepare_for_obfuscation(
                original_circuit,
            ),
        )
        if obfuscate
        else original_circuit
    )
    counts, run_time = _execute(output_circuit, shots)
    decoded = grover.decode_results(counts)
    correct_results = [
        result
        for result in decoded
        if result["x"] + result["y"] + result["z"] == target
    ]
    successful_shots = sum(result["freq"] for result in correct_results)

    gate_counts = {
        str(name): int(count) for name, count in output_circuit.count_ops().items()
    }
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target": target,
        "num_bits": num_bits,
        "iterations": iterations,
        "shots": shots,
        "mode": mode,
        "run_time_seconds": run_time,
        "num_solutions": len(correct_results),
        "successful_shots": successful_shots,
        "success_rate": successful_shots / shots,
        "depth": output_circuit.depth(),
        "num_qubits": output_circuit.num_qubits,
        "gate_counts": gate_counts,
        "files": {
            name: path.name
            for name, path in paths.items()
            if (name != "figure") or draw
        },
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    paths["qasm"].write_text(
        circuit_to_qasm(output_circuit),
        encoding="utf-8",
    )
    paths["result"].write_text(
        "\n".join(
            [
                f"target = {target}",
                f"num_bits = {num_bits}",
                f"iterations = {iterations}",
                f"shots = {shots}",
                f"mode = {mode}",
                f"run_time_seconds = {run_time}",
                f"num_solutions = {len(correct_results)}",
                f"successful_shots = {successful_shots}",
                f"success_rate = {successful_shots / shots}",
                f"depth = {output_circuit.depth()}",
                f"num_qubits = {output_circuit.num_qubits}",
                f"gate_counts = {json.dumps(gate_counts, sort_keys=True)}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    paths["manifest"].write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if draw:
        output_circuit.draw("mpl", filename=str(paths["figure"]))

    return {
        "original_circuit": original_circuit,
        "output_circuit": output_circuit,
        "counts": counts,
        "decoded_results": decoded,
        "manifest": manifest,
        "paths": paths,
    }


if __name__ == "__main__":
    main()
