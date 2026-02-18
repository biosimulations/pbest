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
            "address": "local:pbest.registry.simulators.copasi_process.CopasiUTCStep",
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


def test_copasi() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.pbg")
        experiment["state"]["time_course"]["config"]["output_dir"] = tmpdir
        with open(input_path, "w") as f:
            json.dump(experiment, f)
        run_experiment(
            prog_args=ExecutionProgramArguments(input_file_path=input_path, output_directory=Path(tmpdir), interval=1)
        )

        compare_csv(
            experiment_result=os.path.join(tmpdir, "results.csv"),
            expected_csv_path=os.path.join(root_dir_path(), "resources", "simulators", "copasi_report.csv"),
            difference_tolerance=1e-4,
        )


def test_copasi_omex() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = root_dir_path() / "resources" / "simulators" / "copasi_phase_cycle.omex"
        run_experiment(
            prog_args=ExecutionProgramArguments(
                input_file_path=str(input_path), output_directory=Path(tmpdir), interval=1
            )
        )

        compare_csv(
            experiment_result=os.path.join(tmpdir, "results.csv"),
            expected_csv_path=os.path.join(root_dir_path(), "resources", "simulators", "copasi_report.csv"),
            difference_tolerance=1e-4,
        )
