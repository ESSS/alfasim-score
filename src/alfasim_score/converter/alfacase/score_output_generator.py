from typing import Any
from typing import Dict
from typing import List

import json
import numpy as np
from alfasim_sdk import CaseDescription
from alfasim_sdk import CaseOutputDescription
from alfasim_sdk import GlobalTrendDescription
from alfasim_sdk import LengthAndElevationDescription
from alfasim_sdk import OutputAttachmentLocation
from alfasim_sdk import PipeDescription
from alfasim_sdk import ProfileDescription
from alfasim_sdk import ProfileOutputDescription
from alfasim_sdk import TrendsOutputDescription
from alfasim_sdk import WellDescription
from alfasim_sdk.result_reader import Results
from barril.units import Scalar
from pathlib import Path

from alfasim_score.common import AnnulusLabel
from alfasim_score.constants import WELLBORE_NAME
from alfasim_score.units import LENGTH_UNIT
from alfasim_score.units import PRESSURE_UNIT
from alfasim_score.units import TEMPERATURE_UNIT


class ScoreOutputGenerator:
    def __init__(
        self,
        results_path: Path,
        well_start_position: Scalar,
        active_annuli: List[AnnulusLabel] = [],
    ):
        self.results_path = results_path
        self.well_start_position = well_start_position
        self.active_annuli = active_annuli
        self.element_name = WELLBORE_NAME

    def _generate_output_results(self) -> Dict[str, Any]:
        """Create data for the output results."""
        annuli_temperature_profiles = [
            f"annulus_{annuli_label.value}_temperature" for annuli_label in self.active_annuli
        ]
        annuli_pressure_profiles = [
            f"annulus_{annuli_label.value}_pressure" for annuli_label in self.active_annuli
        ]
        tubing_profiles = [
            "pressure",
            "mixture temperature",
        ]
        results = Results(self.results_path)
        measured_depths = self.well_start_position.GetValue(LENGTH_UNIT) + np.array(
            results.get_profile_curve("pressure", self.element_name, -1).domain.GetValues("m")
        )

        # build annuli output data
        annuli_output: Dict[str, Any] = {}
        annulus_index = 0
        for temperature_profile_name, pressure_profile_name in zip(
            annuli_temperature_profiles, annuli_pressure_profiles
        ):
            annuli_output[str(annulus_index)] = {}
            annuli_output[str(annulus_index)]["MD"] = measured_depths.tolist()
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

        # build production tubing output data
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
        return {
            "annuli": annuli_output,
            "MD": measured_depths.tolist(),
            "production_tubing": production_tubing,
        }

    def generate_output_file(self, output_filepath: Path) -> None:
        """Create the output file for SCORE."""
        json_data = json.dumps(self._generate_output_results(), indent=2)
        output_filepath.write_text(json_data, encoding="utf-8")
