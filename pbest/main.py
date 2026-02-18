import argparse
import datetime
import json
import logging
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import compose_api_client
from compose_api_client.api.simulation import run_simulation_and_wait
from compose_api_client.models import SimulationExperiment
from compose_api_client.types import File
from httpx import Client
from process_bigraph import Composite, gather_emitter_results

from pbest.globals import get_loaded_core, set_logging_config
from pbest.utils.input_types import ExecutionProgramArguments

logger = logging.getLogger(__name__)


def get_program_arguments() -> ExecutionProgramArguments:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        prog="BioSimulators Experiment Wrapper (BSew)",
        description="""BSew is a BioSimulators project designed to serve as a template/wrapper for
running Process Bigraph Experiments.""",
    )
    parser.add_argument("input_file_path")  # positional argument
    parser.add_argument("-o", "--output-directory", type=str)
    parser.add_argument("-n", "--interval", default=1.0, type=float)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    input_file = os.path.abspath(os.path.expanduser(args.input_file_path))
    output_dir = (
        os.path.abspath(os.path.expanduser(args.output_directory))
        if args.output_directory is not None
        else os.path.dirname(input_file)
    )

    if not os.path.isfile(input_file):
        print(
            "error: `input_file_path` must be a JSON/PBIF file (or an archive containing one) that exists!",
            file=sys.stderr,
        )
        sys.exit(11)
    return ExecutionProgramArguments(
        input_file_path=input_file, output_directory=Path(output_dir), interval=args.interval
    )


def get_program_env_variables() -> ExecutionProgramArguments | None:
    pb_input_path = os.getenv("PB_INPUT_FILE_PATH")
    output_dir = os.getenv("PB_OUTPUT_DIRECTORY")
    interval = os.getenv("PB_INTERVAL")
    if pb_input_path is None or output_dir is None or interval is None:
        return None
    return ExecutionProgramArguments(
        input_file_path=pb_input_path,
        output_directory=Path(output_dir),
        interval=int(interval),
    )


def replace_relative_pbif_paths(dic: dict[Any, Any], root_dir: str) -> None:
    for k, v in dic.items():
        if isinstance(v, dict):
            replace_relative_pbif_paths(v, root_dir)
        elif k == "model_source" or k == "output_dir":
            dic[k] = os.path.join(root_dir, v)


def get_pb_schema(prog_args: ExecutionProgramArguments, working_dir: str) -> dict[Any, Any]:
    input_file: str | None = None
    is_omex = prog_args.input_file_path.endswith(".omex") or prog_args.input_file_path.endswith(".zip")
    if not is_omex:
        input_file = os.path.join(working_dir, os.path.basename(prog_args.input_file_path))
        shutil.copyfile(prog_args.input_file_path, input_file)
    else:
        with zipfile.ZipFile(prog_args.input_file_path, "r") as zf:
            zf.extractall(working_dir)
        for file_name in os.listdir(working_dir):
            if not (file_name.endswith(".pbg") or file_name.endswith(".json")):
                continue
            input_file = os.path.join(working_dir, file_name)
            break

    if input_file is None:
        err = f"Could not find any PBG or JSON file in or at `{prog_args.input_file_path}`."
        raise FileNotFoundError(err)
    with open(input_file) as input_data:
        result: dict[Any, Any] = json.load(input_data)
        if is_omex:
            replace_relative_pbif_paths(result, working_dir)
        return result


def run_experiment(prog_args: ExecutionProgramArguments) -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        schema = get_pb_schema(prog_args, tmp_dir)
        core = get_loaded_core()
        prepared_composite = Composite(core=core, config=schema)

        prepared_composite.run(prog_args.interval)
        query_results = gather_emitter_results(prepared_composite)

        current_dt = datetime.datetime.now()
        date, tz, time = str(current_dt.date()), str(current_dt.tzinfo), str(current_dt.time()).replace(":", "-")

        try:
            if len(query_results) != 0:
                emitter_results_file_path = os.path.join(
                    prog_args.output_directory, f"results_{date}[{tz}#{time}].pber"
                )
                with open(emitter_results_file_path, "w") as emitter_results_file:
                    json.dump(query_results, emitter_results_file)
        except TypeError as e:
            err_msg = f"Tried to save query results to {emitter_results_file_path}: {e}"
            logger.exception(err_msg)

        prepared_composite.save(filename=f"state_{date}#{time}.pbg", outdir=tmp_dir)

        logger.debug(
            f"Copying tmpdir contents [{os.listdir(tmp_dir)}] to output directory {prog_args.output_directory}"
        )
        shutil.copytree(tmp_dir, prog_args.output_directory, dirs_exist_ok=True)
        logger.debug(f"Contents copied to output directory [{os.listdir(prog_args.output_directory)}]")


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
        result, sim_id = await run_simulation_and_wait.async_call(experiment_file=sent_file, client=client)

    with open(os.path.join(prog_args.output_directory, "output.zip"), "wb") as output_file:
        output_file.write(result.content)

    return sim_id


if __name__ == "__main__":
    log_level = os.getenv("LOGGER_LEVEL", "INFO")
    set_logging_config(log_level)

    logger.info("Starting execution...")
    program_arguments = get_program_env_variables()
    if program_arguments is None:
        program_arguments = get_program_arguments()
    logger.info("Got Program Arguments: " + str(program_arguments))
    run_experiment(program_arguments)
    logger.info("Finished executing experiment.")
