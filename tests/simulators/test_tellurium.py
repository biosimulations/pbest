import json
import os.path
import tempfile
from pathlib import Path

from pbest import run_experiment
from pbest.utils.input_types import ExecutionProgramArguments
from tests.fixtures.utils import compare_csv, root_dir_path

experiment = {
    "state": {
        "time_course": {
            "_type": "step",
            "address": "local:pbest.registry.simulators.tellurium_process.TelluriumUTCStep",
            "config": {
                "model_source": os.path.join(root_dir_path(), "resources", "simulators", "phase_cycle.sbml"),
                "time": 10,
                "n_points": 51,
            },
            "interval": 1.0,
            "inputs": {},
            "outputs": {},
        }
    }
}


def test_tellurium() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.pbif")
        experiment["state"]["time_course"]["config"]["output_dir"] = tmpdir
        with open(input_path, "w") as f:
            json.dump(experiment, f)
        run_experiment(
            prog_args=ExecutionProgramArguments(input_file_path=input_path, output_directory=Path(tmpdir), interval=1)
        )

        compare_csv(
            experiment_result=os.path.join(tmpdir, "results.csv"),
            expected_csv_path=os.path.join(root_dir_path(), "resources", "simulators", "tellurium_report.csv"),
        )
