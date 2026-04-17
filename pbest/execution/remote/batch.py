import asyncio
import datetime
import os
import zipfile
from pathlib import Path

from compose_api_client.api.results import get_simulation_results_file, get_simulations_status_batch
from compose_api_client.models import HpcRun, JobStatus, SimulationExperiment
from httpx import Client

from pbest.execution.remote.single import run_remote_experiment
from pbest.execution.remote.utils import _default_client
from pbest.utils.input_types import ExperimentSubmission


async def get_simulation_status(
    simulations: list[SimulationExperiment] | list[int], client: Client | None = None
) -> list[HpcRun]:
    if client is None:
        client = _default_client()
    sent_simulations = simulations.copy()
    if len(simulations) != 0 and isinstance(simulations[0], SimulationExperiment):
        sent_simulations = []
        for i in simulations:
            if isinstance(i, SimulationExperiment):
                sent_simulations.append(i.simulation_database_id)
            else:
                sent_simulations.append(i)
    response = await get_simulations_status_batch.asyncio_detailed(client=client, body=sent_simulations)
    if response.status_code != 200:
        err_msg = f"Error when attempting to get simulation status: {response}"
        raise RuntimeError(err_msg)
    result: list[HpcRun] = response.parsed
    return result


async def batch_run_remote_experiment(
    submissions: list[ExperimentSubmission], client: Client | None = None
) -> list[SimulationExperiment]:
    if client is None:
        client = _default_client()
    result: list[SimulationExperiment] = []
    for i in submissions:
        result.append(await run_remote_experiment(i, client))
    return result


def print_statuses(
    hpc_runs: list[HpcRun | None], completed_runs: list[HpcRun], incomplete_runs: list[HpcRun], ids_to_check: list[int]
) -> None:
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
    submissions: list[ExperimentSubmission], output_dir: Path, client: Client | None = None, seconds_to_wait: int = 600
) -> list[HpcRun]:
    if client is None:
        client = _default_client()
    simulation_experiments: list[SimulationExperiment] = await batch_run_remote_experiment(submissions, client)
    ids_to_check: list[int] = [i.simulation_database_id for i in simulation_experiments]

    running_experiments: list[HpcRun | None] = []
    num_loops = 0
    sleep_interval = 2
    loops_to_wait = seconds_to_wait / sleep_interval

    print("Waiting for simulations to be submitted to slurm...")
    while len(running_experiments) == 0 and num_loops < loops_to_wait:
        running_experiments = await get_simulation_status(simulations=ids_to_check, client=client)
        await asyncio.sleep(sleep_interval)
        num_loops += 1
        print(f"Waited for {num_loops * sleep_interval} seconds.")
    completed_experiments: list[HpcRun] = []
    incomplete_experiments: list[HpcRun] = []

    if len(running_experiments) == 0:
        err_msg = (
            f"After waiting for {seconds_to_wait} seconds for simulations to be submitted to slurm, "
            f"and none have been submitted.\nStopping current execution wait."
        )
        raise TimeoutError(err_msg)

    print("At least one simulation has been submitted. Now monitoring if simulations have completed.")
    num_loops = 0
    while len(running_experiments) != 0 and num_loops < loops_to_wait:
        await asyncio.sleep(sleep_interval)
        running_experiments = await get_simulation_status(simulations=ids_to_check, client=client)
        print_statuses(
            hpc_runs=running_experiments,
            completed_runs=completed_experiments,
            incomplete_runs=incomplete_experiments,
            ids_to_check=ids_to_check,
        )
        num_loops += 1
        print(f"{sleep_interval * num_loops} seconds have passed.")

    print_summary(
        hpc_runs=running_experiments, completed_runs=completed_experiments, incomplete_runs=incomplete_experiments
    )
    print(f"Saving completed simulation results to specified directory: {output_dir}")
    for run in completed_experiments:
        result = await get_simulation_results_file.asyncio_detailed(client=client, simulation_id=run.sim_id)
        output_name = output_dir / f"sim_{run.sim_id}_experiment_result_{datetime.datetime.now()}"
        zip_path = os.path.join(output_dir, f"{output_name}.zip")

        with open(zip_path, "wb") as output_file:
            output_file.write(result.content)
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            os.makedirs(output_dir / output_name, exist_ok=True)
            zip_ref.extractall(output_dir / output_name)
            os.remove(zip_path)

    return completed_experiments
