import datetime
import json
import logging
import os
import shutil
import tempfile
from pathlib import Path

from process_bigraph import Composite, gather_emitter_results

from pbest.globals import get_loaded_core
from pbest.utils.input_types import ExperimentSubmission

logger = logging.getLogger(__name__)


def run_experiment(submission: ExperimentSubmission, output_directory: Path) -> None:
    """
    Is the function which all other "run" related functions end up calling, both locally and on the server.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        schema = submission.pbg
        if isinstance(submission.pbg, Path):
            is_pbg = submission.pbg.suffix == ".pbg"
            if not is_pbg:
                err_msg = f"Expected pbg file instead got {submission.pbg}"
                raise ValueError(err_msg)
            else:
                with open(submission.pbg) as input_data:
                    schema = json.load(input_data)

        logger.debug(f"PBG schema: {schema}")
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
