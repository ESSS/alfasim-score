from typing import Any
from typing import Dict
from typing import List

import numpy as np
from alfasim_sdk.result_reader import Results
from pathlib import Path

from alfasim_score.constants import TOTAL_WALLS
from alfasim_score.constants import WELLBORE_NAME
from alfasim_score.converter.alfacase.score_input_data import ScoreInputData
from alfasim_score.units import LENGTH_UNIT
from alfasim_score.units import PRESSURE_UNIT
from alfasim_score.units import TEMPERATURE_UNIT


class ScoreOutputBuilder:
    def __init__(
        self,
        score_input_data: ScoreInputData,
        score_output_filepath: Path,
    ):
        self.score_data = score_input_data
        self.score_output_filepath = score_output_filepath
        self.element_name = WELLBORE_NAME

    def _generate_annuli_output(self, results: Results, measured_depths: List) -> Dict[str, Any]:
        """Create data for the output results of annuli."""
        active_annuli = self.score_data.get_annuli_list()
        annuli_temperature_profiles = [
            f"annulus_{annuli_label.value}_temperature" for annuli_label in active_annuli
        ]
        annuli_pressure_profiles = [
            f"annulus_{annuli_label.value}_pressure" for annuli_label in active_annuli
        ]
        annuli_output: Dict[str, Any] = {}
        annulus_index = 0
        for temperature_profile_name, pressure_profile_name in zip(
            annuli_temperature_profiles, annuli_pressure_profiles
        ):
            annuli_output[str(annulus_index)] = {}
            annuli_output[str(annulus_index)]["MD"] = measured_depths
            temperature = {}
            temperature["start"] = (
                results.get_profile_curve(temperature_profile_name, self.element_name, 0)
                .image.GetValues(TEMPERATURE_UNIT)
                .tolist()
            )
            temperature["final"] = (
                results.get_profile_curve(temperature_profile_name, self.element_name, -1)
                .image.GetValues(TEMPERATURE_UNIT)
                .tolist()
            )
            pressure = {}
            pressure["start"] = (
                results.get_profile_curve(pressure_profile_name, self.element_name, 0)
                .image.GetValues(PRESSURE_UNIT)
                .tolist()
            )
            pressure["final"] = (
                results.get_profile_curve(pressure_profile_name, self.element_name, -1)
                .image.GetValues(PRESSURE_UNIT)
                .tolist()
            )
            annuli_output[str(annulus_index)]["temperature"] = temperature
            annuli_output[str(annulus_index)]["pressure"] = pressure
            annulus_index += 1
        return annuli_output

    def _generate_production_tubing_output(self, results: Results) -> Dict[str, Any]:
        """Create data for the output results of production tubing."""
        production_tubing = {
            "temperature": {
                "final": (
                    results.get_profile_curve("mixture temperature", self.element_name, -1)
                    .image.GetValues(TEMPERATURE_UNIT)
                    .tolist()
                )
            },
            "pressure": {
                "final": (
                    results.get_profile_curve("pressure", self.element_name, -1)
                    .image.GetValues(PRESSURE_UNIT)
                    .tolist()
                )
            },
        }
        return production_tubing

    def _generate_walls_output(self, results: Results, measured_depths: List) -> Dict[str, Any]:
        """Create data for the output results of walls."""
        walls_output: Dict[str, Any] = {}
        wall_index = 0
        # Score wall labels are inverted with respect to PWPA
        for wall_label in range(TOTAL_WALLS - 1, -1, -1):
            wall_name = f"wall_{wall_label}_temperature"
            wall = {}
            wall["MD"] = measured_depths
            wall_temperatures = results.get_profile_curve(
                wall_name, self.element_name, -1
            ).image.GetValues(TEMPERATURE_UNIT)
            # Ignore walls with negative dummy values from ALFAsim
            if not np.all(wall_temperatures < 0):
                wall["temperature"] = wall_temperatures.tolist()
                walls_output[str(wall_index)] = wall
                wall_index += 1
        return walls_output

    def generate_output_results(self, alfasim_results_filepath: Path) -> Dict[str, Any]:
        """Create data for the output results."""
        results = Results(alfasim_results_filepath)
        well_start_position = self.score_data.get_well_start_position().GetValue(LENGTH_UNIT)
        measured_depths = list(
            well_start_position
            + results.get_profile_curve("pressure", self.element_name, -1).domain.GetValues(
                LENGTH_UNIT
            )
        )
        return {
            "annuli": self._generate_annuli_output(results, measured_depths),
            "MD": measured_depths,
            "production_tubing": self._generate_production_tubing_output(results),
            "layers": self._generate_walls_output(results, measured_depths),
        }
