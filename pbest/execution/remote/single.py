import datetime
import os
import tempfile
import zipfile
from pathlib import Path

import compose_api_client
from compose_api_client.api.simulation import run_simulation
from compose_api_client.models import BodyRunSimulation, SimulationExperiment
from compose_api_client.types import File
from compose_api_client.utils import run_simulation_and_wait
from httpx import Client

from pbest.execution.remote.utils import _default_client, _normalize_pbg_paths
from pbest.utils.input_types import ExperimentSubmission

async def _run_remote_helper(submission: ExperimentSubmission, client: Client, is_batch: bool = False) -> SimulationExperiment:
    with tempfile.TemporaryDirectory() as tmp_dir:
        omex_file = _normalize_pbg_paths(submission.pbg, tmp_dir)
        with open(omex_file, "rb") as input_file:
            sent_file = File(file_name="experiment.omex", payload=input_file)
            body = BodyRunSimulation(uploaded_file=sent_file)
            response = await run_simulation.asyncio_detailed(
                client=client, body=body, interval_time=submission.interval, batch_submission=is_batch
            )
            if response.status_code != 200:
                err_msg = f"Error when attempting to submit simulation: {response}"
                raise RuntimeError(err_msg)

        return response.parsed

async def run_remote_experiment(submission: ExperimentSubmission, client: Client | None = None) -> SimulationExperiment:
    if client is None:
        client = compose_api_client.Client(base_url="https://compose.cam.uchc.edu")
    return await _run_remote_helper(submission, client)

async def run_remote_experiment_and_wait(
    submission: ExperimentSubmission, output_dir: Path, client: Client | None = None
) -> SimulationExperiment:
    if client is None:
        client = _default_client()

    with tempfile.TemporaryDirectory() as tmp_dir:
        omex_file = _normalize_pbg_paths(submission.pbg, tmp_dir)

        with open(omex_file, "rb") as input_file:
            sent_file = File(file_name="experiment.omex", payload=input_file)
            result, sim_id = await run_simulation_and_wait.async_call(
                experiment_file=sent_file, interval=submission.interval, client=client
            )

        output_name = output_dir / f"experiment_result_{sim_id.simulation_database_id}_{datetime.date.today()}"
        zip_name = str(output_name) + ".zip"
        with open(os.path.join(output_dir, zip_name), "wb") as output_file:
            output_file.write(result.content)

        with zipfile.ZipFile(zip_name, "r") as zip_ref:
            os.makedirs(output_name, exist_ok=True)
            zip_ref.extractall(output_name)
            os.remove(zip_name)

        return sim_id
