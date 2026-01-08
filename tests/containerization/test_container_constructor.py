import tempfile
from pathlib import Path

from bsedic.containerization import (
    convert_dependencies_to_installation_string_representation,
    determine_dependencies,
    formulate_dockerfile_for_necessary_env,
)
from bsedic.utils.input_types import (
    ContainerizationEngine,
    ContainerizationProgramArguments,
    ContainerizationTypes,
    ExperimentPrimaryDependencies,
)

# def test_generate_necessary_values() -> None:
#     results = generate_necessary_values()
#     correct_answer = [  # update this as we add more fields!
#         "CONDA_FORGE_DEPENDENCIES",
#         "PYPI_DEPENDENCIES",
#     ]
#     assert set(results) == set(correct_answer)


def get_test_docker_str(managers_to_install: str = "", packages_to_add: str = "") -> str:
    return f"""
FROM ghcr.io/astral-sh/uv:python3.12-bookworm

RUN apt update
RUN apt upgrade -y
RUN apt install -y git curl

## Additional Execution tools (ex. Conda)
{managers_to_install}

## Dependency Installs
{packages_to_add}


## Execute
RUN mkdir /runtime
WORKDIR /runtime
RUN git clone https://github.com/biosimulations/biosim-registry.git /runtime
RUN python3 -m pip install -e /runtime

ENTRYPOINT ["python3", "/runtime/bsedic/main.py"]
""".strip()


def test_determine_dependencies():
    mock_list = """
`python:pypi<numpy[>=2.0.0]>@numpy.random.rand`
`python:pypi<process-bigraph[<1.0]>@process_bigraph.processes.ParameterScan`
`python:pypi<importlib>@importlib.metadata.distribution`
`python:conda<readdy>@readdy.ReactionDiffusionSystem`
    """.strip()
    correct_answer = (
        [
            "numpy>=2.0.0",
            "process-bigraph<1.0",
            "importlib",
        ],
        ["readdy"],
        """
`local:numpy.random.rand`
`local:process_bigraph.processes.ParameterScan`
`local:importlib.metadata.distribution`
`local:readdy.ReactionDiffusionSystem`
""".strip(),
    )
    (pypi_results, conda_results), adjusted_list = determine_dependencies(mock_list)
    assert (pypi_results[1], conda_results[1], adjusted_list) == correct_answer


def test_convert_dependencies_to_installation_string_representation():
    dependencies = [
        "numpy>=2.0.0",
        "process-bigraph<1.0",
        "importlib",
    ]
    results = convert_dependencies_to_installation_string_representation(dependencies)
    correct_answer = "'numpy>=2.0.0' 'process-bigraph<1.0' 'importlib'".strip()
    assert results == correct_answer


def _build_dockerfile_for_necessary_env_exec(
    correct_answer: str, fake_input_file: str, dependencies: ExperimentPrimaryDependencies
):
    with tempfile.TemporaryDirectory() as tmpdir:
        with tempfile.NamedTemporaryFile(mode="w", dir=tmpdir, delete=False) as fake_target_file:
            fake_target_file.write(fake_input_file)
        test_args = ContainerizationProgramArguments(
            input_file_path=fake_target_file.name,
            working_directory=Path(tmpdir),
            containerization_type=ContainerizationTypes.SINGLE,
            containerization_engine=ContainerizationEngine.DOCKER,
        )
        results = formulate_dockerfile_for_necessary_env(test_args, dependencies)
        print(results[0].representation)
        assert results[0].representation == correct_answer


def test_build_dockerfile_for_necessary_env_pypi_only() -> None:
    correct_answer = get_test_docker_str(
        packages_to_add="RUN python3 -m pip install 'numpy>=2.0.0' 'process-bigraph<1.0'"
    )
    fake_input_file = """
"python:pypi<numpy[>=2.0.0]>@numpy.random.rand"
"python:pypi<process-bigraph[<1.0]>@process_bigraph.processes.ParameterScan"
""".strip()
    _build_dockerfile_for_necessary_env_exec(
        correct_answer, fake_input_file, ExperimentPrimaryDependencies(["numpy>=2.0.0", "process-bigraph<1.0"], [])
    )


def test_build_dockerfile_for_necessary_env_both() -> None:
    exp_dependencies = ExperimentPrimaryDependencies(["numpy>=2.0.0", "process-bigraph<1.0"], ["readdy"])
    packages_to_install = """
RUN python3 -m pip install 'numpy>=2.0.0' 'process-bigraph<1.0'
RUN micromamba update -c conda-forge -p /micromamba_env/runtime_env readdy python=3.12
""".strip()
    fake_input_file = """
"python:pypi<numpy[>=2.0.0]>@numpy.random.rand"
"python:pypi<process-bigraph[<1.0]>@process_bigraph.processes.ParameterScan"
`python:conda<readdy>@readdy.ReactionDiffusionSystem`
""".strip()
    correct_answer = get_test_docker_str(exp_dependencies.manager_installation_string(), packages_to_install)
    _build_dockerfile_for_necessary_env_exec(correct_answer, fake_input_file, exp_dependencies)


def test_build_dockerfile_for_necessary_env_conda() -> None:
    exp_dependencies = ExperimentPrimaryDependencies([], ["readdy"])
    packages_to_install = """
RUN micromamba update -c conda-forge -p /micromamba_env/runtime_env readdy python=3.12
    """.strip()
    correct_answer = get_test_docker_str(
        managers_to_install=exp_dependencies.manager_installation_string(), packages_to_add=packages_to_install
    )
    _build_dockerfile_for_necessary_env_exec(correct_answer, "", exp_dependencies)
