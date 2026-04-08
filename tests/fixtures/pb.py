from pathlib import Path
from typing import Any

import pytest
from bigraph_schema.core import Core
from process_bigraph.emitter import emitter_from_wires

# from biocompose import standard_types
from pbest.globals import get_loaded_core
from pbest.utils.builder import CompositeBuilder


@pytest.fixture(scope="function")
def fully_registered_core() -> Core:
    return get_loaded_core()


@pytest.fixture(scope="function")
def fully_registered_builder(fully_registered_core) -> CompositeBuilder:
    return CompositeBuilder()


def _get_model_path() -> str:
    path = Path(__file__).parent.parent
    return f"{path}/resources/BIOMD0000000012_url.xml"


def get_default_config() -> dict[str, Any]:
    return {
        "name": "actin_membrane",
        "random_seed": 0,
    }


@pytest.fixture(scope="function")
def readdy_document() -> dict[str, Any]:
    emitters_from_wires = emitter_from_wires(
        {"particles": ["particles"], "topologies": ["topologies"], "global_time": ["global_time"]},
        address="local:pb_multiscale_actin.processes.simularium_emitter.SimulariumEmitter",
    )

    readd_pbg = {
        "emitter": emitters_from_wires,
        "readdy": {
            "_type": "process",
            "address": "local:pb_multiscale_actin.processes.readdy_actin_membrane.ReaddyActinMembrane",
            "config": get_default_config(),
            "inputs": {"particles": ["particles"], "topologies": ["topologies"]},
            "outputs": {"particles": ["particles"], "topologies": ["topologies"]},
        },
    }
    return {"state": readd_pbg}


@pytest.fixture(scope="function", autouse=True)
def comparison_document() -> dict[Any, Any]:
    model_path = _get_model_path()

    state = {
        # provide initial values to overwrite those in the configured model
        "species_concentrations": {},
        "species_counts": {},
        "comparison_result": {"species_mse": {}},
        "tellurium_step": {
            "_type": "step",
            "address": "local:pbsim_common.simulators.tellurium_process.TelluriumUTCStep",
            "config": {
                "model_source": model_path,
                "time": 10,
                "n_points": 10,
            },
            "inputs": {"concentrations": ["species_concentrations"], "counts": ["species_counts"]},
            "outputs": {
                "result": ["results", "tellurium"],
            },
        },
        "copasi_step": {
            "_type": "step",
            "address": "local:pbsim_common.simulators.copasi_process.CopasiUTCStep",
            "config": {
                "model_source": model_path,
                "time": 10,
                "n_points": 10,
            },
            "inputs": {"concentrations": ["species_concentrations"], "counts": ["species_counts"]},
            "outputs": {
                "result": ["results", "copasi"],
            },
        },
        "comparison": {
            "_type": "step",
            "address": "local:pbsim_common.comparison.MSEComparison",
            "config": {},
            "inputs": {
                "results": ["results"],
            },
            "outputs": {
                "comparison_result": ["comparison_result"],
            },
        },
    }

    document = {"state": state}
    return document
