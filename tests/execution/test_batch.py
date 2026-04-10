import os
import tempfile
import zipfile
from pathlib import Path

import pytest

from pbest.execution.remote import batch_run_remote_experiment_and_wait
from pbest.utils.builder import CompositeBuilder
from tests.fixtures.utils import root_dir_path
from tests.standard_tools.test_harmony import create_parameter_scan
import json
from tests.standard_tools.test_harmony import perform_parameter_scan_comparison


@pytest.mark.asyncio
async def test_batch_run_remote_experiment_and_wait(fully_registered_builder: CompositeBuilder):
    model_path = f"{root_dir_path()}/resources/BIOMD0000000012_url.xml"
    create_parameter_scan(fully_registered_builder, model_path=model_path)

    builder_states = fully_registered_builder.get_builder_state()
    all_pbgs = [builder_states, builder_states]
    all_intervals = [0, 0]

    with tempfile.TemporaryDirectory() as temp_dir:
        completed = await batch_run_remote_experiment_and_wait(all_pbgs, all_intervals, Path(temp_dir))

        assert len(completed) == len(all_pbgs)
        paths = os.listdir(temp_dir)
        assert len(paths) > 0
        for path in paths:
            res_path = os.path.join(temp_dir, path)
            result_pbg = next(k for k in os.listdir(res_path) if "state" in k)

            with open(os.path.join(res_path, result_pbg)) as result_file:
                json_data = json.load(result_file)
                perform_parameter_scan_comparison(json_data["state"]["parameter_scan_0"]["results"])
