import math
from pathlib import Path

import docker
import numpy


def is_docker_present() -> bool:
    client = docker.from_env()
    try:
        client.ping()
        return True  # noqa: TRY300
    except Exception:
        return False


def root_dir_path() -> Path:
    return Path(__file__).parent.parent


def compare_csv(experiment_result: str, expected_csv_path: str, difference_tolerance: float = 5e-10):
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
