import logging
import os
import sys
from argparse import ArgumentParser
from pathlib import Path

from pbest.cli.types import CLIExecutionProgramArguments

logger = logging.getLogger(__name__)

def add_args(sub_arg_parser: ArgumentParser) -> None:
    sub_arg_parser.add_argument("input_file_path")  # positional argument
    sub_arg_parser.add_argument("-o", "--output-directory", type=str)
    sub_arg_parser.add_argument("-n", "--interval", default=1.0, type=float)
    sub_arg_parser.add_argument("-v", "--verbose", action="store_true")


def parse_run_args(parser: ArgumentParser) -> CLIExecutionProgramArguments:
    print(parser)
    args = parser.parse_args()
    print(args)
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
