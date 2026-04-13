import logging
import os
import tempfile

import pbest.execution.cli_parsing as cli_parsing
from pbest.execution.local import run_experiment, get_pb_schema_from_omex
from pbest.globals import set_logging_config
from pbest.utils.input_types import ExperimentSubmission

logger = logging.getLogger(__name__)


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
