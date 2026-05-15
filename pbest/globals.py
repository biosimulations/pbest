import logging

from bigraph_schema import Core
from pbsim_common import standard_types
from process_bigraph import allocate_core

logger = logging.getLogger(__name__)
TRACE_LEVEL_NUM = 5
logging.addLevelName(TRACE_LEVEL_NUM, "TRACE")

loaded_core: Core | None = None


def set_logging_config(level: str) -> None:
    logging.basicConfig(level=level)


def get_trace_level() -> int:
    return TRACE_LEVEL_NUM


def get_loaded_core() -> Core:
    global loaded_core
    if loaded_core is None:
        loaded_core = allocate_core()
        for k, i in standard_types.items():
            loaded_core.register_type(k, i)
    logger.log(level=get_trace_level(), msg=f"Link registry in use: {loaded_core.link_registry}")
    return loaded_core
