from typing import Any
from typing import Dict
from typing import List
from typing import Union

import json
from barril.units import Array
from barril.units import Scalar
from pathlib import Path

from alfasim_score.common import AnnulusModeType
from alfasim_score.common import FluidType
from alfasim_score.common import LiftMethod
from alfasim_score.common import ModelFluidType
from alfasim_score.common import OperationType
from alfasim_score.common import WellItemFunction
from alfasim_score.common import WellItemType
from alfasim_score.constants import CEMENT_NAME
from alfasim_score.constants import CEMENT_PREFIX
from alfasim_score.constants import FORMATION_PREFIX
from alfasim_score.units import DENSITY_UNIT
from alfasim_score.units import DIAMETER_UNIT
from alfasim_score.units import FRACTION_UNIT
from alfasim_score.units import GAS_OIL_RATIO_UNIT
from alfasim_score.units import LENGTH_UNIT
from alfasim_score.units import PRESSURE_UNIT
from alfasim_score.units import SPECIFIC_HEAT_UNIT
from alfasim_score.units import STD_VOLUMETRIC_FLOW_RATE_UNIT
from alfasim_score.units import TEMPERATURE_UNIT
from alfasim_score.units import THERMAL_CONDUCTIVITY_UNIT
from alfasim_score.units import THERMAL_EXPANSION_UNIT
from alfasim_score.units import TIME_UNIT_SCORE
from alfasim_score.units import VOLUME_UNIT
from alfasim_score.units import YOUNG_MODULUS_UNIT


def encode_formation_name(name: str) -> str:
    return FORMATION_PREFIX + name


def encode_cement_name(name: str) -> str:
    return CEMENT_PREFIX + name


class ScoreInputReader:
    def __init__(self, score_filepath: Path):
        self.score_filepath = score_filepath
        with open(score_filepath) as f:
            self.input_content = json.load(f)

    def read_general_data(self) -> Dict[str, Any]:
        """Read the general data from SCORE input file."""
        return {
            "case_name": self.input_content["name"],
            "final_md": Scalar(self.input_content["final_md"], LENGTH_UNIT),
            "water_depth": Scalar(self.input_content["water_depth"], LENGTH_UNIT),
            "air_gap": Scalar(self.input_content["air_gap"], LENGTH_UNIT),
        }

    def read_well_trajectory(self) -> Dict[str, Array]:
        """Read the arrays with the x and y positions."""
        x = [entry["displacement"] for entry in self.input_content["trajectory"]["data"]]
        y = [-entry["vertical_depth"] for entry in self.input_content["trajectory"]["data"]]
        md = [entry["depth"] for entry in self.input_content["trajectory"]["data"]]
        return {
            "x": Array(x, LENGTH_UNIT),
            "y": Array(y, LENGTH_UNIT),
            "md": Array(md, LENGTH_UNIT),
        }

    def read_tubing_materials(self) -> List[Dict[str, Union[Scalar, str]]]:
        """Read the data for the tubings from SCORE input file."""
        tubing_data = []
        for section in self.input_content["operation"]["tubing_string"]["string_sections"]:
            thermal_property = section["pipe"]["grade"]["thermomechanical_properties"]
            tubing_data.append(
                {
                    "name": section["pipe"]["grade"]["name"],
                    "type": "solid",
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

    def read_casing_materials(self) -> List[Dict[str, Union[Scalar, str]]]:
        """Read geometric data for the casing and annulus data associated to the casing from SCORE input file."""
        casing_data = []
        for item in self.input_content["well_strings"]:
            for section in item["string_sections"]:
                properties = section["pipe"]["grade"]["thermomechanical_properties"]
                casing_data.append(
                    {
                        "name": section["pipe"]["grade"]["name"],
                        "type": "solid",
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
                )
        return casing_data

    def read_cement_material(self) -> List[Dict[str, Union[Scalar, str]]]:
        """
        Read the data for the cement from SCORE input file.
        This method assumes all configured cement properties are the same and that
        the first_slurry and second_slurry have the same properties.
        """
        well_strings = self.input_content["well_strings"]
        properties = well_strings[0]["cementing"]["first_slurry"]["thermomechanical_properties"]
        return [
            {
                "name": encode_cement_name(CEMENT_NAME),
                "type": "solid",
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
            properties = lithology["thermomechanical_properties"]
            lithology_data.append(
                {
                    "name": encode_formation_name(lithology["display_name"]),
                    "type": "solid",
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

    def read_casings(self) -> List[Dict[str, Any]]:
        """Read the data for the casing from SCORE input file."""
        casing_data = []
        for item in self.input_content["well_strings"]:
            if item["interval"] != WellItemFunction.OPEN.value:
                casing_data.append(
                    {
                        "type": WellItemType(item["type"]) if "type" in item else WellItemType.NONE,
                        "function": WellItemFunction(item["interval"]),
                        "hanger_md": Scalar(item["hanger_md"], LENGTH_UNIT, "length"),
                        "shoe_md": Scalar(item["shoe_md"], LENGTH_UNIT, "length"),
                        "final_md": Scalar(item["final_md"], LENGTH_UNIT, "length"),
                        "top_of_cement": Scalar(item["toc_md"], LENGTH_UNIT, "length"),
                        "hole_diameter": Scalar(item["hole_size"], DIAMETER_UNIT, "diameter"),
                        "annular_fluids": [
                            {
                                "name": fluid_data["fluid"],
                                "top_md": Scalar(fluid_data["top"], LENGTH_UNIT, "length"),
                                "base_md": Scalar(fluid_data["base"], LENGTH_UNIT, "length"),
                                "extension": Scalar(fluid_data["extension"], LENGTH_UNIT, "length"),
                            }
                            for fluid_data in item["annular_fluids"]
                        ],
                        "pressure_relief": {
                            "is_active": item["pressure_relief"].get("active", False),
                            "pressure": Scalar(
                                item["pressure_relief"].get("considered_pressure", 0.0),
                                PRESSURE_UNIT,
                            ),
                            "position": Scalar(
                                item["pressure_relief"].get("depth", 0.0),
                                LENGTH_UNIT,
                            ),
                        },
                        "sections": [
                            {
                                "material": section["pipe"]["grade"]["name"],
                                "top_md": Scalar(section["top_md"], LENGTH_UNIT, "length"),
                                "base_md": Scalar(section["base_md"], LENGTH_UNIT, "length"),
                                "inner_diameter": Scalar(
                                    section["pipe"]["od"] - 2.0 * section["pipe"]["wt"],
                                    DIAMETER_UNIT,
                                    "diameter",
                                ),
                                "outer_diameter": Scalar(
                                    section["pipe"]["od"], DIAMETER_UNIT, "diameter"
                                ),
                            }
                            for section in item["string_sections"]
                        ],
                    }
                )
        return casing_data

    def read_tubing(self) -> List[Dict[str, Any]]:
        """Read the data for the tubing from SCORE input file."""
        tubing_data = []
        for section in self.input_content["operation"]["tubing_string"]["string_sections"]:
            outer_radius = section["pipe"]["od"] / 2.0
            thickness = section["pipe"]["wt"]
            inner_diameter = 2.0 * (outer_radius - thickness)
            tubing_data.append(
                {
                    "top_md": Scalar(section["top_md"], LENGTH_UNIT, "length"),
                    "base_md": Scalar(section["base_md"], LENGTH_UNIT, "length"),
                    "inner_diameter": Scalar(inner_diameter, DIAMETER_UNIT, "diameter"),
                    "outer_diameter": Scalar(section["pipe"]["od"], DIAMETER_UNIT, "diameter"),
                    "material": section["pipe"]["grade"]["name"],
                }
            )
        return tubing_data

    def read_packers(self) -> List[Dict[str, Union[Scalar, str]]]:
        """Read the data for the packers from SCORE input file."""
        packer_data = []
        for component in self.input_content["operation"]["tubing_string"]["components"]:
            if component["component"]["type"] == "PACKER":
                packer_data.append(
                    {
                        "name": component["name"],
                        "position": Scalar(component["depth"], LENGTH_UNIT, "length"),
                    }
                )
        return packer_data

    def read_open_hole(self) -> List[Dict[str, Scalar]]:
        """Read the data for the open hole from SCORE input file."""
        open_hole_data = []
        for section in self.input_content["well_strings"]:
            if section["interval"] == WellItemFunction.OPEN.value:
                open_hole_data.append(
                    {
                        "final_md": Scalar(section["final_md"], LENGTH_UNIT, "length"),
                        "hole_diameter": Scalar(section["hole_size"], DIAMETER_UNIT, "diameter"),
                    }
                )
        return open_hole_data

    def read_formations(self) -> List[Dict[str, Scalar]]:
        """Read data for formations from SCORE input file."""
        return [
            {
                "material": encode_formation_name(lithology["display_name"]),
                # elevations are given in quota
                "top_elevation": Scalar(lithology["top_elevation"], LENGTH_UNIT, "length"),
                "base_elevation": Scalar(lithology["base_elevation"], LENGTH_UNIT, "length"),
            }
            for lithology in self.input_content["lithologies"]
        ]

    def read_formation_temperatures(self) -> Dict[str, Array]:
        """Read data for formations temperatures from SCORE input file."""
        label = "Geotérmico (default)"
        temperature_profile = list(
            filter(
                lambda item: item["name"] == label or item["is_default"],
                self.input_content["temperature"]["ground_thermal_profiles"],
            )
        )[0]
        return {
            "temperatures": Array(
                [data["temperature"] for data in temperature_profile["data"]], TEMPERATURE_UNIT
            ),
            # elevations are given in quota
            "elevations": Array(
                [data["elevation"] for data in temperature_profile["data"]], LENGTH_UNIT
            ),
        }

    def read_operation_type(self) -> OperationType:
        """Read data for the operation type configured in SCORE input file."""
        return OperationType(self.input_content["operation"]["type"])

    def read_operation_data(self) -> Dict[str, Any]:
        """Read data for production operation registered in SCORE input file."""
        operation = self.input_content["operation"]["data"]
        operation_type = self.read_operation_type()
        duration_unit = operation.get("duration_unit", TIME_UNIT_SCORE)
        operation_data = {
            "name": self.input_content["operation"]["name"],
            "type": operation_type,
            "fluid_type": FluidType(operation["fluid"]),
            "fluid": operation["fluid_type"],
            "duration": Scalar(
                operation["duration"] * 30 if duration_unit == "month" else operation["duration"],
                "d" if duration_unit == "month" else duration_unit,
            ),
            "flow_initial_temperature": Scalar(
                operation["flow_initial_temperature"], TEMPERATURE_UNIT
            ),
            "flow_initial_pressure": Scalar(operation["flow_initial_pressure"], PRESSURE_UNIT),
            "perforation_base_depth": Scalar(operation["perforation_base_depth"], LENGTH_UNIT),
            "flow_rate": Scalar(operation["flow_rate"], STD_VOLUMETRIC_FLOW_RATE_UNIT),
        }
        if operation_type == OperationType.PRODUCTION:
            operation_data.update(
                {
                    "lift_method": LiftMethod(operation["method"]),
                    "oil_flow_rate": Scalar(
                        operation["oil_flow_rate"], STD_VOLUMETRIC_FLOW_RATE_UNIT
                    ),
                    "gas_oil_ratio": Scalar(operation["gor"], GAS_OIL_RATIO_UNIT),
                    "water_flow_rate": Scalar(
                        operation["water_flow_rate"], STD_VOLUMETRIC_FLOW_RATE_UNIT
                    ),
                }
            )
        return operation_data

    def read_operation_method_data(self) -> Dict[str, Any]:
        """Read data from the gas lift method."""
        method_data = self.input_content["operation"]["data"]["method_data"]
        lift_method = LiftMethod(self.input_content["operation"]["data"]["method"])
        data: Dict[str, Any] = {}
        if lift_method == LiftMethod.GAS_LIFT:
            data = {
                "well_head_pressure": Scalar(method_data["well_head_pressure"], PRESSURE_UNIT),
                "well_head_temperature": Scalar(
                    method_data["well_head_temperature"], TEMPERATURE_UNIT
                ),
                "fluid": method_data["fluid_type"],
                "valve_depth": Scalar(method_data["valve_depth"], LENGTH_UNIT),
                "well_head_flow": Scalar(
                    method_data["well_head_flow"], STD_VOLUMETRIC_FLOW_RATE_UNIT
                ),
            }
        return data

    def read_operation_fluid_data(self) -> Dict[str, Any]:
        """Read data for the fluid for the operation registered in SCORE input file."""
        fluid_data = self.input_content["operation"]["thermal_data"]
        return {
            "name": fluid_data["fluid"],
            "fluid_model_type": ModelFluidType(fluid_data["fluid_type"]),
            "gas_oil_ratio": Scalar(fluid_data["gas_oil_ratio"], GAS_OIL_RATIO_UNIT),
            "api_gravity": Scalar(fluid_data["api_gravity"], FRACTION_UNIT),
            "gas_gravity": Scalar(fluid_data["gas_gravity"], FRACTION_UNIT),
        }

    def read_operation_annuli_data(self) -> List[Dict[str, Any]]:
        """Read annuli data defined in operation in SCORE input file."""
        annuli_data = []
        for annulus in self.input_content["operation"]["thermal_data"]["annuli_data"]:
            leakoff_volume = annulus["apb_bled_volume"] if annulus["apb_bled_volume"] else 0.0
            annuli_data.append(
                {
                    "string_name": annulus["string_name"],
                    "leakoff_volume": Scalar(leakoff_volume, VOLUME_UNIT),
                    "initial_top_pressure": Scalar(annulus["initial_top_pressure"], PRESSURE_UNIT),
                }
            )
        return annuli_data

    def read_tubing_fluid_data(self) -> List[Dict[str, Any]]:
        """Read data for the annulus fluid associated to tubing in SCORE input file."""
        tubing_string_data = self.input_content["operation"]["tubing_string"]
        return [
            {
                "name": fluid_data["fluid"],
                "top_md": Scalar(fluid_data["top"], LENGTH_UNIT, "length"),
                "base_md": Scalar(fluid_data["base"], LENGTH_UNIT, "length"),
                "extension": Scalar(fluid_data["extension"], LENGTH_UNIT, "length"),
            }
            for fluid_data in tubing_string_data["annular_fluids"]
        ]

    def read_initial_condition(self) -> Dict[str, AnnulusModeType]:
        """
        Get the initial condition data from the input file.
        """
        initial_conditions_data = self.input_content["initial_conditions"][0]
        return {"mode": AnnulusModeType(initial_conditions_data["reference"])}

    def read_output_curves(self) -> Dict[str, Array]:
        """
        Get the results from the input file.
        This parsed output curves are used to check cases results.
        """
        if "result" in self.input_content["operation"]["thermal_simulation"]:
            result = self.input_content["operation"]["thermal_simulation"]["result"]["0"]
            # this list is not complete, there are other results recorded in the input file.
            return {
                "measured_depth": Array(result["md"], LENGTH_UNIT),
                "temperature": Array(
                    result["production_tubing"]["temperature"]["final"], TEMPERATURE_UNIT
                ),
                "pressure": Array(result["production_tubing"]["pressure"]["final"], PRESSURE_UNIT),
                "density": Array(result["production_tubing"]["density"]["final"], DENSITY_UNIT),
                "gas_mass_fraction": Array(
                    result["production_tubing"]["mass_fraction"]["gas"], FRACTION_UNIT
                ),
            }
        return {}
