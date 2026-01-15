import os
from typing import Any

import pytest
from process_bigraph import ProcessTypes, generate_core
from process_bigraph.emitter import emitter_from_wires

# from biocompose import standard_types
from pbest import standard_types
from pbest.utils.builder import CompositeBuilder


@pytest.fixture(scope="function")
def fully_registered_core() -> ProcessTypes:
    core = generate_core()
    for k, i in standard_types.items():
        core.register(k, i)
    return core


@pytest.fixture(scope="function")
def fully_registered_builder(fully_registered_core) -> CompositeBuilder:
    return CompositeBuilder(core=fully_registered_core)


def _get_model_path() -> str:
    return f"{os.getcwd()}/tests/resources/BIOMD0000000012_url.xml"


def get_default_config() -> dict[str, Any]:
    return {
        "name": "actin_membrane",
        "internal_timestep": 0.1,  # ns
        "box_size": (150.0, 150.0, 150.0),  # nm
        "periodic_boundary": True,
        "reaction_distance": 1.0,  # nm
        "n_cpu": 4,
        "only_linear_actin_constraints": True,
        "reactions": True,
        "dimerize_rate": 1e-30,  # 1/ns
        "dimerize_reverse_rate": 1.4e-9,  # 1/ns
        "trimerize_rate": 2.1e-2,  # 1/ns
        "trimerize_reverse_rate": 1.4e-9,  # 1/ns
        "pointed_growth_ATP_rate": 2.4e-5,  # 1/ns
        "pointed_growth_ADP_rate": 2.95e-6,  # 1/ns
        "pointed_shrink_ATP_rate": 8.0e-10,  # 1/ns
        "pointed_shrink_ADP_rate": 3.0e-10,  # 1/ns
        "barbed_growth_ATP_rate": 1e30,  # 1/ns
        "barbed_growth_ADP_rate": 7.0e-5,  # 1/ns
        "nucleate_ATP_rate": 2.1e-2,  # 1/ns
        "nucleate_ADP_rate": 7.0e-5,  # 1/ns
        "barbed_shrink_ATP_rate": 1.4e-9,  # 1/ns
        "barbed_shrink_ADP_rate": 8.0e-9,  # 1/ns
        "arp_bind_ATP_rate": 2.1e-2,  # 1/ns
        "arp_bind_ADP_rate": 7.0e-5,  # 1/ns
        "arp_unbind_ATP_rate": 1.4e-9,  # 1/ns
        "arp_unbind_ADP_rate": 8.0e-9,  # 1/ns
        "barbed_growth_branch_ATP_rate": 2.1e-2,  # 1/ns
        "barbed_growth_branch_ADP_rate": 7.0e-5,  # 1/ns
        "debranching_ATP_rate": 1.4e-9,  # 1/ns
        "debranching_ADP_rate": 7.0e-5,  # 1/ns
        "cap_bind_rate": 2.1e-2,  # 1/ns
        "cap_unbind_rate": 1.4e-9,  # 1/ns
        "hydrolysis_actin_rate": 1e-30,  # 1/ns
        "hydrolysis_arp_rate": 3.5e-5,  # 1/ns
        "nucleotide_exchange_actin_rate": 1e-5,  # 1/ns
        "nucleotide_exchange_arp_rate": 1e-5,  # 1/ns
        "verbose": False,
        "use_box_actin": True,
        "use_box_arp": False,
        "use_box_cap": False,
        "obstacle_radius": 0.0,
        "obstacle_diff_coeff": 0.0,
        "use_box_obstacle": False,
        "position_obstacle_stride": 0,
        "displace_pointed_end_tangent": False,
        "displace_pointed_end_radial": False,
        "tangent_displacement_nm": 0.0,
        "radial_displacement_radius_nm": 0.0,
        "radial_displacement_angle_deg": 0.0,
        "longitudinal_bonds": True,
        "displace_stride": 1,
        "bonds_force_multiplier": 0.2,
        "angles_force_constant": 1000.0,
        "dihedrals_force_constant": 1000.0,
        "actin_constraints": True,
        "actin_box_center_x": 12.0,
        "actin_box_center_y": 0.0,
        "actin_box_center_z": 0.0,
        "actin_box_size_x": 20.0,
        "actin_box_size_y": 50.0,
        "actin_box_size_z": 50.0,
        "add_extra_box": False,
        "barbed_binding_site": True,
        "binding_site_reaction_distance": 3.0,
        "add_membrane": True,
        "membrane_center_x": 25.0,
        "membrane_center_y": 0.0,
        "membrane_center_z": 0.0,
        "membrane_size_x": 0.0,
        "membrane_size_y": 100.0,
        "membrane_size_z": 100.0,
        "membrane_particle_radius": 2.5,
        "obstacle_controlled_position_x": 0.0,
        "obstacle_controlled_position_y": 0.0,
        "obstacle_controlled_position_z": 0.0,
        "random_seed": 0,
    }


@pytest.fixture(scope="function")
def readdy_document() -> dict[str, Any]:
    emitters_from_wires = emitter_from_wires(
        {"particles": ["particles"], "topologies": ["topologies"], "global_time": ["global_time"]},
        address="local:pb_multiscale_actin.processes.readdy_actin_membrane.SimulariumEmitter",
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
    return readd_pbg


@pytest.fixture(scope="function", autouse=True)
def comparison_document() -> dict[Any, Any]:
    model_path = _get_model_path()

    state = {
        # provide initial values to overwrite those in the configured model
        "species_concentrations": {},
        "species_counts": {},
        "tellurium_step": {
            "_type": "step",
            "address": "local:pbest.registry.simulators.tellurium_process.TelluriumUTCStep",
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
            "address": "local:pbest.registry.simulators.copasi_process.CopasiUTCStep",
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
            "address": "local:pbest.registry.comparison.MSEComparison",
            "config": {},
            "inputs": {
                "results": ["results"],
            },
            "outputs": {
                "comparison_result": ["comparison_result"],
            },
        },
    }

    bridge = {"outputs": {"result": ["comparison_result"]}}

    document = {"state": state, "bridge": bridge}
    return document
