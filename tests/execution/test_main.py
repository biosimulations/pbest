import json
import os
import tempfile
from pathlib import Path
from typing import Any

from process_bigraph import Composite, ProcessTypes

from bsedic.main import run_experiment
from bsedic.utils.input_types import ExecutionProgramArguments


# Write a pbg that is used for comparison between Copasi and Tellurium, run it, and then check results
def test_run_experiment(comparison_document: dict[Any, Any], fully_registered_core: ProcessTypes) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        comp = Composite(config=comparison_document, core=fully_registered_core)
        comp.save(filename="input.pbif", outdir=tmpdir)

        os.mkdir(f"{tmpdir}/output")
        program_arguments = ExecutionProgramArguments(
            input_file_path=f"{tmpdir}/input.pbif", output_directory=Path(f"{tmpdir}/output"), interval=1
        )
        run_experiment(program_arguments)

        result: dict[Any, Any] | None = None
        for file_name in os.listdir(f"{tmpdir}/output"):
            if file_name.endswith(".pbg"):
                with open(f"{tmpdir}/output/{file_name}") as file:
                    result = json.load(file)
                break

    assert result is not None
    comparison_result: dict[str, dict[str, float]] = result["state"]["comparison_result"]["species_mse"]
    for key in comparison_result:
        for compared_to in comparison_result[key]:
            if compared_to == key:
                assert float(comparison_result[key][compared_to]) == 0
            else:
                assert float(comparison_result[key][compared_to]) < 1e-6
                assert float(comparison_result[key][compared_to]) != 0
