import datetime
import json
import logging
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from process_bigraph import Composite, gather_emitter_results

from pbest.globals import get_loaded_core, get_trace_level
from pbest.utils.input_types import ExperimentSubmission, OmexExperimentSubmission

logger = logging.getLogger(__name__)


def _get_pb_schema_from_omex(omex_file: Path, working_dir: str) -> dict[str, Any]:
    pbg_file: str | None = None
    with zipfile.ZipFile(omex_file, "r") as zf:
        zf.extractall(working_dir)
    for file_name in os.listdir(working_dir):
        if not file_name.endswith(".pbg"):
            continue
        pbg_file = os.path.join(working_dir, file_name)
        break

    if pbg_file is None:
        err = f"Could not find any PBG or JSON file in or at `{omex_file}`."
        raise FileNotFoundError(err)

    # Make relative paths in PBG absolute
    with open(pbg_file) as input_data:
        json_string = input_data.read()
        for other_file in os.listdir(working_dir):
            if not other_file.endswith(".pbg"):
                json_string = json_string.replace(other_file, os.path.join(working_dir, other_file))
        result: dict[str, Any] = json.loads(json_string)
    return result


def _get_pb_schema(submission: ExperimentSubmission | OmexExperimentSubmission, working_dir: str) -> dict[str, Any]:
    if isinstance(submission, ExperimentSubmission):
        if isinstance(submission.pbg, Path):
            is_pbg = submission.pbg.suffix == ".pbg"
            if not is_pbg:
                err_msg = f"Expected pbg file instead got {submission.pbg}"
                raise ValueError(err_msg)
            else:
                with open(submission.pbg) as input_data:
                    schema: dict[str, Any] = json.load(input_data)
                return schema
        return submission.pbg
    elif isinstance(submission, OmexExperimentSubmission):
        return _get_pb_schema_from_omex(submission.omex, working_dir)
    else:
        msg = f"Unsupported submission type: {submission.__class__.__name__}"
        raise TypeError(msg)


def run_experiment(submission: ExperimentSubmission | OmexExperimentSubmission, output_directory: Path) -> None:
    """
    Is the function which all other "run" related functions end up calling, both locally and on the server.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        schema = _get_pb_schema(submission, tmp_dir)
        logger.log(level=get_trace_level(), msg=f"PBG schema: {schema}")
        core = get_loaded_core()
        prepared_composite = Composite(core=core, config=schema)

        prepared_composite.run(interval=submission.interval)
        query_results = gather_emitter_results(prepared_composite)

        current_dt = datetime.datetime.now()
        date, tz, time = str(current_dt.date()), str(current_dt.tzinfo), str(current_dt.time()).replace(":", "-")

        try:
            if len(query_results) != 0:
                emitter_results_file_path = os.path.join(output_directory, f"results_{date}[{tz}#{time}].pber")
                with open(emitter_results_file_path, "w") as emitter_results_file:
                    json.dump(query_results, emitter_results_file)
        except TypeError as e:
            err_msg = f"Tried to save query results to {emitter_results_file_path}: {e}"
            logger.exception(err_msg)

        prepared_composite.save(filename=f"state_{date}#{time}.pbg", outdir=tmp_dir)

        logger.debug(f"Copying tmpdir contents [{os.listdir(tmp_dir)}] to output directory {output_directory}")
        shutil.copytree(tmp_dir, output_directory, dirs_exist_ok=True)
        logger.debug(f"Contents copied to output directory [{os.listdir(output_directory)}]")
