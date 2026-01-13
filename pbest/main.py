import argparse
import datetime
import json
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from process_bigraph import Composite, gather_emitter_results

from pbest.globals import get_loaded_core
from pbest.utils.input_types import ExecutionProgramArguments
import logging

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


def get_pb_schema(prog_args: ExecutionProgramArguments, working_dir: str) -> dict[Any, Any]:
    input_file: str | None = None
    if not (prog_args.input_file_path.endswith(".omex") or prog_args.input_file_path.endswith(".zip")):
        input_file = os.path.join(working_dir, os.path.basename(prog_args.input_file_path))
        shutil.copyfile(prog_args.input_file_path, input_file)
    else:
        with zipfile.ZipFile(prog_args.input_file_path, "r") as zf:
            zf.extractall(working_dir)
        for file_name in os.listdir(working_dir):
            if not (file_name.endswith(".pbif") or file_name.endswith(".json")):
                continue
            input_file = os.path.join(working_dir, file_name)
            break

    if input_file is None:
        err = f"Could not find any PBIF or JSON file in or at `{prog_args.input_file_path}`."
        raise FileNotFoundError(err)
    with open(input_file) as input_data:
        result: dict[Any, Any] = json.load(input_data)
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
        if len(query_results) != 0:
            emitter_results_file_path = os.path.join(prog_args.output_directory, f"results_{date}[{tz}#{time}].pber")
            with open(emitter_results_file_path, "w") as emitter_results_file:
                json.dump(query_results, emitter_results_file)
        prepared_composite.save(filename=f"state_{date}#{time}.pbg", outdir=tmp_dir)

        shutil.copytree(tmp_dir, prog_args.output_directory, dirs_exist_ok=True)

if __name__ == "__main__":
    logger.info("Starting execution...")
    program_arguments = get_program_env_variables()
    if program_arguments is None:
        program_arguments = get_program_arguments()
    logger.info("Got Program Arguments")
    run_experiment(program_arguments)
    logger.info("Finished executing experiment.")
