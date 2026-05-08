from pathlib import Path

from pydantic.dataclasses import dataclass

from pbest.utils.input_types import ContainerizationEngine, ExperimentPrimaryDependencies


@dataclass(frozen=True)
class CLIExecutionProgramArguments:
    """
    Provide information required to execute a process bi-graph.
    """

    file_path: Path
    interval: float
    output_directory: Path


@dataclass(frozen=True)
class CLIContainerizationProgramArguments:
    """
    Create a container acting as an isolated environment for execution.
    """

    output_directory: Path
    input: ExperimentPrimaryDependencies | Path
    containerization_engine: ContainerizationEngine
