import json
import math
import os.path
import tempfile
from pathlib import Path

import numpy

from pbest import run_experiment
from pbest.utils.input_types import ExecutionProgramArguments
from tests.fixtures.utils import test_root_dir_path

experiment = {
    "state": {
        "time_course": {
            "_type" : "step",
            "address": "local:pbest.registry.simulators.tellurium_process.TelluriumUTCStep",
            "config": {
                "model_source": os.path.join(test_root_dir_path(), "resources", "simulators", "tellurium.sbml"),
                "time": 10,
                "n_points": 51,
            },
            "interval": 1.0,
            "inputs": {},
            "outputs": {}
        }
    }
}

def check_test(experiment_result: str, expected_csv_path: str, difference_tolerance: float=5e-10):
    experiment_numpy = numpy.genfromtxt(experiment_result, delimiter=",", dtype=object)
    report_numpy = numpy.genfromtxt(expected_csv_path, delimiter=",", dtype=object)
    assert report_numpy.shape == experiment_numpy.shape
    r, c = report_numpy.shape
    for i in range(r):
        for j in range(c):
            report_val = report_numpy[i, j].decode("utf-8")
            experiment_val = experiment_numpy[i, j].decode("utf-8")
            try:
                f_report = float(report_val)
                f_exp = float(experiment_val)
                assert math.isclose(f_report, f_exp, rel_tol=0, abs_tol=difference_tolerance)
            except ValueError:
                assert report_val == experiment_val  # Must be string portion of report then (columns)

def test_tellurium() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.pbif")
        experiment["state"]["time_course"]["config"]["output_dir"] = tmpdir
        with open(input_path, "w") as f:
            json.dump(experiment, f)
        run_experiment(prog_args=ExecutionProgramArguments(
            input_file_path=input_path,
            output_directory=Path(tmpdir),
            interval=1
        ))


        check_test(experiment_result=os.path.join(tmpdir, "results.csv"),
                   expected_csv_path=os.path.join(test_root_dir_path(), "resources", "simulators", "tellurium_report.csv"),)
