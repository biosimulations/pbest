import os

import compose_api_client
from compose_api_client import Client
from compose_api_client.models import SimulationExperiment
from compose_api_client.types import File
from compose_api_client.utils import run_simulation_and_wait

from pbest.utils.input_types import ExecutionProgramArguments


async def run_remote_experiment(
    prog_args: ExecutionProgramArguments, client: Client | None = None
) -> SimulationExperiment:
    if client is None:
        client = compose_api_client.Client(base_url="https://compose.cam.uchc.edu")

    extension = prog_args.input_file_path.rsplit(".", maxsplit=1)[-1]
    if extension not in ["json", "omex", "pbg", "sbml"]:
        err_msg = f"File extension {extension} not supported."
        raise ValueError(err_msg)

    with open(prog_args.input_file_path, "rb") as input_file:
        sent_file = File(file_name=f"experiment.{extension}", payload=input_file)
        result, sim_id = await run_simulation_and_wait.async_call(
            experiment_file=sent_file, interval=prog_args.interval, client=client
        )

    with open(os.path.join(prog_args.output_directory, "output.zip"), "wb") as output_file:
        output_file.write(result.content)

    return sim_id

