import json
import math
import os
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import pytest

from pbest.main import run_remote_experiment
from pbest.utils.builder import CompositeBuilder
from pbest.utils.input_types import ExecutionProgramArguments
from tests.fixtures.utils import root_dir_path


def comparison_builder(builder: CompositeBuilder) -> None:
    model_path = f"{root_dir_path()}/resources/BIOMD0000000012_url.xml"
    builder.add_step(
        address="local:pbsim_common.simulators.tellurium_process.TelluriumUTCStep",
        config={
            "model_source": model_path,
            "time": 10,
            "n_points": 10,
        },
        inputs={"concentrations": ["species_concentrations"], "counts": ["species_counts"]},
        outputs={"result": ["results", "tellurium"]},
    )
    builder.add_step(
        address="local:pbsim_common.simulators.copasi_process.CopasiUTCStep",
        config={
            "model_source": model_path,
            "time": 10,
            "n_points": 10,
        },
        inputs={"concentrations": ["species_concentrations"], "counts": ["species_counts"]},
        outputs={"result": ["results", "copasi"]},
    )
    builder.add_comparison_step("copasi_tellurium", ["results"])


def test_comparison_example(fully_registered_builder: CompositeBuilder):
    comparison_builder(builder=fully_registered_builder)
    compare_composite = fully_registered_builder.build()
    comparisons = compare_composite.state["comparison_results"]["copasi_tellurium"]["species_mse"]
    for simulator_of_focus in comparisons:
        for key, value in comparisons[simulator_of_focus].items():
            if key == simulator_of_focus:
                assert value == 0
            else:
                assert value < 1e-6
                assert value != 0


def perform_parameter_scan_comparison(results: dict[Any, Any]):
    steady_state_values = [
        [
            240.8222635574016,
            240.8222635574016,
            240.8222635574016,
            2.408222635574016,
            2.408222635574016,
            2.408222635574016,
        ]
    ]
    jacboian_values = [
        [-0.06931471805599441, 0.0, 0.0, 6.931471805599392, 0.0, 0.0],
        [0.0, -0.06931471805599441, 0.0, 0.0, 6.931471805599392, 0.0],
        [0.0, 0.0, -0.06931471805599441, 0.0, 0.0, 6.931471805599392],
        [0.0, 0.0, -0.006502909960777793, -0.34657359027997203, 0.0, 0.0],
        [-0.006502909960777793, 0.0, 0.0, 0.0, -0.34657359027997203, 0.0],
        [0.0, -0.006502909960777793, 0.0, 0.0, 0.0, -0.34657359027997203],
    ]

    # Seems as if values don't change over parameter scan, cause for concern?
    for k in results:
        parameter_jacobian = results[k]["jacobian"]["values"]
        parameter_steady_state = results[k]["steady_state"]["values"][0]
        for i in range(len(parameter_jacobian)):
            for j in range(len(parameter_jacobian[i])):
                assert math.isclose(parameter_jacobian[i][j], jacboian_values[i][j], rel_tol=0, abs_tol=1e-10)

        for j in range(len(parameter_steady_state)):
            assert math.isclose(parameter_steady_state[j], steady_state_values[0][j], rel_tol=0, abs_tol=1e-10)


def create_parameter_scan(
    fully_registered_builder: CompositeBuilder,
    model_path: str = f"{root_dir_path()}/resources/BIOMD0000000012_url.xml",
) -> None:
    fully_registered_builder.add_parameter_scan(
        step_address="local:pbsim_common.simulators.tellurium_process.TelluriumSteadyStateStep",
        step_config={"model_source": model_path},
        input_mappings={"species_concentrations": ["species_concentrations"]},
        config_values={},
        state_values={"species_concentrations": {"PX": [1, 30000], "PY": [1, 2000], "PZ": [1, 5000]}},
    )


def test_parameter_scan(fully_registered_builder: CompositeBuilder):
    create_parameter_scan(fully_registered_builder)
    comp = fully_registered_builder.build()
    perform_parameter_scan_comparison(comp.state["parameter_scan_0"]["results"])


@pytest.mark.asyncio
async def test_remote_parameter_scan(fully_registered_builder: CompositeBuilder):
    create_parameter_scan(fully_registered_builder, model_path="biomodel.xml")
    with tempfile.TemporaryDirectory() as temp_dir:
        input_path = os.path.join(temp_dir, "input.pbg")
        model_path = f"{root_dir_path()}/resources/BIOMD0000000012_url.xml"
        with open(input_path, "w") as input_file:
            json.dump({"state": fully_registered_builder.state}, input_file)
        omex_path = os.path.join(temp_dir, "input.omex")
        with zipfile.ZipFile(omex_path, "w") as omex_input:
            omex_input.write(input_path, arcname="input.pbg")
            omex_input.write(model_path, arcname="biomodel.xml")

        await run_remote_experiment(
            prog_args=ExecutionProgramArguments(input_file_path=omex_path, interval=1, output_directory=Path(temp_dir))
        )

        with zipfile.ZipFile(os.path.join(temp_dir, "output.zip")) as output:
            output.extractall(temp_dir)

        result_pbg = next(k for k in os.listdir(temp_dir) if ".pbg" in k)

        with open(os.path.join(temp_dir, result_pbg)) as result_file:
            json_data = json.load(result_file)
            perform_parameter_scan_comparison(json_data["state"]["parameter_scan_0"]["results"])
