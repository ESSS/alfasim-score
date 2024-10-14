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


def generate_output_results(
    results_path: Path, element_name: str = WELLBORE_NAME, active_annuli: list[str] = ["a"]
) -> Dict[str, Any]:
    results = Results(results_path)
    annuli_temperature_profiles = [
        f"annulus_{annuli_label}_temperature" for annuli_label in active_annuli
    ]
    annuli_pressure_profiles = [
        f"annulus_{annuli_label}_pressure" for annuli_label in active_annuli
    ]
    tubing_profiles = [
        "pressure",
        "mixture temperature",
    ]

    # TODO: check if need this
    # global_trends_list = [str(trend) for trend in results.list_global_trends()]
    # time_step = results.get_global_trend_curve("timestep")
    # count = len(time_step.image)
    # expected_profiles_list = [
    #     f"{profile_name}@{element_name}(timesteps={count})" for profile_name in EXPECTED_PROFILES
    # ]
    # profiles_list = [str(profile) for profile in results.list_profiles()]
    # assert set(profiles_list) == set(expected_profiles_list)

    # TODO: check domain values are equal for all profiles (annulus can end before the end of the well domain...)
    # TODO: add the waterdepth + air gap
    measured_depths = results.get_profile_curve("pressure", element_name, -1).domain.GetValues("m")

    # build annuli data
    annuli_output: Dict[str, Any] = {}
    annulus_index = 0
    for temperature_profile_name, pressure_profile_name in zip(
        annuli_temperature_profiles, annuli_pressure_profiles
    ):
        annuli_output[str(annulus_index)] = {}
        annuli_output[str(annulus_index)]["MD"] = measured_depths.tolist()
        temperature = {}
        temperature["start"] = (
            results.get_profile_curve(temperature_profile_name, element_name, 0)
            .image.GetValues(TEMPERATURE_UNIT)
            .tolist()
        )
        temperature["final"] = (
            results.get_profile_curve(temperature_profile_name, element_name, -1)
            .image.GetValues(TEMPERATURE_UNIT)
            .tolist()
        )
        pressure = {}
        pressure["start"] = (
            results.get_profile_curve(pressure_profile_name, element_name, 0)
            .image.GetValues(PRESSURE_UNIT)
            .tolist()
        )
        pressure["final"] = (
            results.get_profile_curve(pressure_profile_name, element_name, -1)
            .image.GetValues(PRESSURE_UNIT)
            .tolist()
        )
        annuli_output[str(annulus_index)]["temperature"] = temperature
        annuli_output[str(annulus_index)]["pressure"] = pressure
        annulus_index += 1
    production_tubing = {
        "temperature": {
            "final": (
                results.get_profile_curve("mixture temperature", element_name, -1)
                .image.GetValues(TEMPERATURE_UNIT)
                .tolist()
            )
        },
        "pressure": {
            "final": (
                results.get_profile_curve("pressure", element_name, -1)
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
