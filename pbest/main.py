import logging
import os

import pbest.execution.cli_parsing as cli_parsing
from pbest import run_experiment
from pbest.globals import set_logging_config

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    log_level = os.getenv("LOGGER_LEVEL", "INFO")
    set_logging_config(log_level)

    logger.info("Starting execution...")
    program_arguments = cli_parsing.get_program_env_variables()
    if program_arguments is None:
        program_arguments = cli_parsing.get_program_arguments()
    logger.info("Got Program Arguments: " + str(program_arguments))
    run_experiment(program_arguments)
    logger.info("Finished executing experiment.")
