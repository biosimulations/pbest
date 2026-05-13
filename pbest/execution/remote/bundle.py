import os.path
import tempfile
import zipfile
from pathlib import Path

from httpx import Client

from pbest import run_remote_experiment_and_wait
from pbest.execution.remote.utils import _normalize_pbg_paths
from pbest.utils.input_types import ExperimentSubmission, OmexExperimentSubmission


async def bundle_and_wait(
    submissions: list[ExperimentSubmission], output_dir: Path, client: Client | None = None, seconds_to_wait: int = 600,
    bundle_size: int = 100
):
    cur_limit: int = 0
    total_subs: int = 0

    while total_subs < len(submissions):
        new_limit = cur_limit + bundle_size if cur_limit + bundle_size < len(submissions) else -1
        sub_section = submissions[cur_limit:new_limit]
        with tempfile.TemporaryDirectory() as tmp_dir:
            cur_uber_omex = tmp_dir / f"bundle.omex"
            with zipfile.ZipFile(cur_uber_omex, "w") as zip_ref:
                for k in range(len(sub_section)):
                    cur_omex = _normalize_pbg_paths(sub_section[k].pbg, os.path.join(tmp_dir, str(k)))
                    zip_ref.write(cur_omex, f"omex_{k}.omex")

            await run_remote_experiment_and_wait(OmexExperimentSubmission(
                omex=cur_uber_omex, interval=0.0),
                client=client,
                output_dir=output_dir,
                seconds_to_wait=seconds_to_wait,
            )
        total_subs += bundle_size
    