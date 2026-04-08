import datetime
import json
import logging
import os
import shutil
import tempfile
import zipfile
from typing import Any

from process_bigraph import Composite, gather_emitter_results

from pbest.globals import get_loaded_core
from pbest.utils.input_types import ExecutionProgramArguments

logger = logging.getLogger(__name__)


def replace_relative_pbif_paths(dic: dict[Any, Any], root_dir: str) -> None:
    for k, v in dic.items():
        if isinstance(v, dict):
            replace_relative_pbif_paths(v, root_dir)
        elif k == "model_source" or k == "output_dir":
            dic[k] = os.path.join(root_dir, v)


def get_pb_schema(prog_args: ExecutionProgramArguments, working_dir: str) -> dict[Any, Any]:
    input_file: str | None = None
    is_omex = prog_args.input_file_path.endswith(".omex") or prog_args.input_file_path.endswith(".zip")
    if not is_omex:
        input_file = os.path.join(working_dir, os.path.basename(prog_args.input_file_path))
        shutil.copyfile(prog_args.input_file_path, input_file)
    else:
        with zipfile.ZipFile(prog_args.input_file_path, "r") as zf:
            zf.extractall(working_dir)
        for file_name in os.listdir(working_dir):
            if not (file_name.endswith(".pbg") or file_name.endswith(".json")):
                continue
            input_file = os.path.join(working_dir, file_name)
            break

    if input_file is None:
        err = f"Could not find any PBG or JSON file in or at `{prog_args.input_file_path}`."
        raise FileNotFoundError(err)
    with open(input_file) as input_data:
        result: dict[Any, Any] = json.load(input_data)
        if is_omex:
            replace_relative_pbif_paths(result, working_dir)
        return result


def run_experiment(prog_args: ExecutionProgramArguments) -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        schema = get_pb_schema(prog_args, tmp_dir)
        logger.debug(f"PBG schema: {schema}")
        core = get_loaded_core()
        prepared_composite = Composite(core=core, config=schema)

        prepared_composite.run(prog_args.interval)
        query_results = gather_emitter_results(prepared_composite)

        current_dt = datetime.datetime.now()
        date, tz, time = str(current_dt.date()), str(current_dt.tzinfo), str(current_dt.time()).replace(":", "-")

        try:
            if len(query_results) != 0:
                emitter_results_file_path = os.path.join(
                    prog_args.output_directory, f"results_{date}[{tz}#{time}].pber"
                )
                with open(emitter_results_file_path, "w") as emitter_results_file:
                    json.dump(query_results, emitter_results_file)
        except TypeError as e:
            err_msg = f"Tried to save query results to {emitter_results_file_path}: {e}"
            logger.exception(err_msg)

        prepared_composite.save(filename=f"state_{date}#{time}.pbg", outdir=tmp_dir)

        logger.debug(
            f"Copying tmpdir contents [{os.listdir(tmp_dir)}] to output directory {prog_args.output_directory}"
        )
        shutil.copytree(tmp_dir, prog_args.output_directory, dirs_exist_ok=True)
        logger.debug(f"Contents copied to output directory [{os.listdir(prog_args.output_directory)}]")
