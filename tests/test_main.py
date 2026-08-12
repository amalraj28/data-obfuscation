import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from qiskit import QuantumCircuit

import main as experiment


class TestMain(unittest.TestCase):
    def test_prepares_only_small_basis_gates_for_obfuscation(self):
        circuit = QuantumCircuit(4)
        circuit.mcx([0, 1, 2], 3)

        prepared = experiment._prepare_for_obfuscation(circuit)

        self.assertTrue(
            all(item.operation.num_qubits <= 2 for item in prepared.data)
        )
        self.assertTrue(set(prepared.count_ops()).issubset({"u", "cx"}))

    def test_reports_the_exact_selected_circuit(self):
        with tempfile.TemporaryDirectory() as directory:
            captured = {}

            def execute(circuit, shots):
                captured["circuit"] = circuit
                captured["shots"] = shots
                return {"001": 7, "000": 1}, 0.25

            with patch.object(experiment, "_execute", side_effect=execute):
                result = experiment.main(
                    target=1,
                    shots=8,
                    obfuscate=True,
                    output_dir=directory,
                    draw=False,
                )

            self.assertIs(captured["circuit"], result["output_circuit"])
            self.assertEqual(captured["shots"], 8)
            self.assertIsNot(result["output_circuit"], result["original_circuit"])
            self.assertEqual(result["manifest"]["num_solutions"], 1)
            self.assertEqual(result["manifest"]["successful_shots"], 7)
            self.assertEqual(result["manifest"]["success_rate"], 0.875)
            self.assertEqual(result["manifest"]["run_time_seconds"], 0.25)

            manifest = json.loads(result["paths"]["manifest"].read_text())
            self.assertEqual(manifest, result["manifest"])
            self.assertTrue(result["paths"]["qasm"].exists())
            self.assertTrue(result["paths"]["result"].exists())

    def test_unobfuscated_mode_and_overwrite_protection(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(
                experiment,
                "_execute",
                return_value=({"001": 1}, 0.1),
            ):
                result = experiment.main(
                    target=1,
                    shots=1,
                    obfuscate=False,
                    output_dir=directory,
                    draw=False,
                )
                self.assertIs(
                    result["output_circuit"],
                    result["original_circuit"],
                )
                with self.assertRaises(FileExistsError):
                    experiment.main(
                        target=1,
                        shots=1,
                        obfuscate=False,
                        output_dir=directory,
                        draw=False,
                    )

    def test_draws_only_the_complete_output_circuit(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(
                experiment,
                "_execute",
                return_value=({"001": 1}, 0.1),
            ), patch.object(QuantumCircuit, "draw", autospec=True) as draw:
                result = experiment.main(
                    target=1,
                    shots=1,
                    obfuscate=False,
                    output_dir=directory,
                    draw=True,
                )

            draw.assert_called_once()
            self.assertIs(draw.call_args.args[0], result["output_circuit"])
            self.assertEqual(
                Path(draw.call_args.kwargs["filename"]),
                result["paths"]["figure"],
            )


if __name__ == "__main__":
    unittest.main()
