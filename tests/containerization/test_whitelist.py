# import os
# import tempfile
# import zipfile
#
# import pytest
#
# from pbest.containerization.container_constructor import generate_container_def_file as run_pbest
# from pbest.utils.input_types import ContainerizationEngine, ContainerizationTypes, ExecutionProgramArguments
#
# fake_input_file = """
# "python:pypi<numpy[>=2.0.0]>@numpy.random.rand"
# "python:pypi<process-bigraph[<1.0]>@process_bigraph.processes.ParameterScan"
# """.strip()
#
# fake_input_file_2 = """
# "python:secret_protocol<numpy[>=2.0.0]>@totally.not.malicious
# "python:pypi<process-bigraph[<1.0]>@process_bigraph.processes.ParameterScan"
# """.strip()
#
#
# def test_whitelist_rejects_invalid_whitelist_appropriately():
#     with pytest.raises(ValueError):
#         _perform_execution_with_whitelist(fake_input_file, "")
#
#
# def test_whitelist_rejects_untrusted_package_from_valid_whitelist_appropriately():
#     valid_whitelist = """
# pypi:process-bigraph
# """.strip()
#     with pytest.raises(ValueError):
#         _perform_execution_with_whitelist(fake_input_file, valid_whitelist)
#
#
# def test_whitelist_rejects_unknown_source_from_valid_whitelist_appropriately():
#     valid_whitelist_with_invalid_source = """
# pypi::process-bigraph
# pypi::numpy
# """.strip()
#     with pytest.raises(ValueError):
#         _perform_execution_with_whitelist(fake_input_file_2, valid_whitelist_with_invalid_source)
#
#
# def test_whitelist_approves_appropriately():
#     valid_whitelist = """
# pypi::numpy
# pypi::process-bigraph
# """.strip()
#     _perform_execution_with_whitelist(fake_input_file, valid_whitelist)
#
#
# def _perform_execution_with_whitelist(input_pbif_as_string: str, whitelist_str: str):
#     correct_answer = """
# FROM ghcr.io/astral-sh/uv:python3.12-bookworm
#
# RUN apt update
# RUN apt upgrade -y
# RUN apt install -y git curl
#
# ## Dependency Installs
# ### Conda
# # No conda dependencies!
#
# ### PyPI
# RUN python3 -m pip install 'numpy>=2.0.0' 'process-bigraph<1.0'
#
# ##
# RUN mkdir /runtime
# WORKDIR /runtime
# RUN git clone https://github.com/biosimulators/bsew.git  /runtime
# RUN python3 -m pip install -e /runtime
#
# ENTRYPOINT ["python3", "/runtime/main.py"]
# """.strip()
#     with tempfile.TemporaryDirectory() as tmpdir:
#         # whitelist_file_path = os.path.join(tmpdir, "whitelist.txt")
#         whitelist_tokens = whitelist_str.strip().split("\n")
#         zip_path = os.path.join(tmpdir, "inputArchive.omex")
#         with zipfile.ZipFile(zip_path, "a") as zip_ref:
#             zip_ref.writestr("inputFile.pbif", input_pbif_as_string)
#         test_args = ExecutionProgramArguments(
#             zip_path, tmpdir, whitelist_tokens, ContainerizationTypes.SINGLE, ContainerizationEngine.DOCKER
#         )
#         run_bsedic(test_args)
#         output_dockerfile = os.path.join(tmpdir, "Dockerfile")
#         with open(output_dockerfile) as results_file:
#             results = results_file.read()
#         assert results == correct_answer
