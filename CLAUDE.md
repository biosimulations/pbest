# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

PBest (Process Bigraph Extensible Simulation Toolkit) is a Python library + CLI for running
[process-bigraph](https://github.com/vivarium-collective/process-bigraph) simulation documents
either locally or on a remote HPC (via a [Compose-API](https://github.com/biosimulations/compose-api)
server, default `https://compose.cam.uchc.edu`), and for generating container definitions that
reproduce the simulator environment those documents need.

## Commands

Dependency management is `uv`; every task has a `Makefile` target. `.DEFAULT_GOAL := help`, so a
bare `make` prints the annotated target list.

| Target | Runs | Notes |
| --- | --- | --- |
| `make install` | `uv sync` + `uv run pre-commit install` | First-time setup |
| `make check` | `uv lock --locked` → `pre-commit run -a` (ruff, ruff-format, file hygiene) → `mypy` → `deptry .` | The lint/typecheck gate; CI runs exactly this |
| `make test` | `pytest --cov --cov-config=pyproject.toml --cov-report=xml` | See caveats below |
| `make docs` | `mkdocs serve` | Live docs preview |
| `make docs-test` | `mkdocs build -s` | Strict build; fails on warnings |
| `make build` | `clean-build`, then `uvx --from build pyproject-build --installer uv` | Wheel into `dist/` |
| `make clean-build` | Removes `dist/` | |
| `make publish` | `./publish.sh` | Interactive; see Release below |
| `make build-and-publish` | `build` then `publish` | |
| `make help` | Prints targets with their `##` descriptions | Default goal |

`make check` is all-or-nothing. To run one piece while iterating:

```bash
uv run ruff check pbest/        # lint only (note: ruff is configured with fix = true)
uv run ruff format .            # formatter only
uv run mypy                     # types only (files = ["pbest"]; tests/ is not checked)
uv run deptry .                 # unused/missing dependency scan
uv run pre-commit run -a        # every hook, no mypy/deptry
```

Running tests directly:

```bash
uv run python -m pytest tests                                   # all
uv run python -m pytest tests/standard_tools/test_builder.py    # one file
uv run python -m pytest tests/execution/test_batch.py::test_batch_run_remote_experiment_and_wait
```

Test environment caveats:
- `tests/containerization/test_container_execution.py` is `skipif`'d unless a Docker daemon is
  reachable; it builds the generated Dockerfile with `docker buildx` for `linux/amd64`, which is slow.
- `tests/execution/` and parts of `tests/standard_tools/test_harmony.py` submit real jobs to the
  remote Compose-API and poll SLURM; they need network access and can take minutes.
- Async tests are marked `@pytest.mark.asyncio` (pytest-asyncio).
- `tests/conftest.py` star-imports `tests/fixtures/pb.py`; `comparison_document` is `autouse`.

CI (`.github/workflows/ci-test.yml`) runs `make check` plus pytest + mypy on Python 3.12.

Release: `make build-and-publish` runs `publish.sh`, which requires a clean working tree, prompts for
a version, **rewrites the `pbest_tag` default in `pbest/containerization/container_constructor.py`
via sed**, then tags, pushes and `uv publish`es. That tag is what the generated Dockerfile clones,
so the version in `pyproject.toml`, the git tag, and `pbest_tag` must stay in lockstep.

## Architecture

### The document (PBG) is the unit of work

Everything flows through a process-bigraph document — a JSON dict (`.pbg` file, or bundled inside an
`.omex`/zip archive) whose `state` maps node names to `{_type: process|step, address, config,
inputs, outputs}`. `address` names the implementing Python callable, e.g.
`local:pbsim_common.simulators.tellurium_process.TelluriumUTCStep`.

`pbest/globals.py::get_loaded_core()` is a lazily-built process-bigraph `Core` singleton registered
with `pbsim_common.standard_types`. Anything that instantiates a `Composite` must go through it.

### Four subsystems under `pbest/`

- **`cli/`** — `main.py::cli_tool` defines two subcommands, `run` and `containerize`. Each has an
  `add_args`/`parse_*_args` pair in `cli/parsing/` producing a frozen pydantic dataclass from
  `cli/types.py`, which the handler in `cli/` consumes. Note the parsers call
  `parser.parse_args()` on the *top-level* parser, not the subparser.
- **`execution/local.py`** — `run_experiment()` is the single funnel that both the CLI and the
  container entrypoint reach. It resolves the schema (`.pbg` JSON, in-memory dict, or extracted from
  `.omex`), builds a `Composite`, runs it for `interval`, writes emitter results as
  `results_<date>.pber` and final state as `state_<date>.pbg` into a tempdir, and copies that tempdir
  into the output directory.
- **`execution/remote/`** — `utils._normalize_pbg_paths()` walks the PBG dict, finds any string value
  that is an existing file path, copies that file into a new `experiment.omex` zip, and rewrites the
  value to the bare filename — this is what makes a locally-authored document portable to HPC.
  `single.py` submits one experiment; `batch.py` submits many with `batch_submission=True` and then
  polls `get_simulations_status_batch` on a 2 s interval until every `HpcRun` reaches a terminal
  `JobStatus`, downloading and unzipping each completed result.
- **`containerization/container_constructor.py`** — builds a Dockerfile from
  `generic_container.jinja` (uv base image + micromamba env at `/micromamba_env/runtime_env`, pip and
  conda install lines generated per dependency, entrypoint `pbest/main.py`). Apptainer/Singularity
  output is produced by round-tripping the Dockerfile through spython's `DockerParser` →
  `SingularityWriter`. Dependencies default to `_default_registry_deps()`, which fetches the
  BioSimulations registry JSON at
  `https://raw.githubusercontent.com/biosimulations/registry/refs/heads/dev/registry.json`.

Supporting modules: `utils/builder.py` (`CompositeBuilder` — programmatic PBG construction, including
`add_parameter_scan` which cross-products config/state values into many steps),
`utils/experiment_archive.py` (pull the PBG out of an `.omex`/`.zip`),
`dependency_resolution/discovery.py` (parse the
`python:{source}<{package}[{version}]>@{module.path}` address protocol out of a document, validate it
against a whitelist, and rewrite those addresses to `local:{module.path}` — the intended path for
deriving container dependencies from a document, currently returning empty dependency lists).

### CLI shape

```bash
pbest run <file.pbg|file.omex> [-o OUT_DIR] [-n INTERVAL] [-v]
pbest containerize [-i INPUT] [-t docker|apptainer|singularity|both] [-o OUT_DIR] [-v]
```

`containerize` with no `-i` falls back to the remote registry dependency list. Output files are
written as `<OUT_DIR>/<ENGINE_NAME>` with a `_N` suffix if the name is taken.

## Conventions

- Ruff, line length 120, with `S`(bandit), `B`, `SIM`, `TRY`, `UP`, `RUF` and more enabled. `TRY003`
  is active, which is why exception messages are assigned to a local first
  (`err_msg = ...; raise ValueError(err_msg)`) rather than inlined in the `raise` — match that, or
  lint fails.
- Note `[tool.ruff] target-version = "py39"` contradicts `requires-python = ">=3.12"`. Ruff therefore
  reports `match` statements (e.g. `utils/builder.py`, `container_constructor.py`) as
  `invalid-syntax`. Don't rewrite working `match` blocks to appease it — the target-version is the bug.
- mypy runs with `disallow_untyped_defs = true` over `pbest/` — every function there needs
  annotations. `tests/` is not type-checked.
- Input/output shapes are frozen pydantic dataclasses in `pbest/utils/input_types.py`
  (`ExperimentSubmission`, `OmexExperimentSubmission`, `ExperimentDependency`,
  `ExperimentPrimaryDependencies`, `ContainerizationEngine`).
- Untyped third-party imports are silenced per-module in `[[tool.mypy.overrides]]`; add a new block
  there rather than scattering `# type: ignore`.
