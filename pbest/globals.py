import logging

from bigraph_schema import Core
from pbsim_common import standard_types
from process_bigraph import allocate_core

logger = logging.getLogger(__name__)

loaded_core: Core | None = None


def set_logging_config(level: str) -> None:
    logging.basicConfig(level=level)


def get_loaded_core() -> Core:
    global loaded_core
    if loaded_core is None:
        loaded_core = allocate_core()
        for k, i in standard_types.items():
            loaded_core.register_type(k, i)
    logger.debug(f"Link registry in use: {loaded_core.link_registry}")
    return loaded_core
