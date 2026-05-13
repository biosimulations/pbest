import os.path
import tempfile
import zipfile
from pathlib import Path

from httpx import Client

from pbest import run_remote_experiment_and_wait
from pbest.execution.remote.utils import _normalize_pbg_paths
from pbest.utils.input_types import ExperimentSubmission, OmexExperimentSubmission

def _bundle_maker(submissions: list[ExperimentSubmission], cur_limit,  bundle_size, tmp_dir: str) -> Path:
    new_limit = cur_limit + bundle_size if cur_limit + bundle_size < len(submissions) else -1
    sub_section = submissions[cur_limit:new_limit]
    cur_uber_omex = Path(tmp_dir) / f"bundle_{cur_limit}.omex"
    with zipfile.ZipFile(cur_uber_omex, "w") as zip_ref:
        for k in range(len(sub_section)):
            sub_dir = os.path.join(tmp_dir, str(k))
            os.makedirs(sub_dir, exist_ok=True)
            cur_omex = _normalize_pbg_paths(sub_section[k].pbg, sub_dir)
            zip_ref.write(cur_omex, f"omex_{k}.omex")
    return cur_uber_omex


async def bundle_and_wait(
    submissions: list[ExperimentSubmission],
    output_dir: Path,
    client: Client | None = None,
    seconds_to_wait: int = 600,
    bundle_size: int = 100,
) -> None:
    cur_limit: int = 0
    total_subs: int = 0

    with tempfile.TemporaryDirectory() as tmp_dir:
        while total_subs < len(submissions):
            cur_uber_omex = _bundle_maker(submissions, cur_limit, bundle_size, tmp_dir)
            await run_remote_experiment_and_wait(
                OmexExperimentSubmission(omex=cur_uber_omex, interval=0.0),
                client=client,
                output_dir=output_dir,
                seconds_to_wait=seconds_to_wait,
            )
            total_subs += bundle_size
            cur_limit += bundle_size
