import json
import os
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from bigraph_schema import Core

from pbest import run_experiment
from pbest.execution.local import _get_pb_schema_from_omex
from pbest.utils.input_types import ExperimentSubmission
from tests.fixtures.pb import _get_model_path


def _test(input_file: Path | dict, output_dir: Path) -> None:
    os.mkdir(output_dir)
    run_experiment(ExperimentSubmission(pbg=input_file, interval=0), output_directory=output_dir)

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


# Write a pbg that is used for comparison between Copasi and Tellurium, run it, and then check results
def test_run_experiment(comparison_document: dict[Any, Any], fully_registered_core: Core) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        pbg_file = Path(tmpdir) / "input.pbg"
        pbg_string = json.dumps(comparison_document)
        with open(pbg_file, "w") as file:
            file.write(pbg_string)
        _test(pbg_file, Path(tmpdir) / "pbg_output")


def test_run_experiment_omex(comparison_document: dict[Any, Any], fully_registered_core: Core) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        model_name = "BIOMD0000000012_url.xml"
        pbg_string = json.dumps(comparison_document).replace(_get_model_path(), model_name)
        pbg_relative = Path(tmpdir) / "relative.pbg"
        with open(pbg_relative, "w") as file:
            file.write(pbg_string)
        omex_file = Path(tmpdir) / "output.omex"
        with zipfile.ZipFile(omex_file, "w") as zip_ref:
            zip_ref.write(pbg_relative, "input.pbg")
            zip_ref.write(_get_model_path(), model_name)
        pbg = _get_pb_schema_from_omex(omex_file, tmpdir)
        _test(pbg, Path(tmpdir) / "omex_output")
