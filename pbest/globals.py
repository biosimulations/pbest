import logging

from bigraph_schema import Core
from pbsim_common.comparison import MSEComparison
from pbsim_common.simulators import TelluriumUTCStep, CopasiUTCStep, TelluriumSteadyStateStep
from process_bigraph import allocate_core

from pbest import standard_types

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
    return loaded_core
