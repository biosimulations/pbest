from typing import Any

from bigraph_schema.core import Core
from process_bigraph import Composite


def comparison_result_dict_test(comparison_result: dict[str, Any]) -> None:
    for key in comparison_result:
        for compared_to in comparison_result[key]:
            if compared_to == key:
                assert float(comparison_result[key][compared_to]) == 0
            else:
                assert float(comparison_result[key][compared_to]) < 1e-6
                assert float(comparison_result[key][compared_to]) != 0


def test_mse_comparison(comparison_document: dict[Any, Any], fully_registered_core: Core) -> None:
    comparison_composite = Composite(config=comparison_document, core=fully_registered_core)
    comparison_result = comparison_composite.bridge_updates[-1]["result"]["species_mse"]
    comparison_result_dict_test(comparison_result)
