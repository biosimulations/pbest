import os
import shutil

from jinja2 import Template
from spython.main.parse.parsers import DockerParser  # type: ignore[import-untyped]
from spython.main.parse.writers import SingularityWriter  # type: ignore[import-untyped]

from pbest.utils.experiment_archive import extract_archive_returning_pbif_path
from pbest.utils.input_types import (
    ContainerizationEngine,
    ContainerizationFileRepr,
    ContainerizationProgramArguments,
    ContainerizationTypes,
    ExperimentPrimaryDependencies,
)

micromamba_env_path = "/micromamba_env/runtime_env"


def get_experiment_deps() -> ExperimentPrimaryDependencies:
    return ExperimentPrimaryDependencies(
        ["cobra", "tellurium", "numpy", "matplotlib", "scipy", "pb_multiscale_actin"],
        ["readdy"],
    )


def formulate_dockerfile_for_necessary_env(
    program_arguments: ContainerizationProgramArguments, experiment_deps: ExperimentPrimaryDependencies
) -> ContainerizationFileRepr:
    # pb_document_str: str
    deps_install_command: str = ""
    # with open(program_arguments.input_file_path) as pb_document_file:
    #     pb_document_str = pb_document_file.read()
    # experiment_deps, updated_document_str = determine_dependencies(pb_document_str, program_arguments.passlist_entries)

    pypi_deps = experiment_deps.get_pypi_dependencies()
    for p in range(len(pypi_deps)):
        if p == 0:
            deps_install_command += (
                f"RUN micromamba run -p {micromamba_env_path} python3 -m pip install '{pypi_deps[p]}'"
            )
        elif p != len(pypi_deps) - 1:
            deps_install_command += f" '{pypi_deps[p]}'"
        else:
            deps_install_command += f" '{pypi_deps[p]}'\n"
    for c in experiment_deps.get_conda_dependencies():
        deps_install_command += (
            f"RUN micromamba install -c conda-forge -p {micromamba_env_path} {c} python=3.12 --yes\n"
        )

    with open(__file__.rsplit(os.sep, maxsplit=1)[0] + f"{os.sep}generic_container.jinja") as f:
        template = Template(f.read())
        templated_container = template.render(
            additional_execution_tools=experiment_deps.manager_installation_string(),
            dependencies_to_install=deps_install_command,
            micromamba_env_path=micromamba_env_path,
        )

    return ContainerizationFileRepr(representation=templated_container)


def generate_container_def_file(
    og_args: ContainerizationProgramArguments,
) -> ContainerizationFileRepr:
    new_input_file_path: str
    input_is_archive = og_args.input_file_path.endswith(".zip") or og_args.input_file_path.endswith(".omex")
    if input_is_archive:
        new_input_file_path = extract_archive_returning_pbif_path(
            og_args.input_file_path, str(og_args.working_directory)
        )
    else:
        new_input_file_path = os.path.join(str(og_args.working_directory), os.path.basename(og_args.input_file_path))
        print(f"file copied to `{shutil.copy(og_args.input_file_path, new_input_file_path)}`")
    updated_args = ContainerizationProgramArguments(
        input_file_path=new_input_file_path,
        containerization_type=og_args.containerization_type,
        containerization_engine=og_args.containerization_engine,
        working_directory=og_args.working_directory,
    )

    # load_local_modules()  # Collect Abstracts
    # TODO: Add feature - resolve abstracts

    # Determine Dependencies
    docker_template: ContainerizationFileRepr
    returned_template: ContainerizationFileRepr
    docker_template = formulate_dockerfile_for_necessary_env(updated_args, experiment_deps=get_experiment_deps())
    returned_template = docker_template
    if updated_args.containerization_type != ContainerizationTypes.NONE:
        if updated_args.containerization_type != ContainerizationTypes.SINGLE:
            raise NotImplementedError("Only single containerization is currently supported")
        container_file_path: str
        container_file_path = os.path.join(str(og_args.working_directory), "Dockerfile")
        with open(container_file_path, "w") as docker_file:
            docker_file.write(docker_template.representation)
        if (
            updated_args.containerization_engine == ContainerizationEngine.APPTAINER
            or updated_args.containerization_engine == ContainerizationEngine.BOTH
        ):
            dockerfile_path = container_file_path
            container_file_path = os.path.join(str(og_args.working_directory), "singularity.def")
            dockerfile_parser = DockerParser(dockerfile_path)
            singularity_writer = SingularityWriter(dockerfile_parser.recipe)
            results = singularity_writer.convert()
            returned_template = ContainerizationFileRepr(representation=results)
            with open(container_file_path, "w") as container_file:
                container_file.write(results)
            if updated_args.containerization_engine != ContainerizationEngine.BOTH:
                os.remove(dockerfile_path)
        print(f"Container build file located at '{container_file_path}'")

    # Reconstitute if archive
    if input_is_archive:
        base_name = os.path.basename(og_args.input_file_path)
        output_dir: str = (
            os.path.dirname(og_args.input_file_path)
            if og_args.working_directory is None
            else str(og_args.working_directory)
        )
        new_archive_path = os.path.join(output_dir, base_name)
        # Note: If no output dir is provided (dir is `None`), then input file WILL BE OVERWRITTEN
        target_dir = os.path.join(str(og_args.working_directory), base_name.split(".")[0])
        shutil.make_archive(new_archive_path, "zip", target_dir)
        shutil.move(new_archive_path + ".zip", new_archive_path)  # get rid of extra suffix
    return returned_template
