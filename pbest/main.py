import json
import logging
import os
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import pbest.execution.cli_parsing as cli_parsing
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

if __name__ == "__main__":
    log_level = os.getenv("LOGGER_LEVEL", "INFO")
    set_logging_config(log_level)

    logger.info("Starting execution...")
    program_arguments = cli_parsing.get_program_env_variables()
    if program_arguments is None:
        program_arguments = cli_parsing.get_program_arguments()
    logger.info("Got Program Arguments: " + str(program_arguments))

    pbg = program_arguments.file_path
    if program_arguments.file_path.suffix == ".omex":
        with tempfile.TemporaryDirectory() as tmp_dir:
            pbg = get_pb_schema_from_omex(program_arguments.file_path, tmp_dir)
    elif program_arguments.file_path.suffix != ".pbg":
        raise ValueError(f"Expected either .omex or .pbg. Instead got: {program_arguments.file_path}")
    run_experiment(ExperimentSubmission(pbg=pbg, interval=program_arguments.interval), program_arguments.output_directory)
    logger.info("Finished executing experiment.")
