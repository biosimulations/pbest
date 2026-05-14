import json
import logging
import os
import tempfile
import zipfile
from argparse import ArgumentParser
from pathlib import Path
from typing import Any

import pbest.cli.parsing.run_experiment_parsing as cli_parsing
from pbest.cli.types import CLIExecutionProgramArguments
from pbest.execution.local import run_experiment
from pbest.globals import set_logging_config
from pbest.utils.input_types import ExperimentSubmission

logger = logging.getLogger(__name__)


def get_pb_schema_from_omex(omex_file: Path, working_dir: str) -> dict[Any, Any]:
    pbg_file: str | None = None
    with zipfile.ZipFile(omex_file, "r") as zf:
        zf.extractall(working_dir)
    for file_name in os.listdir(working_dir):
        if not (file_name.endswith(".pbg") or file_name.endswith(".json")):
            continue
        pbg_file = os.path.join(working_dir, file_name)
        break

    if pbg_file is None:
        err = f"Could not find any PBG or JSON file in or at `{omex_file}`."
        raise FileNotFoundError(err)
    with open(pbg_file) as input_data:
        json_string = input_data.read()
        for other_file in os.listdir(working_dir):
            if not other_file.endswith(".pbg") or not other_file.endswith(".json"):
                json_string = json_string.replace(other_file, os.path.join(working_dir, other_file))
        result: dict[Any, Any] = json.loads(json_string)
        return result


def _is_bundle(omex_file: Path) -> bool:
    with zipfile.ZipFile(omex_file, "r") as zf:
        res = True
        for file_name in zf.namelist():
            res = res and file_name.endswith(".omex")
    return res


def run_bundle(program_arguments: CLIExecutionProgramArguments, tmp_dir: str) -> None:
    logger.info("Running Bundle...")
    with zipfile.ZipFile(program_arguments.file_path, "r") as zf:
        zf.extractall(tmp_dir)
        dir_list = os.listdir(tmp_dir)
        for i in range(len(dir_list)):
            try:
                logger.info(f"Processing {dir_list[i]}")
                path_file_name = Path(os.path.join(tmp_dir, dir_list[i]))
                pbg = get_pb_schema_from_omex(path_file_name, os.path.join(tmp_dir, str(i)))
                run_experiment(
                    ExperimentSubmission(pbg=pbg, interval=program_arguments.interval),
                    program_arguments.output_directory / str(i),
                )
            except Exception as e:
                logger.error(msg=f"Failed to run: {pbg}.", exc_info=e)


def cli_run_experiment(parser: ArgumentParser) -> None:
    log_level = os.getenv("LOGGER_LEVEL", "INFO")
    set_logging_config(log_level)

    logger.info("Starting execution...")
    program_arguments = cli_parsing.parse_run_args(parser=parser)
    logger.info("Got Program Arguments: " + str(program_arguments))

    pbg: Path | dict = program_arguments.file_path
    with tempfile.TemporaryDirectory() as tmp_dir:
        if isinstance(pbg, Path) and _is_bundle(pbg):
            run_bundle(program_arguments, tmp_dir)
        else:
            if program_arguments.file_path.suffix == ".omex":
                pbg = get_pb_schema_from_omex(program_arguments.file_path, tmp_dir)
            elif program_arguments.file_path.suffix != ".pbg":
                msg = f"Expected either .omex or .pbg. Instead got: {program_arguments.file_path}"
                raise ValueError(msg)
            run_experiment(
                ExperimentSubmission(pbg=pbg, interval=program_arguments.interval), program_arguments.output_directory
            )

    logger.info("Finished executing experiment.")
