import os
import re
import shutil
from typing import Optional

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
            deps_install_command += f"RUN python3 -m pip install '{pypi_deps[p]}'"
        elif p != len(pypi_deps) - 1:
            deps_install_command += f" '{pypi_deps[p]}'"
        else:
            deps_install_command += f" '{pypi_deps[p]}'\n"
    for c in experiment_deps.get_conda_dependencies():
        deps_install_command += f"RUN micromamba update -c conda-forge -p /micromamba_env/runtime_env {c} python=3.12\n"

    with open(__file__.rsplit(os.sep, maxsplit=1)[0] + f"{os.sep}generic_container.jinja") as f:
        template = Template(f.read())
        templated_container = template.render(
            additional_execution_tools=experiment_deps.manager_installation_string(),
            dependencies_to_install=deps_install_command,
        )

    return ContainerizationFileRepr(representation=templated_container)


# Due to an assumption that we can not have all dependencies included
# in the same python environment, we need a solid address protocol to assume.
# going with: `python:{source}<{package_name}>[{version_statement}]@{python_module_path_to_class_def}`
#         ex: "python: pypi<copasi-basico[~0.8]>@basico.model_io.load_model" (if this was a class, and not a function)
def determine_dependencies(  # noqa: C901
    string_to_search: str, whitelist_entries: Optional[list[str]] = None
) -> tuple[ExperimentPrimaryDependencies, str]:
    whitelist_mapping: dict[str, set[str]] | None
    if whitelist_entries is not None:
        whitelist_mapping = {}
        for whitelist_entry in whitelist_entries:
            entry = whitelist_entry.split("::")
            if len(entry) != 2:
                err_msg = f"invalid whitelist entry: {whitelist_entry}"
                raise ValueError(err_msg)
            source, package = (entry[0], entry[1])
            if source not in whitelist_mapping:
                whitelist_mapping[source] = set()
            whitelist_mapping[source].add(package)
    else:
        whitelist_mapping = None
    source_name_legal_syntax = r"[\w\-]+"
    package_name_legal_syntax = r"[\w\-._~:/?#[\]@!$&'()*+,;=%]+"  # package or git-http repo name
    version_string_legal_syntax = (
        r"\[([\w><=~!*\-.]+)]"  # hard brackets around alphanumeric plus standard python version constraint characters
    )
    # stricter pattern of only legal python module names
    # (letters and underscore first character, alphanumeric and underscore for remainder); must be at least 1 char long
    import_name_legal_syntax = r"[A-Za-z_]\w*(\.[A-Za-z_]\w*)*"
    known_sources = ["pypi", "conda"]
    approved_dependencies: dict[str, list[str]] = {source: [] for source in known_sources}
    regex_pattern = f"python:({source_name_legal_syntax})<({package_name_legal_syntax})({version_string_legal_syntax})?>@({import_name_legal_syntax})"
    adjusted_search_string = str(string_to_search)
    matches = re.findall(regex_pattern, string_to_search)
    if len(matches) == 0:
        local_protocol_matches = re.findall(f"local:{import_name_legal_syntax}", string_to_search)
        if len(local_protocol_matches) == 0:
            err_msg = "No dependencies found in document; unable to generate environment."
            raise ValueError(err_msg)
        match_str_list: str = ",".join([str(match) for match in matches])
        if len(match_str_list) != 0:  # For some reason, we can get a single "match" that's empty...
            err_msg = f"Document is using the following local protocols: `{match_str_list}`; unable to determine needed environment."
            raise ValueError(err_msg)
    for match in matches:
        source_name = match[0]
        package_name = match[1]
        package_version = match[3]
        if source_name not in known_sources:
            err_msg = f"Unknown source `{source_name}` used; can not determine dependencies"
            raise ValueError(err_msg)
        dependency_str = f"{package_name}{package_version}".strip()
        if dependency_str in approved_dependencies[source_name]:
            continue  # We've already accounted for this dependency
        if whitelist_mapping is not None:
            # We need to validate against whitelist!
            if source_name not in whitelist_mapping:
                err_msg = f"Unapproved source `{source_name}` used; can not trust document"
                raise ValueError(err_msg)
            if package_name not in whitelist_mapping[source_name]:
                err_msg = f"`{package_name}` from `{source_name}` is not a trusted package; can not trust document"
                raise ValueError(err_msg)
        approved_dependencies[source_name].append(dependency_str)
        version_str = match[2] if package_version != "" else ""
        complete_match = f"python:{source_name}<{package_name}{version_str}>@{match[4]}"
        adjusted_search_string = adjusted_search_string.replace(complete_match, f"local:{match[4]}")
    return ExperimentPrimaryDependencies(
        approved_dependencies["pypi"], approved_dependencies["conda"]
    ), adjusted_search_string.strip()


def convert_dependencies_to_installation_string_representation(dependencies: list[str]) -> str:
    return "'" + "' '".join(dependencies) + "'"


def generate_container_def_file(
    original_program_arguments: ContainerizationProgramArguments,
) -> ContainerizationFileRepr:
    new_input_file_path: str
    input_is_archive = original_program_arguments.input_file_path.endswith(
        ".zip"
    ) or original_program_arguments.input_file_path.endswith(".omex")
    if input_is_archive:
        new_input_file_path = extract_archive_returning_pbif_path(
            original_program_arguments.input_file_path, str(original_program_arguments.working_directory)
        )
    else:
        new_input_file_path = os.path.join(
            str(original_program_arguments.working_directory),
            os.path.basename(original_program_arguments.input_file_path),
        )
        print(f"file copied to `{shutil.copy(original_program_arguments.input_file_path, new_input_file_path)}`")
    required_program_arguments = ContainerizationProgramArguments(
        input_file_path=new_input_file_path,
        containerization_type=original_program_arguments.containerization_type,
        containerization_engine=original_program_arguments.containerization_engine,
        working_directory=original_program_arguments.working_directory,
    )

    # load_local_modules()  # Collect Abstracts
    # TODO: Add feature - resolve abstracts

    # Determine Dependencies
    docker_template: ContainerizationFileRepr
    returned_template: ContainerizationFileRepr
    docker_template = formulate_dockerfile_for_necessary_env(
        required_program_arguments,
        experiment_deps=get_experiment_deps(),
    )
    returned_template = docker_template
    if required_program_arguments.containerization_type != ContainerizationTypes.NONE:
        if required_program_arguments.containerization_type != ContainerizationTypes.SINGLE:
            raise NotImplementedError("Only single containerization is currently supported")
        container_file_path: str
        container_file_path = os.path.join(str(original_program_arguments.working_directory), "Dockerfile")
        with open(container_file_path, "w") as docker_file:
            docker_file.write(docker_template.representation)
        if (
            required_program_arguments.containerization_engine == ContainerizationEngine.APPTAINER
            or required_program_arguments.containerization_engine == ContainerizationEngine.BOTH
        ):
            dockerfile_path = container_file_path
            container_file_path = os.path.join(str(original_program_arguments.working_directory), "singularity.def")
            dockerfile_parser = DockerParser(dockerfile_path)
            singularity_writer = SingularityWriter(dockerfile_parser.recipe)
            results = singularity_writer.convert()
            returned_template = ContainerizationFileRepr(representation=results)
            with open(container_file_path, "w") as container_file:
                container_file.write(results)
            if required_program_arguments.containerization_engine != ContainerizationEngine.BOTH:
                os.remove(dockerfile_path)
        print(f"Container build file located at '{container_file_path}'")

    # Reconstitute if archive
    if input_is_archive:
        base_name = os.path.basename(original_program_arguments.input_file_path)
        output_dir: str = (
            os.path.dirname(original_program_arguments.input_file_path)
            if original_program_arguments.working_directory is None
            else str(original_program_arguments.working_directory)
        )
        new_archive_path = os.path.join(output_dir, base_name)
        # Note: If no output dir is provided (dir is `None`), then input file WILL BE OVERWRITTEN
        target_dir = os.path.join(str(original_program_arguments.working_directory), base_name.split(".")[0])
        shutil.make_archive(new_archive_path, "zip", target_dir)
        shutil.move(new_archive_path + ".zip", new_archive_path)  # get rid of extra suffix
    return returned_template
