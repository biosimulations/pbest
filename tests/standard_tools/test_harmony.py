import json
import math
import os
import tempfile
from pathlib import Path
from typing import Any

import pytest

from pbest import run_remote_experiment_and_wait
from pbest.utils.builder import CompositeBuilder
from pbest.utils.input_types import ExperimentSubmission
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


def test_comparison_example(fully_registered_builder: CompositeBuilder, fully_registered_core):
    comparison_builder(builder=fully_registered_builder)
    compare_composite = fully_registered_builder.run_composite(core=fully_registered_core, interval=1)
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
        address="local:pbsim_common.simulators.tellurium_process.TelluriumSteadyStateStep",
        config={"model_source": model_path},
        input_mappings={"species_concentrations": ["species_concentrations"]},
        config_values={},
        state_values={"species_concentrations": {"PX": [1, 30000], "PY": [1, 2000], "PZ": [1, 5000]}},
    )


def test_parameter_scan(fully_registered_builder: CompositeBuilder, fully_registered_core):
    create_parameter_scan(fully_registered_builder)
    comp = fully_registered_builder.run_composite(core=fully_registered_core, interval=1)
    perform_parameter_scan_comparison(comp.state["parameter_scan_0"]["results"])


@pytest.mark.hpc
@pytest.mark.asyncio
async def test_remote_parameter_scan(fully_registered_builder: CompositeBuilder):
    model_path = f"{root_dir_path()}/resources/BIOMD0000000012_url.xml"
    create_parameter_scan(fully_registered_builder, model_path=model_path)
    with tempfile.TemporaryDirectory() as temp_dir:
        await run_remote_experiment_and_wait(
            ExperimentSubmission(pbg=fully_registered_builder.get_builder_state(), interval=0),
            Path(temp_dir),
            seconds_to_wait=30,
        )

        store_path = os.listdir(temp_dir)[0]
        result_pbg = next(k for k in os.listdir(os.path.join(temp_dir, store_path)) if "state" in k)

        with open(os.path.join(temp_dir, store_path, result_pbg)) as result_file:
            json_data = json.load(result_file)
            perform_parameter_scan_comparison(json_data["state"]["parameter_scan_0"]["results"])
