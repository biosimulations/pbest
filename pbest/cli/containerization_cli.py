import os.path
import sys
from argparse import ArgumentParser
from pathlib import Path

from pbest.cli.parsing.containerization_parsing import parse_container_args
from pbest.cli.types import CLIContainerizationProgramArguments
from pbest.containerization.container_constructor import generate_container_def_file, _default_experiment_deps
from pbest.utils.input_types import ExperimentPrimaryDependencies


def cli_run_containerization(parser: ArgumentParser) -> None:
    prog_args: CLIContainerizationProgramArguments = parse_container_args(parser=parser)
    try:
        dependencies: ExperimentPrimaryDependencies | Path = prog_args.input
        if dependencies == "":
            dependencies = _default_experiment_deps()

        container_file = generate_container_def_file(dependencies=dependencies, container_engine=prog_args.containerization_engine)
        container_path = os.path.join(prog_args.output_directory, str(prog_args.containerization_engine.name))
        if os.path.exists(container_path):
            k = 1
            next_path = container_path
            while k < 100000 and os.path.exists(next_path):
                next_path = container_path + f"_{k}"
                k += 1
            container_path = next_path

        with open(container_path, "w") as f:
            f.write(container_file.representation)
    except Exception as e:
        print(e, file=sys.stderr)
