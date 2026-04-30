import os
import tempfile
from pathlib import Path

from jinja2 import Template
from pydantic import HttpUrl
from spython.main.parse.parsers import DockerParser  # type: ignore[import-untyped]
from spython.main.parse.writers import SingularityWriter  # type: ignore[import-untyped]

from pbest.utils.input_types import (
    ContainerizationEngine,
    ContainerizationFileRepr,
    ContainerizationTypes,
    DependencyTypes,
    ExperimentDependency,
    ExperimentPrimaryDependencies,
)

micromamba_env_path = "/micromamba_env/runtime_env"


def _default_experiment_deps() -> ExperimentPrimaryDependencies:
    pypi_deps = [
        {"name": "python-copasi", "version": "4.46.300"},
        {"name": "tellurium", "version": "2.2.11.1"},
        {"name": "pb_multiscale_actin", "version": "1.3.1"}
    ]
    return ExperimentPrimaryDependencies(
        pypi_dependencies=[
            ExperimentDependency(
                dependency_name=package["name"],
                url_reference=DependencyTypes.get_pypi_url(package["name"]),
                dependency_type=DependencyTypes.PYPI,
                version=package["version"],
            )
            for package in pypi_deps
        ],
        conda_dependencies=[
            ExperimentDependency(
                dependency_name="readdy",
                url_reference=HttpUrl("https://github.com/readdy/readdy"),
                dependency_type=DependencyTypes.CONDA,
                version="2.0.13",
            )
        ],
    )


def _formulate_dockerfile_for_necessary_env(
    experiment_deps: ExperimentPrimaryDependencies,
    pbest_tag: str = "0.5.6",
) -> ContainerizationFileRepr:
    deps_install_command: str = ""
    pypi_deps = experiment_deps.get_pypi_dependencies()
    for p in range(len(pypi_deps)):
        install_line = (
            f"{pypi_deps[p].get_name() + ('' if pypi_deps[p].any_version_allowed() else f'=={pypi_deps[p].version}')}"
        )
        if p == 0:
            deps_install_command += (
                f"RUN micromamba run -p {micromamba_env_path} python3 -m pip install '{install_line}'"
            )
        elif p != len(pypi_deps) - 1:
            deps_install_command += f" '{install_line}'"
        else:
            deps_install_command += f" '{install_line}'\n"
    for c in experiment_deps.get_conda_dependencies():
        install_line = f"{c.get_name() + ('' if c.any_version_allowed() else f'={c.version}')}"
        deps_install_command += (
            f"RUN micromamba install -c conda-forge -p {micromamba_env_path} {install_line} python=3.12 --yes\n"
        )

    with open(__file__.rsplit(os.sep, maxsplit=1)[0] + f"{os.sep}generic_container.jinja") as f:
        template = Template(f.read())
        templated_container = template.render(
            dependencies_to_install=deps_install_command, micromamba_env_path=micromamba_env_path, pbest_tag=pbest_tag
        )

    return ContainerizationFileRepr(representation=templated_container, containerization_engine=ContainerizationEngine.DOCKER)

def _get_dependencies_from_pbg():
    return _default_experiment_deps()

def _get_dependencies_from_registry():
    pass

def _convert_to_requested_engine(docker_template: ContainerizationFileRepr, desired_engine: ContainerizationEngine) -> ContainerizationFileRepr:
    with tempfile.TemporaryDirectory() as tmp_dir:
        docker_file_path = os.path.join(tmp_dir, "Dockerfile")
        with open(docker_file_path, "w") as docker_file:
            docker_file.write(docker_template.representation)
        match desired_engine:
            case ContainerizationEngine.APPTAINER:
                dockerfile_parser = DockerParser(docker_file_path)
                singularity_writer = SingularityWriter(dockerfile_parser.recipe)
                results = singularity_writer.convert()
                return ContainerizationFileRepr(representation=results, containerization_engine=desired_engine)
            case _:
                return docker_template

def generate_container_def_file(
    dependencies: ExperimentPrimaryDependencies | Path,
    container_engine: ContainerizationEngine = ContainerizationEngine.DOCKER
) -> ContainerizationFileRepr:
    if isinstance(dependencies, Path):
        dependencies = _get_dependencies_from_pbg()

    docker_template: ContainerizationFileRepr = _formulate_dockerfile_for_necessary_env(experiment_deps=dependencies)
    if container_engine != ContainerizationEngine.DOCKER:
        return _convert_to_requested_engine(docker_template=docker_template, desired_engine=container_engine)

    return docker_template
