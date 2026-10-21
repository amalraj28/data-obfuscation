import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from qiskit import QuantumCircuit

import main as experiment


class TestMain(unittest.TestCase):
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
            self.assertNotIn("result", manifest["files"])
            self.assertNotIn("figure", manifest["files"])
            self.assertNotIn("original_figure", manifest["files"])

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

    def test_draws_only_the_original_in_unobfuscated_mode(self):
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
            self.assertIs(draw.call_args.args[0], result["original_circuit"])
            self.assertEqual(
                Path(draw.call_args.kwargs["filename"]),
                result["paths"]["original_figure"],
            )
            self.assertNotIn("figure", result["paths"])
            self.assertNotIn("figure", result["manifest"]["files"])
            self.assertIn("original_figure", result["manifest"]["files"])

    def test_draws_original_and_obfuscated_circuits(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(
                experiment, "_execute", return_value=({"001": 1}, 0.1)
            ), patch.object(QuantumCircuit, "draw", autospec=True) as draw:
                result = experiment.main(
                    target=1, shots=1, obfuscate=True,
                    output_dir=directory, draw=True,
                )

            self.assertEqual(draw.call_count, 2)
            for call, circuit, key in zip(
                draw.call_args_list,
                (result["original_circuit"], result["output_circuit"]),
                ("original_figure", "figure"),
            ):
                self.assertIs(call.args[0], circuit)
                self.assertEqual(Path(call.kwargs["filename"]), result["paths"][key])
                self.assertEqual(result["manifest"]["files"][key], result["paths"][key].name)

    def test_original_image_is_protected_from_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = experiment._output_paths(Path(directory), 1, "obfuscated")
            paths["original_figure"].touch()
            with self.assertRaises(FileExistsError):
                experiment.main(target=1, output_dir=directory, draw=True)


if __name__ == "__main__":
    unittest.main()
