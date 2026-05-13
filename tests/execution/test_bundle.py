import json
import os
import tempfile
from pathlib import Path
from typing import Any

from bigraph_schema import Core

from pbest.cli.run_experiment import run_bundle
from pbest.cli.types import CLIExecutionProgramArguments
from pbest.execution.remote.bundle import _bundle_maker
from pbest.utils.input_types import ExperimentSubmission


def _validate_experiment_output(output_dir: Path) -> None:
    result: dict[Any, Any] | None = None
    for file_name in os.listdir(output_dir):
        if file_name.endswith(".pbg"):
            with open(output_dir / file_name) as file:
                result = json.load(file)
            break

    assert result is not None
    comparison_result: dict[str, dict[str, float]] = result["state"]["comparison_result"]["species_mse"]
    for key in comparison_result:
        for compared_to in comparison_result[key]:
            if compared_to == key:
                assert float(comparison_result[key][compared_to]) == 0
            else:
                assert float(comparison_result[key][compared_to]) < 1.05e-6
                assert float(comparison_result[key][compared_to]) != 0


def test_run_bundle(comparison_document: dict[Any, Any], fully_registered_core: Core) -> None:
    num_experiments = 3
    submissions = [
        ExperimentSubmission(pbg=comparison_document, interval=0)
        for _ in range(num_experiments + 1)
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        bundle_path = _bundle_maker(submissions, 0, num_experiments, tmpdir)

        output_dir = Path(tmpdir) / "bundle_output"
        os.mkdir(output_dir)
        program_arguments = CLIExecutionProgramArguments(
            file_path=bundle_path,
            interval=0,
            output_directory=output_dir,
        )

        with tempfile.TemporaryDirectory() as run_tmpdir:
            run_bundle(program_arguments, run_tmpdir)

        for i in range(num_experiments):
            _validate_experiment_output(output_dir / str(i))
