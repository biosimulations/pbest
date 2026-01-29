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

from pbest.containerization.container_constructor import formulate_dockerfile_for_necessary_env, get_experiment_deps
from pbest.utils.input_types import ContainerizationEngine, ContainerizationProgramArguments, ContainerizationTypes
from tests.fixtures.pb import _get_model_path
from tests.fixtures.utils import is_docker_present
from tests.standard_tools.test_comparison import comparison_result_dict_test


def build_image_and_run_experiment(
    input_dir: Path,
    output_dir: Path,
    input_file: Path,
    time_to_run: int = 1,
    show_logs: bool = False,
) -> None:
    experiment_deps = get_experiment_deps()
    docker_image_path = f"{input_dir}{os.sep}Dockerfile"
    docker_tag = "test_crbm_containerization"

    with open(docker_image_path, "w") as f:
        docker_file = formulate_dockerfile_for_necessary_env(
            ContainerizationProgramArguments(
                containerization_type=ContainerizationTypes.SINGLE,
                containerization_engine=ContainerizationEngine.DOCKER,
                working_directory=Path(input_dir),
                input_file_path=str(input_file),
            ),
            experiment_deps,
        )
        f.write(docker_file.representation)

    # Subprocess because SDK seems to have problems building containers for other platforms
    subprocess.run(
        [
            "docker",
            "buildx",
            "build",
            "--platform=linux/amd64",
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
            volumes={
                input_dir: {"bind": "/experiment/input", "mode": "rw"},
                output_dir: {"bind": "/experiment/output", "mode": "rw"},
            },
            environment={
                "PB_INPUT_FILE_PATH": f"/experiment/input/{input_file.name}",
                "PB_OUTPUT_DIRECTORY": "/experiment/output",
                "LOGGER_LEVEL": "DEBUG",
                "PB_INTERVAL": time_to_run,
            },
            platform="linux/amd64",
            stderr=True,
            stdout=True,
        )
        if show_logs:
            print(logs.decode("utf-8"))
    except ContainerError as e:
        print(e.stderr)


@pytest.mark.skipif(not is_docker_present(), reason="docker daemon is not running")
def test_execution_of_container(comparison_document: dict[Any, Any]) -> None:
    with tempfile.TemporaryDirectory(delete=False) as tmpdir:
        input_dir = Path(tmpdir) / "input"
        output_dir = Path(tmpdir) / "output"
        os.mkdir(input_dir)
        os.mkdir(output_dir)

        model_name = "model.xml"
        comparison_pbg_path = Path(f"{input_dir}{os.sep}comparison.pbif")

        shutil.copyfile(_get_model_path(), input_dir / model_name)
        with open(comparison_pbg_path, "w") as f:
            comparison_doc_str = json.dumps(comparison_document)
            comparison_doc_str = comparison_doc_str.replace(_get_model_path(), f"/experiment/input/{model_name}")
            f.write(comparison_doc_str)

        build_image_and_run_experiment(input_dir, output_dir, comparison_pbg_path)

        result_file = next(k for k in os.listdir(output_dir) if ".pbg" in k)
        with open(os.path.join(output_dir, result_file)) as f:
            json_result = json.load(f)["state"]["comparison_result"]["species_mse"]

        comparison_result_dict_test(json_result)


@pytest.mark.skipif(not is_docker_present(), reason="docker daemon is not running")
def test_execution_of_readdy_container(readdy_document: dict[str, Any]) -> None:
    with tempfile.TemporaryDirectory(delete=False) as tmpdir:
        input_dir = Path(tmpdir) / "input"
        output_dir = Path(tmpdir) / "output"
        os.mkdir(input_dir)
        os.mkdir(output_dir)

        readdy_pbif = Path(f"{input_dir}{os.sep}readdy.pbif")
        readdy_document["state"]["emitter"]["config"]["output_dir"] = "/experiment/output"

        with open(readdy_pbif, "w") as f:
            readdy_state_str = json.dumps(readdy_document)
            f.write(readdy_state_str)

        build_image_and_run_experiment(input_dir, output_dir, readdy_pbif, time_to_run=3, show_logs=True)

        result_file = next(k for k in os.listdir(output_dir) if ".simularium" in k)

        assert result_file != ""
        assert "readdy_result" in result_file
