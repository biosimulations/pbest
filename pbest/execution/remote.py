import copy
import datetime
import json
import os
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import compose_api_client
from compose_api_client.models import SimulationExperiment
from compose_api_client.types import File
from compose_api_client.utils import run_simulation_and_wait
from httpx import Client


def _normalize_pbg_paths(pbg: Path | dict[str, Any], tmp_dir: str) -> Path:
    new_pbg: dict
    if isinstance(pbg, Path) and pbg.suffix == ".pbg":
        with open(pbg) as input_file:
            new_pbg = json.load(input_file)
    elif isinstance(pbg, dict):
        new_pbg = copy.deepcopy(pbg)
    else:
        err_msg = f"PBG must be a .pbg file or a dict, instead got: {pbg}"
        raise TypeError(err_msg)

    exploration_set: list[dict] = [new_pbg]
    new_omex = Path(tmp_dir) / "experiment.omex"
    with zipfile.ZipFile(new_omex, "w") as zip_file:
        while len(exploration_set) != 0:
            sub_dict = exploration_set.pop()
            for k, v in sub_dict.items():
                if isinstance(v, dict):
                    exploration_set.append(v)
                elif isinstance(v, str) and Path(v).is_file():
                    og_file = Path(v)
                    new_name = og_file.name
                    sub_dict[k] = new_name
                    if not new_name in zip_file.namelist():
                        zip_file.write(og_file, new_name)

        update_pbg_path = Path(tmp_dir) / "updated.pbg"
        with open(update_pbg_path, "w") as input_pbg:
            json.dump(new_pbg, input_pbg)
        zip_file.write(update_pbg_path, "updated.pbg")

    return new_omex


async def run_remote_experiment(pbg: Path | dict, interval: float, output_dir: Path, client: Client | None = None) -> SimulationExperiment:
    if client is None:
        client = compose_api_client.Client(base_url="https://compose.cam.uchc.edu")

    with tempfile.TemporaryDirectory() as tmp_dir:
        omex_file = _normalize_pbg_paths(pbg, tmp_dir)

        with open(omex_file, "rb") as input_file:
            sent_file = File(file_name=f"experiment.omex", payload=input_file)
            result, sim_id = await run_simulation_and_wait.async_call(
                experiment_file=sent_file, interval=interval, client=client
            )

        output_name = output_dir / f"experiment_result_{datetime.datetime.now()}.zip"
        with open(os.path.join(output_dir, output_name), "wb") as output_file:
            output_file.write(result.content)

        return sim_id
