import argparse
import logging
import os
import sys
from pathlib import Path

from pydantic.dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CLIExecutionProgramArguments:
    """
    Provide information required to execute a process bi-graph.
    """

    file_path: Path
    interval: float
    output_directory: Path


def get_program_arguments() -> CLIExecutionProgramArguments:
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
    input_file = Path(os.path.abspath(os.path.expanduser(args.input_file_path)))
    output_dir = (
        os.path.abspath(os.path.expanduser(args.output_directory))
        if args.output_directory is not None
        else os.path.dirname(input_file)
    )

    if not os.path.isfile(input_file):
        logger.error(
            f"`input_file_path`:{input_file}  must be a JSON/PBG file (or an archive containing one) that exists!"
        )
        sys.exit(11)
    return CLIExecutionProgramArguments(file_path=input_file, output_directory=Path(output_dir), interval=args.interval)


def get_program_env_variables() -> CLIExecutionProgramArguments | None:
    pb_input_path = os.getenv("PB_INPUT_FILE_PATH")
    output_dir = os.getenv("PB_OUTPUT_DIRECTORY")
    interval = os.getenv("PB_INTERVAL")
    if pb_input_path is None or output_dir is None or interval is None:
        return None
    return CLIExecutionProgramArguments(
        file_path=Path(pb_input_path),
        output_directory=Path(output_dir),
        interval=int(interval),
    )
