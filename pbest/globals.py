from process_bigraph import ProcessTypes, generate_core

from pbest import standard_types

loaded_core: ProcessTypes | None = None


def get_loaded_core() -> ProcessTypes:
    global loaded_core
    if loaded_core is None:
        loaded_core = generate_core()
        for k, i in standard_types.items():
            loaded_core.register(k, i)
    return loaded_core


def reload_core() -> ProcessTypes:
    global loaded_core
    loaded_core = generate_core()
    for k, i in standard_types.items():
        loaded_core.register(k, i)
    return loaded_core
