from pathlib import Path

import docker
import pytest


def is_docker_present() -> bool:
    client = docker.from_env()
    try:
        client.ping()
        return True  # noqa: TRY300
    except Exception:
        return False

def test_root_dir_path() -> Path:
    return Path(__file__).parent.parent
