from typing import Any
from typing import Dict
from typing import List

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
from pathlib import Path

from alfasim_score.constants import WELLBORE_NAME
from alfasim_score.units import LENGTH_UNIT
from alfasim_score.units import PRESSURE_UNIT
from alfasim_score.units import TEMPERATURE_UNIT

# TODO: move this to the generate_output_results
EXPECTED_PROFILES = [
    "pressure",
    "mixture temperature",
    # "interface_19_temperature",
]


# TODO: put this in a result generator class to convert alfasim result to SCORE
def generate_output_results(
    results_path: Path, element_name: str = WELLBORE_NAME, active_annuli: list[str] = ["a"]
) -> Dict[str, Any]:
    annuli_temperature_profiles = [
        f"annulus_{annuli_label}_temperature" for annuli_label in active_annuli
    ]
    annuli_pressure_profiles = [
        f"annulus_{annuli_label}_pressure" for annuli_label in active_annuli
    ]

    results = Results(results_path)
    global_trends_list = [str(trend) for trend in results.list_global_trends()]

    time_step = results.get_global_trend_curve("timestep")
    count = len(time_step.image)
    expected_profiles_list = [
        f"{profile_name}@{element_name}(timesteps={count})" for profile_name in EXPECTED_PROFILES
    ]

    # TODO: check if need this
    # profiles_list = [str(profile) for profile in results.list_profiles()]
    # assert set(profiles_list) == set(expected_profiles_list)

    # TODO: domain values are equal for all profiles
    # TODO: add the waterdepth + air gap
    measured_depths = results.get_profile_curve("pressure", element_name, -1).domain.GetValues("m")

    # TODO: remember to get only active annulus
    # build annuli data
    annuli_output: Dict[str, Any] = {}
    annulus_index = 0
    for temperature_profile_name, pressure_profile_name in zip(
        annuli_temperature_profiles, annuli_pressure_profiles
    ):
        annuli_output[str(annulus_index)] = {}
        annuli_output[str(annulus_index)]["MD"] = measured_depths.tolist()
        annuli_output[str(annulus_index)]["temperature"] = (
            results.get_profile_curve(temperature_profile_name, element_name, -1)
            .image.GetValues(TEMPERATURE_UNIT)
            .tolist()
        )
        annuli_output[str(annulus_index)]["pressure"] = (
            results.get_profile_curve(pressure_profile_name, element_name, -1)
            .image.GetValues(PRESSURE_UNIT)
            .tolist()
        )
        annulus_index += 1
    return {
        "annuli": annuli_output,
        "MD": measured_depths.tolist(),
        # TODO: fill data for tubing here
        "production_tubing": {},
    }
