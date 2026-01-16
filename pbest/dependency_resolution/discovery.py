import re
from typing import Optional

from pbest.utils.input_types import ExperimentPrimaryDependencies


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

