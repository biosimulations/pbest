import asyncio
import copy
import datetime
import json
import os
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import compose_api_client
from compose_api_client.api.results import get_simulation_results_file, get_simulations_status_batch
from compose_api_client.api.simulation import run_simulation
from compose_api_client.models import BodyRunSimulation, HpcRun, JobStatus, SimulationExperiment
from compose_api_client.types import File
from compose_api_client.utils import run_simulation_and_wait
from httpx import Client


def _default_client() -> compose_api_client.client.Client:
    return compose_api_client.client.Client(base_url="https://compose.cam.uchc.edu")


def _normalize_pbg_paths(pbg: Path | dict[str, Any], tmp_dir: str) -> Path:
    new_pbg: dict
    if isinstance(pbg, Path) and pbg.suffix == ".pbg":
        with open(pbg) as input_file:
            new_pbg = json.load(input_file)
    elif isinstance(pbg, dict):
        new_pbg = copy.deepcopy(pbg)
    else:
        err_msg = f"PBG must be a .pbg file or a dict, instead got: {pbg}"
        raise TypeError(err_msg)

    exploration_set: list[dict] = [new_pbg]
    new_omex = Path(tmp_dir) / "experiment.omex"
    with zipfile.ZipFile(new_omex, "w") as zip_file:
        while len(exploration_set) != 0:
            sub_dict = exploration_set.pop()
            for k, v in sub_dict.items():
                if isinstance(v, dict):
                    exploration_set.append(v)
                elif isinstance(v, str) and Path(v).is_file():
                    og_file = Path(v)
                    new_name = og_file.name
                    sub_dict[k] = new_name
                    if new_name not in zip_file.namelist():
                        zip_file.write(og_file, new_name)

        update_pbg_path = Path(tmp_dir) / "updated.pbg"
        with open(update_pbg_path, "w") as input_pbg:
            json.dump(new_pbg, input_pbg)
        zip_file.write(update_pbg_path, "updated.pbg")

    return new_omex


async def get_simulation_status(simulations: list[SimulationExperiment] | list[int], client: Client | None = None) -> list[HpcRun]:
    if client is None:
        client = _default_client()
    if len(simulations) !=0 and isinstance(simulations[0], SimulationExperiment):
        simulations: list[int] = [i.simulation_database_id for i in simulations]
    response = await get_simulations_status_batch.asyncio_detailed(client=client, body=simulations)
    if response.status_code != 200:
        err_msg = f"Error when attempting to get simulation status: {response}"
        raise RuntimeError(err_msg)
    result: list[HpcRun] = response.parsed
    return result


async def run_remote_experiment(
    pbg: Path | dict, interval: float, client: Client | None = None
) -> SimulationExperiment:
    if client is None:
        client = compose_api_client.Client(base_url="https://compose.cam.uchc.edu")

    with tempfile.TemporaryDirectory() as tmp_dir:
        omex_file = _normalize_pbg_paths(pbg, tmp_dir)
        with open(omex_file, "rb") as input_file:
            sent_file = File(file_name="experiment.omex", payload=input_file)
            body = BodyRunSimulation(uploaded_file=sent_file)
            response = await run_simulation.asyncio_detailed(client=client, body=body, interval_time=interval)
            if response.status_code != 200:
                err_msg = f"Error when attempting to submit simulation: {response}"
                raise RuntimeError(err_msg)

        return response.parsed


async def batch_run_remote_experiment(
    all_pbgs: list[Path] | list[dict], all_intervals: list[float], client: Client | None = None
) -> list[SimulationExperiment]:
    if client is None:
        client = _default_client()
    result: list[SimulationExperiment] = []
    for i in range(len(all_pbgs)):
        result.append(await run_remote_experiment(all_pbgs[i], all_intervals[i], client))
    return result


async def run_remote_experiment_and_wait(
    pbg: Path | dict, interval: float, output_dir: Path, client: Client | None = None
) -> SimulationExperiment:
    if client is None:
        client = _default_client()

    with tempfile.TemporaryDirectory() as tmp_dir:
        omex_file = _normalize_pbg_paths(pbg, tmp_dir)

        with open(omex_file, "rb") as input_file:
            sent_file = File(file_name="experiment.omex", payload=input_file)
            result, sim_id = await run_simulation_and_wait.async_call(
                experiment_file=sent_file, interval=interval, client=client
            )

        output_name = output_dir / f"experiment_result_{datetime.datetime.now()}.zip"
        with open(os.path.join(output_dir, output_name), "wb") as output_file:
            output_file.write(result.content)

        return sim_id


def print_statuses(hpc_runs: list[HpcRun | None], completed_runs: list[HpcRun], incomplete_runs: list[HpcRun],
                   ids_to_check: list[int]) -> None:
    incomplete_statuses = {
        JobStatus.FAILED,
        JobStatus.CANCELLED,
        JobStatus.TIMEOUT,
        JobStatus.OUT_OF_MEMORY,
    }
    for run in hpc_runs:
        if run is None:
            pass
        elif run.status == JobStatus.COMPLETED:
            completed_runs.append(run)
            hpc_runs.remove(run)
            ids_to_check.remove(run.sim_id)
        elif run.status in incomplete_statuses:
            print(f"!-- Run for sim {run.sim_id} is incomplete with state {run.status} --!")
            incomplete_runs.append(run)
            hpc_runs.remove(run)
            ids_to_check.remove(run.sim_id)
        else:
            print(f"#-- Run for sim id {run.sim_id} is in state: {run.status} --#")
    print("----------------------------------------------------")
    for run in completed_runs:
        print(f"+ Completed run {run.sim_id} +")


def print_summary(hpc_runs: list[HpcRun | None], completed_runs: list[HpcRun], incomplete_runs: list[HpcRun]) -> None:
    print("##############################\n# Summary #\n##############################")
    if len(hpc_runs) != 0:
        print("----- Simulations that are still running -----")
        for run in hpc_runs:
            if run is not None:
                print(f"Simulation {run.sim_id} still running with state {run.status}")
    if len(incomplete_runs) != 0:
        print("----- Simulations that failed to complete -----")
        for run in incomplete_runs:
            print(f"Simulation {run.sim_id} failed with state {run.status} at date {run.end_time}")
    if len(completed_runs) != 0:
        print("----- Simulations that completed -----")
        for run in completed_runs:
            print(f"Simulation {run.sim_id} completed at date {run.end_time}.")


async def batch_run_remote_experiment_and_wait(
    all_pbgs: list[Path] | list[dict], all_intervals: list[float], output_dir: Path, client: Client | None = None
) -> list[SimulationExperiment]:
    if client is None:
        client = _default_client()
    simulation_experiments: list[SimulationExperiment] = await batch_run_remote_experiment(
        all_pbgs, all_intervals, client
    )
    ids_to_check: list[int] = [i.simulation_database_id for i in simulation_experiments]

    running_experiments: list[SimulationExperiment] = []
    num_loops = 0
    sleep_interval = 2
    while len(running_experiments) == 0 and num_loops < 10:
        running_experiments = await get_simulation_status(simulations=ids_to_check, client=client)
        await asyncio.sleep(sleep_interval)
        num_loops += 1
    completed_experiments: list[HpcRun] = []
    incomplete_experiments: list[HpcRun] = []

    num_loops = 0
    seconds_to_wait = 600
    loops_to_wait = seconds_to_wait / sleep_interval

    while len(running_experiments) != 0 and num_loops < loops_to_wait:
        await asyncio.sleep(sleep_interval)
        running_experiments = await get_simulation_status(simulations=ids_to_check, client=client)
        print_statuses(
            hpc_runs=running_experiments, completed_runs=completed_experiments, incomplete_runs=incomplete_experiments,
            ids_to_check=ids_to_check
        )
        num_loops += 1
        print(f"{sleep_interval * num_loops} seconds have passed.")

    print_summary(
        hpc_runs=running_experiments, completed_runs=completed_experiments, incomplete_runs=incomplete_experiments
    )
    print(f"Saving completed simulation results to specified directory: {output_dir}")
    for run in completed_experiments:
        result = await get_simulation_results_file.asyncio_detailed(client=client, simulation_id=run.sim_id)
        output_name = output_dir / f"sim_{run.sim_id}_experiment_result_{datetime.datetime.now()}.zip"
        with open(os.path.join(output_dir, output_name), "wb") as output_file:
            output_file.write(result.content)

    return completed_experiments
