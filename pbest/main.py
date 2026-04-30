from argparse import ArgumentParser

from pbest.cli.containerization_cli import cli_run_containerization
from pbest.cli.run_experiment import cli_run_experiment
from pbest.cli.parsing import run_experiment_parsing, containerization_parsing


def cli_tool():
    parser: ArgumentParser = ArgumentParser(
        prog="Process Bigraph Extensible Simulation Toolkit  (PBest)",
        description="""Everything required to run a process bigraph file, and containerize the environment used to run it.""",
    )
    sub_parsers = parser.add_subparsers(dest="command", required=True)

    run_parser = sub_parsers.add_parser(name="run", description="Run a process bigraph file.")
    run_experiment_parsing.add_args(run_parser)
    container_parser = sub_parsers.add_parser(name="containerize", description="Containerize your runtime environment.")
    containerization_parsing.add_args(container_parser)

    command = parser.parse_args().command
    if command == "run":
        cli_run_experiment(parser=parser)
    elif command == "containerize":
        cli_run_containerization(parser=parser)


if __name__ == "__main__":
    cli_tool()