import os.path

import numpy as np
import basico as bsc
import pandas as pd
from basico.model_info import T
from process_bigraph import Process, Composite, pf, Step
import matplotlib.pyplot as plt
from roadrunner import RoadRunner
import tellurium as te


class Legacy_RunBasicSBMLTimeCourseSimulation(Step):
    config_schema = {
        'output_dir': {
            '_type': 'string',
            '_default': ''
        }
    }

    def __init__(self, config, core):
        super().__init__(config, core)


    def initialize(self, config):
        ######################
        if config['output_dir'] is None:
            raise ValueError('`output_dir` cannot be None')
        output_dir: str = os.path.abspath(os.path.expanduser(config['output_dir']))
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        self.output_dir = output_dir
        ######################

        return

    def update(self, state):
        sbml_file_path: str = state['sbml_file_path']
        num_data_points: int = state["num_data_points"]
        starting_time: float = state["starting_time"]
        duration: float = state["duration"]
        bsc.load_model(sbml_file_path)
        results: pd.DataFrame = bsc.run_time_course(starting_time, duration, num_data_points)
        results.plot()
        plt.savefig(os.path.join(self.output_dir, "plot.pdf"))
        results.to_csv(os.path.join(self.output_dir, "report.csv"))
        return {}

    def inputs(self):
        return {
            "sbml_file_path" : "string",
            "num_data_points": "integer",
            "starting_time": "float",
            "duration": "float",
        }

    def outputs(self):
        return {}

class Legacy_RunBasicCPSTimeCourseSimulation(Step):
    def update(self, state):
        return {}

    def inputs(self):
        return {
            "cps_file_path" : "string"
        }

    def outputs(self):
        return {}

class TelluriumTimeCourseStep(Step):
    config_schema = {
        'output_dir': {
            '_type': 'string',
            '_default': ''
        }
    }

    def __init__(self, config, core):
        super().__init__(config, core)
        self.runner: RoadRunner = None
        self.output_dir: str = ""

    def initialize(self, config):
        sbml_file_path: str = os.path.abspath(os.path.expanduser(config['sbml_file_path']))
        if not os.path.exists(sbml_file_path):
            raise FileNotFoundError(sbml_file_path)

        if config['output_dir'] is None:
            raise ValueError('`output_dir` cannot be None')
        output_dir = os.path.abspath(os.path.expanduser(config['output_dir']))
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        self.output_dir = output_dir

    def update(self, state):
        sbml_file_path: str = state["sbml_file_path"]
        num_data_points: int = state["num_data_points"]
        starting_time: float = state["starting_time"]
        end_time: float = state["end_time"]
        output_file = self.output_dir + "/report.csv"
        runner = te.loadSBMLModel(sbml_file_path)
        runner.simulate(start=starting_time, end=end_time, points=num_data_points, output_file=output_file)
        return {}

    def inputs(self):
        return {
            "sbml_file_path": "string",
            "num_data_points": "integer",
            "starting_time": "float",
            "end_time": "float",
        }

    def outputs(self):
        return {}
