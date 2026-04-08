import copy
from enum import Enum
from typing import Any, Optional

from bigraph_schema import Core
from process_bigraph import Composite


class CompositeBuilder:
    class CompositeType(Enum):
        CONFIG = "config"
        STATE = "state"

    class _PathNavigation:
        def __init__(self, path: list[str], values: list[Any], composite_type: Any) -> None:
            self.path: list[str] = path
            self.values: list[Any] = values
            self.composite_type: CompositeBuilder.CompositeType = composite_type

    def __init__(self) -> None:
        self.step_number: int = 0
        self.state: dict[str, Any] = {}

    def _allocate_step_key(self, step_name: str) -> str:
        step_key = f"{step_name}_{self.step_number}"
        self.step_number += 1
        return step_key

    def add_step(
        self, address: str, config: dict[str, str | int], inputs: dict[str, Any], outputs: dict[str, Any]
    ) -> "CompositeBuilder":
        new_step_key = self._allocate_step_key(address)
        self.state[new_step_key] = {
            "_type": "step",
            "address": address,
            "config": config,
            "inputs": inputs,
            "outputs": outputs,
        }
        return self

    def add_process(
        self, address: str, config: dict[str, str | int], inputs: dict[str, Any], outputs: dict[str, Any]
    ) -> "CompositeBuilder":
        new_step_key = self._allocate_step_key(address)
        self.state[new_step_key] = {
            "_type": "process",
            "address": address,
            "config": config,
            "inputs": inputs,
            "outputs": outputs,
        }
        return self

    def add_comparison_step(self, comparison_name: str, store_with_values: list[str]) -> "CompositeBuilder":
        comparison_step_key = self._allocate_step_key("comparison_step")
        self.state[comparison_step_key] = {
            "_type": "step",
            "address": "local:pbsim_common.comparison.MSEComparison",
            "config": {},
            "inputs": {
                "results": store_with_values,
            },
            "outputs": {
                "comparison_result": ["comparison_results", comparison_name],
            },
        }
        return self

    def _deconstruct_dictionary(
        self, base_path: list[str], dict_values: dict[str, Any], composite_type: CompositeType
    ) -> list[_PathNavigation]:
        keys_of_interest = list(dict_values.keys())
        paths_to_navigate: list[CompositeBuilder._PathNavigation] = []
        for fixated_key in keys_of_interest:
            new_path = [*base_path, fixated_key]
            if type(dict_values[fixated_key]) is dict:
                paths_to_navigate += self._deconstruct_dictionary(new_path, dict_values[fixated_key], composite_type)
            elif type(dict_values[fixated_key]) is list:
                paths_to_navigate.append(self._PathNavigation(new_path, dict_values[fixated_key], composite_type))
            else:
                err_msg = (
                    f"Invalid type for combination for {dict_values} at {fixated_key}: {type(dict_values[fixated_key])}"
                )
                raise TypeError(err_msg)
        return paths_to_navigate

    def add_parameter_scan(
        self,
        address: str,
        config: dict[Any, Any],
        input_mappings: dict[str, list[str]],
        is_step: bool = True,
        config_values: Optional[dict[str, Any]] = None,
        state_values: Optional[dict[str, Any]] = None,
    ) -> "CompositeBuilder":
        edge_type = "step" if is_step else "process"
        config_values = config_values or {}
        state_values = state_values or {}
        param_step_key = self._allocate_step_key("parameter_scan")
        self.state[param_step_key] = {}
        self.state[param_step_key]["results"] = {}
        self.state[param_step_key]["inputs"] = {}

        parameter_values: list[CompositeBuilder._PathNavigation] = self._deconstruct_dictionary(
            [], state_values, CompositeBuilder.CompositeType.STATE
        ) + self._deconstruct_dictionary([], config_values, CompositeBuilder.CompositeType.CONFIG)

        def combinatorics(current_step: dict, all_paths: list[CompositeBuilder._PathNavigation]) -> None:
            path_of_focus = all_paths[-1]
            for cur_value in path_of_focus.values:
                # put appropriate values
                sub_struct = None
                match path_of_focus.composite_type:
                    case CompositeBuilder.CompositeType.CONFIG:
                        sub_struct = current_step[edge_type]["config"]
                    case CompositeBuilder.CompositeType.STATE:
                        sub_struct = current_step["state"]

                i = 0
                while i < len(path_of_focus.path):
                    if i == len(path_of_focus.path) - 1:
                        sub_struct[path_of_focus.path[i]] = cur_value
                    elif path_of_focus.path[i] not in sub_struct:
                        sub_struct[path_of_focus.path[i]] = {}
                    sub_struct = sub_struct[path_of_focus.path[i]]
                    i += 1

                # pass down as needed
                if len(all_paths) > 1:
                    combinatorics(current_step, all_paths[:-1])
                else:
                    step_key = self._allocate_step_key(address.split(":")[1])
                    current_step[edge_type]["outputs"]["result"] = ["results", step_key]
                    for k in current_step[edge_type]["inputs"]:
                        current_step[edge_type]["inputs"][k] = ["inputs", step_key]
                    self.state[param_step_key]["inputs"][step_key] = copy.deepcopy(current_step["state"])
                    self.state[param_step_key][step_key] = copy.deepcopy(current_step[edge_type])

        combinatorics(
            {
                "state": {},
                edge_type: {
                    "_type": edge_type,
                    "address": address,
                    "config": config,
                    "inputs": input_mappings,
                    "outputs": {"result": {}},
                },
            },
            parameter_values,
        )
        return self

    def get_builder_state(self) -> dict:
        return {"state": self.state}

    def run_composite(self, core: Core, interval: float, force_complete: bool = False) -> Composite:
        comp = Composite({"state": self.state}, core=core)
        comp.run(interval, force_complete)
        return comp
