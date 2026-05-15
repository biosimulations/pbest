import json
import os
import tempfile
from pathlib import Path
from typing import Any

import pytest
from bigraph_schema import Core

from pbest.cli.run_experiment import run_bundle
from pbest.cli.types import CLIExecutionProgramArguments
from pbest.execution.remote.bundle import _bundle_maker, batch_bundle_and_wait, bundle_and_wait
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
    num_experiments = 20
    submissions = [ExperimentSubmission(pbg=comparison_document, interval=0) for _ in range(num_experiments + 1)]

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


@pytest.mark.asyncio
async def test_remote_bundle(comparison_document: dict[Any, Any], fully_registered_core: Core) -> None:
    num_experiments = 20
    submissions = [ExperimentSubmission(pbg=comparison_document, interval=0) for _ in range(num_experiments + 1)]

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "remote_bundle_output"
        os.mkdir(output_dir)

        await bundle_and_wait(submissions, output_dir, seconds_to_wait=600, bundle_size=100)

        result_dirs = os.listdir(output_dir)
        assert len(result_dirs) > 0
        for result_dir in result_dirs:
            result_path = Path(output_dir) / result_dir
            result_files = os.listdir(result_path)
            assert len(result_files) == len(submissions)
            for result_file in result_files:
                _validate_experiment_output(result_path / result_file)


@pytest.mark.asyncio
async def test_remote_batch_bundle(comparison_document: dict[Any, Any], fully_registered_core: Core) -> None:
    num_experiments = 20
    submissions = [ExperimentSubmission(pbg=comparison_document, interval=0) for _ in range(num_experiments)]

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "remote_bundle_output"
        os.mkdir(output_dir)

        await batch_bundle_and_wait(submissions, output_dir, seconds_to_wait=600, bundle_size=10)

        result_dirs = os.listdir(output_dir)
        assert len(result_dirs) > 0
        for result_dir in result_dirs:
            result_path = Path(output_dir) / result_dir
            result_files = os.listdir(result_path)
            assert len(result_files) == 10
