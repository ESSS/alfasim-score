from typing import Dict
from typing import List
from typing import Tuple
from typing import Union

import json
from barril.units import Array, Scalar
from pathlib import Path
from typing import Tuple, List, Dict

from alfasim_score.constants import CEMENT_NAME
from alfasim_score.units import DENSITY_UNIT
from alfasim_score.units import FRACTION_UNIT
from alfasim_score.units import LENGTH_UNIT
from alfasim_score.units import SPECIFIC_HEAT_UNIT
from alfasim_score.units import THERMAL_CONDUCTIVITY_UNIT
from alfasim_score.units import THERMAL_EXPANSION_UNIT
from alfasim_score.units import YOUNG_MODULUS_UNIT


class ScoreInputReader:
    def __init__(self, score_filepath: Path):
        self.score_filepath = score_filepath
        with open(score_filepath) as f:
            self.input_content = json.load(f)

    def read_well_trajectory(self) -> Tuple[Array, Array]:
        """Read the arrays with the x and y positions."""
        x = [entry["displacement"] for entry in self.input_content["trajectory"]["data"]]
        y = [-entry["vertical_depth"] for entry in self.input_content["trajectory"]["data"]]
        return Array(x, LENGTH_UNIT), Array(y, LENGTH_UNIT)

    def read_tubing_materials(self) -> List[Dict[str, Union[Scalar, str]]]:
        """Read the data for the tubings from SCORE input file."""
        tubing_data = []
        for section in self.input_content["operation"]["tubing_string"]["string_sections"]:
            thermal_property = section["pipe"]["grade"]["thermomechanical_property"]
            tubing_data.append(
                {
                    "name": section["pipe"]["grade"]["name"],
                    "density": Scalar(thermal_property["density"], DENSITY_UNIT),
                    "thermal_conductivity": Scalar(
                        thermal_property["thermal_conductivity"], THERMAL_CONDUCTIVITY_UNIT
                    ),
                    "specific_heat": Scalar(thermal_property["specific_heat"], SPECIFIC_HEAT_UNIT),
                    "thermal_expansion": Scalar(
                        thermal_property["thermal_expansion_coefficient"], THERMAL_EXPANSION_UNIT
                    ),
                    "young_modulus": Scalar(thermal_property["e"], YOUNG_MODULUS_UNIT),
                    "poisson_ratio": Scalar(thermal_property["nu"], FRACTION_UNIT),
                }
            )
        return tubing_data

    def read_cement_material(self) -> List[Dict[str, Union[Scalar, str]]]:
        """
        Read the data for the cement from SCORE input file.
        This method assumes all configured cement properties are the same and that
        the first_slurry and second_slurry have the same properties.
        """
        properties = self.input_content["well_strings"][0]["cementing"]["first_slurry"][
            "thermomechanical_property"
        ]
        return [
            {
                "name": CEMENT_NAME,
                "density": Scalar(properties["density"], DENSITY_UNIT),
                "thermal_conductivity": Scalar(
                    properties["thermal_conductivity"], THERMAL_CONDUCTIVITY_UNIT
                ),
                "specific_heat": Scalar(properties["specific_heat"], SPECIFIC_HEAT_UNIT),
                "thermal_expansion": Scalar(
                    properties["thermal_expansion_coefficient"], THERMAL_EXPANSION_UNIT
                ),
                "young_modulus": Scalar(properties["e"], YOUNG_MODULUS_UNIT),
                "poisson_ratio": Scalar(properties["nu"], FRACTION_UNIT),
            }
        ]

    def read_lithology_materials(self) -> List[Dict[str, Union[Scalar, str]]]:
        """Read the data for the lithologies from SCORE input file."""
        lithology_data = []
        for lithology in self.input_content["lithologies"]:
            properties = lithology["thermomechanical_property"]
            lithology_data.append(
                {
                    "name": lithology["display_name"],
                    "density": Scalar(properties["density"], DENSITY_UNIT),
                    "thermal_conductivity": Scalar(
                        properties["thermal_conductivity"], THERMAL_CONDUCTIVITY_UNIT
                    ),
                    "specific_heat": Scalar(properties["specific_heat"], SPECIFIC_HEAT_UNIT),
                    # expansion in the file has null value and APB assumes 0.0 for this parameter
                    "thermal_expansion": Scalar(0.0, THERMAL_EXPANSION_UNIT),
                    "young_modulus": Scalar(properties["e"], YOUNG_MODULUS_UNIT),
                    "poisson_ratio": Scalar(properties["nu"], FRACTION_UNIT),
                }
            )
        return lithology_data

    # TODO: implement the casing parser
    def read_casings() -> List[Dict[str, Scalar | str]]:
        return []

    def read_tubing(self) -> List[Dict[str, Scalar | str]]:
        """"Read the data for the tubing from SCORE input file"""
        casing_data = []
        for section in self.input_content["operation"]["tubing_string"]["string_sections"]:
            outer_radius = section["pipe"]["od"] / 2.0
            thickness = section["pipe"]["wt"]
            inner_diameter = 2.0 * (outer_radius - thickness)
            casing_data.append(
                {
                    "top_md": Scalar(section["top_md"], LENGTH_UNIT, "length"),
                    "base_md": Scalar(section["base_md"], LENGTH_UNIT, "length"),
                    "inner_diameter": Scalar(inner_diameter, DIAMETER_UNIT, "diameter"),
                    "outer_diameter": Scalar(section["od"], DIAMETER_UNIT, "diameter"),
                    "material": section["pipe"]["grade"]["name"]
                }
            )
        return casing_data

    def read_packers(self) -> List[Dict[str, Scalar | str]]:
        """"Read the data for the packers from SCORE input file"""
        packer_data = []
        for component in self.input_content["operation"]["tubing_string"]["components"]:
            if component["component"]["type"] == "PACKER":
                packer_data.append(
                    {
                        "name": component["name"],
                        "position": Scalar(component["depth"], LENGTH_UNIT, "length"),
                        # TODO: get material above from somewhere else
                        "material_above": "",
                    }
                )
        return packer_data

    # TODO: implement the open holes parser
    def read_open_hole(self) -> List[Dict[str, Scalar | str]]:
        return []