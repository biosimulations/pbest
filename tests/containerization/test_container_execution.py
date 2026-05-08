# ruff: noqa: S607
# ruff: noqa: S603
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import docker
import pytest
from docker.errors import ContainerError

from pbest.containerization.container_constructor import _default_registry_deps, \
    generate_container_def_file
from tests.fixtures.pb import _get_model_path
from tests.fixtures.utils import is_docker_present
from tests.standard_tools.test_comparison import comparison_result_dict_test


def build_image_and_run_experiment(
    input_dir: Path,
    output_dir: Path,
    input_file: Path,
    time_to_run: int = 1,
    show_logs: bool = False,
    platform: str = "linux/amd64",
) -> None:
    experiment_deps = _default_registry_deps()
    docker_image_path = f"{input_dir}{os.sep}Dockerfile"
    docker_tag = "test_crbm_containerization"

    with open(docker_image_path, "w") as f:
        docker_file = generate_container_def_file(dependencies=experiment_deps)
        f.write(docker_file.representation)

    # Subprocess because SDK seems to have problems building containers for other platforms
    subprocess.run(
        [
            "docker",
            "buildx",
            "build",
            f"--platform={platform}",
            "--load",
            # "--no-cache",
            "-t",
            docker_tag,
            str(input_dir),
        ],
        check=True,
    )

    # Bind dir with all related files to /experiment
    client = docker.from_env()
    try:
        logs = client.containers.run(
            image="test_crbm_containerization:latest",
            remove=True,
            command=f"run -o /experiment/output -n {time_to_run} /experiment/input/{input_file.name}",
            volumes={
                input_dir: {"bind": "/experiment/input", "mode": "rw"},
                output_dir: {"bind": "/experiment/output", "mode": "rw"},
            },
            environment={
                "LOGGER_LEVEL": "DEBUG",
            },
            platform=platform,
            stderr=True,
            stdout=True,
        )
        if show_logs:
            print(logs.decode("utf-8"))
    except ContainerError as e:
        print(e.stderr.decode("utf-8"))


def comparison_test(comparison_document: dict[Any, Any], platform: str) -> None:
    with tempfile.TemporaryDirectory(delete=False) as tmpdir:
        input_dir = Path(tmpdir) / "input"
        output_dir = Path(tmpdir) / "output"
        os.mkdir(input_dir)
        os.mkdir(output_dir)

        model_name = "model.xml"
        comparison_pbg_path = Path(f"{input_dir}{os.sep}comparison.pbg")

        shutil.copyfile(_get_model_path(), input_dir / model_name)
        with open(comparison_pbg_path, "w") as f:
            comparison_doc_str = json.dumps(comparison_document)
            comparison_doc_str = comparison_doc_str.replace(_get_model_path(), f"/experiment/input/{model_name}")
            f.write(comparison_doc_str)

        build_image_and_run_experiment(input_dir, output_dir, comparison_pbg_path, platform=platform)
        # run_experiment(prog_args=ExecutionProgramArguments(input_file_path=str(comparison_pbg_path), interval=1, output_directory=Path(output_dir)))

        result_file = next(k for k in os.listdir(output_dir) if (".pbg" in k) and ("state" in k))
        with open(os.path.join(output_dir, result_file)) as f:
            json_result = json.load(f)["state"]["comparison_result"]["species_mse"]

        comparison_result_dict_test(json_result)

@pytest.mark.skipif(not is_docker_present(), reason="docker daemon is not running")
def test_execution_of_container_amd(comparison_document: dict[Any, Any]) -> None:
    comparison_test(comparison_document, "linux/amd64")


# @pytest.mark.skipif(not is_docker_present(), reason="docker daemon is not running")
# def test_execution_of_container_arm(comparison_document: dict[Any, Any]) -> None:
#     comparison_test(comparison_document, "linux/arm64")


@pytest.mark.skipif(not is_docker_present(), reason="docker daemon is not running")
def test_execution_of_readdy_container(readdy_document: dict[str, Any]) -> None:
    with tempfile.TemporaryDirectory(delete=False) as tmpdir:
        input_dir = Path(tmpdir) / "input"
        output_dir = Path(tmpdir) / "output"
        os.mkdir(input_dir)
        os.mkdir(output_dir)

        readdy_pbif = Path(f"{input_dir}{os.sep}readdy.pbg")
        readdy_document["state"]["emitter"]["config"]["output_dir"] = "/experiment/output"

        with open(readdy_pbif, "w") as f:
            readdy_state_str = json.dumps(readdy_document)
            f.write(readdy_state_str)

        build_image_and_run_experiment(input_dir, output_dir, readdy_pbif, time_to_run=3, show_logs=True)

        result_file = next(k for k in os.listdir(output_dir) if ".simularium" in k)

        assert result_file != ""
        assert "readdy_result" in result_file
