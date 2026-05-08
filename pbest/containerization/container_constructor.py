import os
import tempfile
from pathlib import Path

import httpx
from jinja2 import Template
from pydantic import HttpUrl
from spython.main.parse.parsers import DockerParser  # type: ignore[import-untyped]
from spython.main.parse.writers import SingularityWriter  # type: ignore[import-untyped]

from pbest.utils.input_types import (
    ContainerizationEngine,
    ContainerizationFileRepr,
    DependencyTypes,
    ExperimentDependency,
    ExperimentPrimaryDependencies,
)

micromamba_env_path = "/micromamba_env/runtime_env"

_REGISTRY_URL = "https://raw.githubusercontent.com/biosimulations/registry/refs/heads/dev/registry.json"


def _default_registry_deps() -> ExperimentPrimaryDependencies:
    response = httpx.get(_REGISTRY_URL)
    response.raise_for_status()
    libraries = response.json()["libraries"]

    pypi: list[ExperimentDependency] = []
    conda: list[ExperimentDependency] = []
    for lib in libraries:
        dep = ExperimentDependency(
            dependency_name=lib["name"],
            url_reference=HttpUrl(lib["url"]),
            dependency_type=DependencyTypes.PYPI if lib["package_registry"] == "pypi" else DependencyTypes.CONDA,
            version=lib.get("version", ""),
        )
        if lib["package_registry"] == "pypi":
            pypi.append(dep)
        else:
            conda.append(dep)

    return ExperimentPrimaryDependencies(pypi_dependencies=pypi, conda_dependencies=conda)


def _formulate_dockerfile_for_necessary_env(
    experiment_deps: ExperimentPrimaryDependencies,
    pbest_tag: str = "0.5.7",
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

    return ContainerizationFileRepr(
        representation=templated_container, containerization_engine=ContainerizationEngine.DOCKER
    )


def _get_dependencies_from_pbg() -> ExperimentPrimaryDependencies:
    return _default_registry_deps()


def _get_dependencies_from_registry() -> None:
    pass


def _convert_to_requested_engine(
    docker_template: ContainerizationFileRepr, desired_engine: ContainerizationEngine
) -> ContainerizationFileRepr:
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
    container_engine: ContainerizationEngine = ContainerizationEngine.DOCKER,
) -> ContainerizationFileRepr:
    if isinstance(dependencies, Path):
        dependencies = _get_dependencies_from_pbg()

    docker_template: ContainerizationFileRepr = _formulate_dockerfile_for_necessary_env(experiment_deps=dependencies)
    if container_engine != ContainerizationEngine.DOCKER:
        return _convert_to_requested_engine(docker_template=docker_template, desired_engine=container_engine)

    return docker_template
