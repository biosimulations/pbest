import tempfile

from bsedic.pbic3g.containerization.container_constructor import (
    ProgramArguments,
    convert_dependencies_to_installation_string_representation,
    determine_dependencies,
    formulate_dockerfile_for_necessary_env,
    generate_necessary_values,
)
from bsedic.utils.input_types import ContainerizationEngine, ContainerizationTypes


def test_generate_necessary_values() -> None:
    results = generate_necessary_values()
    correct_answer = [  # update this as we add more fields!
        "CONDA_FORGE_DEPENDENCIES",
        "PYPI_DEPENDENCIES",
    ]
    assert set(results) == set(correct_answer)


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


def _build_dockerfile_for_necessary_env_exec(correct_answer: str, fake_input_file: str):
    with tempfile.TemporaryDirectory() as tmpdir:
        with tempfile.NamedTemporaryFile(mode="w", dir=tmpdir, delete=False) as fake_target_file:
            fake_target_file.write(fake_input_file)
        test_args = ProgramArguments(
            fake_target_file.name, tmpdir, None, ContainerizationTypes.SINGLE, ContainerizationEngine.DOCKER
        )
        results = formulate_dockerfile_for_necessary_env(test_args)
        assert results[0].representation == correct_answer


def test_build_dockerfile_for_necessary_env_pypi_only() -> None:
    correct_answer = """
FROM ghcr.io/astral-sh/uv:python3.12-bookworm

RUN apt update
RUN apt upgrade -y
RUN apt install -y git curl

## Dependency Installs
### Conda
# No conda dependencies!

### PyPI
RUN python3 -m pip install 'numpy>=2.0.0' 'process-bigraph<1.0'

##
RUN mkdir /runtime
WORKDIR /runtime
RUN git clone https://github.com/biosimulators/bsew.git  /runtime
RUN python3 -m pip install -e /runtime

ENTRYPOINT ["python3", "/runtime/main.py"]
""".strip()
    fake_input_file = """
"python:pypi<numpy[>=2.0.0]>@numpy.random.rand"
"python:pypi<process-bigraph[<1.0]>@process_bigraph.processes.ParameterScan"
""".strip()
    _build_dockerfile_for_necessary_env_exec(correct_answer, fake_input_file)


def test_build_dockerfile_for_necessary_env_both() -> None:
    correct_answer = """
FROM ghcr.io/astral-sh/uv:python3.12-bookworm

RUN apt update
RUN apt upgrade -y
RUN apt install -y git curl

## Dependency Installs
### Conda
RUN mkdir /micromamba
RUN curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xvj bin/micromamba
RUN mv bin/micromamba /usr/local/bin/
RUN micromamba create -y -p /opt/conda -c conda-forge readdy python=3.12
ENV PATH=/opt/conda/bin:$PATH

### PyPI
RUN python3 -m pip install 'numpy>=2.0.0' 'process-bigraph<1.0'

##
RUN mkdir /runtime
WORKDIR /runtime
RUN git clone https://github.com/biosimulators/bsew.git  /runtime
RUN python3 -m pip install -e /runtime

ENTRYPOINT ["python3", "/runtime/main.py"]
""".strip()
    fake_input_file = """
"python:pypi<numpy[>=2.0.0]>@numpy.random.rand"
"python:pypi<process-bigraph[<1.0]>@process_bigraph.processes.ParameterScan"
`python:conda<readdy>@readdy.ReactionDiffusionSystem`
""".strip()
    _build_dockerfile_for_necessary_env_exec(correct_answer, fake_input_file)


def test_build_dockerfile_for_necessary_env_conda() -> None:
    correct_answer = """
FROM ghcr.io/astral-sh/uv:python3.12-bookworm

RUN apt update
RUN apt upgrade -y
RUN apt install -y git curl

## Dependency Installs
### Conda
RUN mkdir /micromamba
RUN curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xvj bin/micromamba
RUN mv bin/micromamba /usr/local/bin/
RUN micromamba create -y -p /opt/conda -c conda-forge readdy python=3.12
ENV PATH=/opt/conda/bin:$PATH

### PyPI
# No PyPI dependencies!

##
RUN mkdir /runtime
WORKDIR /runtime
RUN git clone https://github.com/biosimulators/bsew.git  /runtime
RUN python3 -m pip install -e /runtime

ENTRYPOINT ["python3", "/runtime/main.py"]
""".strip()
    fake_input_file = """
`python:conda<readdy>@readdy.ReactionDiffusionSystem`
""".strip()
    _build_dockerfile_for_necessary_env_exec(correct_answer, fake_input_file)
