import copy
import json
import zipfile
from pathlib import Path
from typing import Any

import compose_api_client


def _default_client() -> compose_api_client.client.Client:
    return compose_api_client.client.Client(base_url="https://compose.cam.uchc.edu")


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
                    if new_name not in zip_file.namelist():
                        zip_file.write(og_file, new_name)

        update_pbg_path = Path(tmp_dir) / "updated.pbg"
        with open(update_pbg_path, "w") as input_pbg:
            json.dump(new_pbg, input_pbg)
        zip_file.write(update_pbg_path, "updated.pbg")

    return new_omex
