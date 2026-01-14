from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from pydantic import BaseModel


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


class ExperimentPrimaryDependencies(BaseModel):
    pypi_dependencies: list[str]
    conda_dependencies: list[str]
    _compact_repr: str

    @staticmethod
    def from_compact_repr(representation: str) -> "ExperimentPrimaryDependencies":
        split_dep_type = representation.split(";")
        if len(split_dep_type) != 2:
            err_msg = f"Invalid primary dependency representation: {representation}"
            raise ValueError(err_msg)
        pypi_dependencies = split_dep_type[0].split(",")
        conda_dependencies = split_dep_type[1].split(",")
        return ExperimentPrimaryDependencies(pypi_dependencies=pypi_dependencies, conda_dependencies=conda_dependencies)

    def __init__(self, pypi_dependencies: list[str], conda_dependencies: list[str]) -> None:
        super().__init__(pypi_dependencies=pypi_dependencies, conda_dependencies=conda_dependencies)
        self.pypi_dependencies = pypi_dependencies
        self.conda_dependencies = conda_dependencies
        self._compact_repr = ",".join(pypi_dependencies) + ";" + ",".join(conda_dependencies)

    def __str__(self) -> str:
        pypi_dependencies: str = "PyPi Dependencies:\n\t" + "\n\t".join(self.pypi_dependencies)
        conda_dependencies: str = "Conda Dependencies:\n\t" + "\n\t".join(self.conda_dependencies)
        return pypi_dependencies + "\n" + ("-" * 25) + "\n" + conda_dependencies

    def __repr__(self) -> str:
        pypi_dependencies: str = "pypi:" + ",pypi:".join(self.pypi_dependencies)
        conda_dependencies: str = "conda:" + ",conda:".join(self.conda_dependencies)
        return pypi_dependencies + "," + conda_dependencies

    @staticmethod
    def manager_installation_string() -> str:
        additional_execution_tools: str = ""
        if True:
            additional_execution_tools += """WORKDIR /usr/local/bin
RUN curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xvj bin/micromamba --strip-components=1
WORKDIR /
RUN mkdir /micromamba_env
RUN micromamba create -p /micromamba_env/runtime_env python=3.12
RUN eval "$(micromamba shell hook --shell posix)" && micromamba activate /micromamba_env/runtime_env"""
        return additional_execution_tools

    def get_compact_repr(self) -> str:
        return self._compact_repr

    def get_pypi_dependencies(self) -> list[str]:
        return self.pypi_dependencies

    def get_conda_dependencies(self) -> list[str]:
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
