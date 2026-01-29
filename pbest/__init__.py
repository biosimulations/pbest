standard_types = {
    "numeric_result": {
        "time": "list[float]",
        "columns": "list[string]",
        "values": "list[list[float]]",
        # 'n_spacial_dimensions': 'tuple[int, int]'
    },
    "numeric_results": "map[numeric_result]",
    "columns_of_interest": "list[string]",
    # ReaDDy related types
    "particle": {
        "type_name": "string",
        "position": "tuple[float,float,float]",
        "neighbor_ids": "list[integer]",
        "_apply": "set",
    },
    "topology": {"type_name": "string", "particle_ids": "list[integer]", "_apply": "set"},
}
__all__ = ["run_experiment", "standard_types"]
from pbest.main import run_experiment  # noqa: E402
