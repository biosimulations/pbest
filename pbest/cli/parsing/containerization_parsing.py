import os
import sys
from argparse import ArgumentParser, Namespace

from pbest.cli.types import CLIContainerizationProgramArguments
from pbest.utils.input_types import ContainerizationEngine


def add_args(sub_arg_parser: ArgumentParser) -> None:
    sub_arg_parser.add_argument("-i", "--input_file_path", type=str, default="", required=False)  # positional argument
    sub_arg_parser.add_argument(
        "-t",
        "--target-containerization",
        choices=["docker", "apptainer", "singularity", "both"],
        help="if containerization is specified, selects whether to containerize with `docker` or `apptainer` (formerly Singularity CE)",
        default="docker",
    )
    sub_arg_parser.add_argument(
        "-o",
        "--output_directory",
        nargs="?",
        const=".",
        help="specifies output directory; if not provided, no output file will be generated, but validation (and containerization if requested) will occur.",
        default="",
    )
    sub_arg_parser.add_argument("-v", "--verbose", action="store_true")


def parse_container_args(parser: ArgumentParser) -> CLIContainerizationProgramArguments:
    args = parser.parse_args()
    if args.output_directory is not None:
        args.output_directory = os.path.abspath(os.path.expanduser(args.output_directory))
        if not os.path.exists(args.output_directory) or not (
            os.path.isdir(args.output_directory) or os.path.islink(args.output_directory)
        ):
            parser.print_help()
            print("`output_directory` must be a directory that exists!", file=sys.stderr)
            sys.exit(12)
    else:
        args.output_directory = args.input_file_path.parent

    containerization_engine = _determine_containerization(args)
    return CLIContainerizationProgramArguments(
        input=args.input_file_path,
        output_directory=args.output_directory,
        containerization_engine=containerization_engine,
    )


def _determine_containerization(args: Namespace) -> ContainerizationEngine:
    if args.target_containerization == "docker":
        containerization_engine = ContainerizationEngine.DOCKER
    elif args.target_containerization == "apptainer" or args.target_containerization == "singularity":
        containerization_engine = ContainerizationEngine.APPTAINER
    elif args.target_containerization == "both":
        containerization_engine = ContainerizationEngine.BOTH
    else:
        print("error: `target-containerization` must be `docker`, `apptainer`, or `both.", file=sys.stderr)
        sys.exit(15)
    return containerization_engine
