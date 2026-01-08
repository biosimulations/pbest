import os
import tempfile
import zipfile
from pathlib import Path

from bsedic.containerization.container_constructor import generate_container_def_file
from bsedic.utils.input_types import (
    ContainerizationEngine,
    ContainerizationProgramArguments,
    ContainerizationTypes,
    ExperimentPrimaryDependencies,
)
from tests.containerization.test_container_constructor import get_test_docker_str


def test_build_dockerfile_for_necessary_env_from_archive() -> None:
    packages_to_install = """RUN python3 -m pip install 'cobra' 'tellurium' 'numpy' 'matplotlib' 'scipy'
RUN micromamba update -c conda-forge -p /micromamba_env/runtime_env readdy python=3.12"""

    packages = ExperimentPrimaryDependencies([""], [""])
    correct_answer = get_test_docker_str(
        managers_to_install=packages.manager_installation_string(), packages_to_add=packages_to_install
    )
    fake_input_file = "bob"
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, "inputArchive.omex")
        with zipfile.ZipFile(zip_path, "a") as zip_ref:
            zip_ref.writestr("inputFile.pbif", fake_input_file)
        test_args = ContainerizationProgramArguments(
            input_file_path=zip_path,
            working_directory=Path(tmpdir),
            containerization_type=ContainerizationTypes.SINGLE,
            containerization_engine=ContainerizationEngine.DOCKER,
        )
        generate_container_def_file(test_args)
        output_dockerfile = os.path.join(tmpdir, "Dockerfile")
        with open(output_dockerfile) as results_file:
            results = results_file.read()
        assert results == correct_answer
