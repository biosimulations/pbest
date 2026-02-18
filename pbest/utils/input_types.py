from enum import Enum
from pathlib import Path

from pydantic import BaseModel, HttpUrl
from pydantic.dataclasses import dataclass


class ContainerizationTypes(Enum):
    NONE = 0
    SINGLE = 1
    MULTIPLE = 2


class ContainerizationEngine(Enum):
    NONE = 0
    DOCKER = 1
    APPTAINER = 2
    BOTH = 3


class ContainerizationFileRepr(BaseModel):
    representation: str


class DependencyTypes(Enum):
    PYPI = "pypi"
    CONDA = "conda"

    @staticmethod
    def get_pypi_url(package_name: str) -> HttpUrl:
        return HttpUrl(f"https://pypi.org/project/{package_name}/")


@dataclass(frozen=True)
class ExperimentDependency:
    dependency_name: str
    url_reference: HttpUrl
    dependency_type: DependencyTypes
    version: str = ""

    def get_name(self) -> str:
        return self.dependency_name


@dataclass(frozen=True)
class ExperimentPrimaryDependencies:
    pypi_dependencies: list[ExperimentDependency]
    conda_dependencies: list[ExperimentDependency]

    def get_pypi_dependencies(self) -> list[ExperimentDependency]:
        return self.pypi_dependencies

    def get_conda_dependencies(self) -> list[ExperimentDependency]:
        return self.conda_dependencies


@dataclass(frozen=True)
class ContainerizationProgramArguments:
    """
    Create a container acting as an isolated environment for execution.
    """

    input_file_path: str
    containerization_type: ContainerizationTypes
    containerization_engine: ContainerizationEngine
    working_directory: Path


@dataclass
class ExecutionProgramArguments:
    """
    Provide information required to execute a process bi-graph.
    """

    input_file_path: str
    interval: float
    output_directory: Path
