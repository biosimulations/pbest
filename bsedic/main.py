import argparse
import datetime
import json
import os
import shutil
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from typing import Any

from process_bigraph import Composite, gather_emitter_results

from bsedic.globals import get_loaded_core


@dataclass(frozen=True)
class PBProgramArguments:
    input_file: str
    output_dir: str
    interval: float
    verbose: bool


def get_program_arguments() -> PBProgramArguments:
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
    return PBProgramArguments(input_file, output_dir, args.interval, args.verbose)


def get_pb_schema(prog_args: PBProgramArguments, working_dir: str) -> dict[Any, Any]:
    input_file: str | None = None
    if not (prog_args.input_file.endswith(".omex") or prog_args.input_file.endswith(".zip")):
        input_file = os.path.join(working_dir, os.path.basename(prog_args.input_file))
        shutil.copyfile(prog_args.input_file, input_file)
    else:
        with zipfile.ZipFile(prog_args.input_file, "r") as zf:
            zf.extractall(working_dir)
        for file_name in os.listdir(working_dir):
            if not (file_name.endswith(".pbif") or file_name.endswith(".json")):
                continue
            input_file = os.path.join(working_dir, file_name)
            break

    if input_file is None:
        err = f"Could not find any PBIF or JSON file in or at `{prog_args.input_file}`."
        raise FileNotFoundError(err)
    with open(input_file) as input_data:
        return json.load(input_data)


def run_experiment(prog_args: PBProgramArguments = None) -> None:
    if prog_args is None:
        prog_args = get_program_arguments()

    with tempfile.TemporaryDirectory() as tmp_dir:
        schema = get_pb_schema(prog_args, tmp_dir)
        core = get_loaded_core()
        prepared_composite = Composite(core=core, config=schema)

        prepared_composite.run(prog_args.interval)
        query_results = gather_emitter_results(prepared_composite)

        current_dt = datetime.datetime.now()
        date, tz, time = str(current_dt.date()), str(current_dt.tzinfo), str(current_dt.time()).replace(":", "-")
        if len(query_results) != 0:
            emitter_results_file_path = os.path.join(prog_args.output_dir, f"results_{date}[{tz}#{time}].pber")
            with open(emitter_results_file_path, "w") as emitter_results_file:
                json.dump(query_results, emitter_results_file)
        prepared_composite.save(filename=f"state_{date}#{time}.pbg", outdir=tmp_dir)

        shutil.copytree(tmp_dir, prog_args.output_dir, dirs_exist_ok=True)


if __name__ == "__main__":
    run_experiment()
