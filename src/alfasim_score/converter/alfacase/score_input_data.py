from typing import Any
from typing import Dict
from typing import List
from typing import Union

import csv
import numpy as np
from barril.units import Array
from barril.units import Scalar
from pathlib import Path

from alfasim_score.common import AnnulusLabel
from alfasim_score.common import LiftMethod
from alfasim_score.constants import ANNULUS_DEPTH_TOLERANCE
from alfasim_score.constants import FLUID_DEFAULT_NAME
from alfasim_score.constants import MAXIMUM_DISTANCE_BETWEEN_TRAJECTORY_POINTS
from alfasim_score.constants import MINIMUM_DISTANCE_BETWEEN_TRAJECTORY_POINTS
from alfasim_score.converter.alfacase.score_input_reader import ScoreInputReader
from alfasim_score.units import LENGTH_UNIT
from alfasim_score.units import SPECIFIC_HEAT_UNIT
from alfasim_score.units import THERMAL_CONDUCTIVITY_UNIT
from alfasim_score.units import THERMAL_EXPANSION_UNIT


class ScoreInputData:
    def __init__(self, score_input_reader: ScoreInputReader):
        self.reader = score_input_reader
        self.general_data = self.reader.read_general_data()
        self.operation_data = self.reader.read_operation_data()

    def has_gas_lift(self) -> bool:
        """Check if the operation has gas lift."""
        return self.operation_data.get("lift_method", "") == LiftMethod.GAS_LIFT

    def has_annular_fluid(self, fluids_data: List[Dict[str, Any]]) -> bool:
        """
        Check if there is fluid in the annular.
        The current criterea is to use a threshold value of ANNULUS_DEPTH_TOLERANCE to define
        if the annulus should be considered active.
        """
        return any([fluid["extension"] > ANNULUS_DEPTH_TOLERANCE for fluid in fluids_data])

    def get_well_start_position(self) -> Scalar:
        return self.general_data["water_depth"] + self.general_data["air_gap"]

    def get_position_in_well(self, position: Scalar) -> Scalar:
        """
        Get the position relative to the well start position.
        This method is a helper function to convert SCORE measured positions to the reference in well head
        because this is the reference ALFAsim uses for well.
        """
        return position - self.get_well_start_position()

    def get_all_annular_fluid_names(self) -> List[str]:
        """Get the list of fluid names registered as annulus fluids in tubing and casing of SCORE data."""
        all_fluids = set([fluid["name"] for fluid in self.reader.read_tubing_fluid_data()])
        for casings in self.reader.read_casings():
            for fluid in casings["annular_fluids"]:
                if fluid["extension"].value > 0:
                    all_fluids.add(fluid["name"])
        return sorted(all_fluids)

    def get_fluid_id(self, fluid_name: str) -> int:
        """
        Get the fluid id.
        This method is used because the fluids need to have an id number because the fluid in the
        plugin is identified by this number instead of its name.
        """
        return self.get_all_annular_fluid_names().index(fluid_name)

    def get_well_length(self) -> Scalar:
        """Calculate the well length configured in SCORE file."""
        return self.get_position_in_well(self.reader.read_general_data()["final_md"])

    def get_annuli_list(self) -> List[AnnulusLabel]:
        """Get the list of active annuli configured in the input file"""
        annuli_data = self.reader.read_operation_annuli_data()
        total_annuli = len(annuli_data)
        return list(AnnulusLabel)[:total_annuli]

    def _get_default_fluid(self, fluid_name: str) -> Dict[str, Union[Scalar, str]]:
        return {
            "name": fluid_name,
            "type": "fluid",
            "density": Scalar(1000.0, "kg/m3", "density"),
            "thermal_conductivity": Scalar(0.6, THERMAL_CONDUCTIVITY_UNIT),
            "specific_heat": Scalar(4181.0, SPECIFIC_HEAT_UNIT),
            "thermal_expansion": Scalar(0.0004, THERMAL_EXPANSION_UNIT),
        }

    def get_default_fluid_properties(self) -> List[Dict[str, Union[Scalar, str]]]:
        """
        Get default properties for the materials that must be filled for material list
        of alfacase regardless their properties are being calculated from pvt table in the plugin.
        The properties here are for now the same of default packer fluid
        """
        return [
            self._get_default_fluid(fluid_name) for fluid_name in self.get_all_annular_fluid_names()
        ]

    def get_default_packer_fluid(self) -> List[Dict[str, Union[Scalar, str]]]:
        """Get the properties of default fluid above packer."""
        return [self._get_default_fluid(FLUID_DEFAULT_NAME)]

    def export_profile_curve(self, filepath: Path, curve_name: str) -> None:
        """
        Export the result of a curve to a file.
        This function export the measured depth related to the well start positions.
        The exported output file is used to check cases results.
        """
        curves = self.reader.read_output_curves()
        if len(curves):
            general_data = self.reader.read_general_data()
            start_position = general_data["water_depth"] + general_data["air_gap"]
            with open(filepath, "w", encoding="utf-8") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=["measured_depth", curve_name])
                writer.writeheader()
                for md, value in zip(curves["measured_depth"], curves[curve_name]):
                    writer.writerow(
                        {
                            "measured_depth": md - start_position.GetValue(LENGTH_UNIT),
                            curve_name: value,
                        }
                    )

    def get_seabed_hydrostatic_pressure(self) -> Scalar:
        """Calculate the value of hydrostatic pressure at seabed position."""
        rho = 1025  # kg/m3
        g = 9.8  # m/s²
        h = self.general_data["water_depth"].GetValue(LENGTH_UNIT)
        return Scalar(rho * g * h, "Pa")

    def get_refined_trajectory(self) -> Dict[str, Array]:
        """
        Transform the original SCORE trajectory into a refined trajectory
        with sections equal or less then some maximum length.
        """
        trajectory = self.reader.read_well_trajectory()
        max_distance = MAXIMUM_DISTANCE_BETWEEN_TRAJECTORY_POINTS.GetValue(LENGTH_UNIT)
        x_array = np.array(trajectory["x"].GetValues(LENGTH_UNIT), dtype=float)
        y_array = np.array(trajectory["y"].GetValues(LENGTH_UNIT), dtype=float)
        md_array = np.array(
            np.insert(
                np.cumsum(np.hypot(np.diff(x_array), np.diff(y_array))) - y_array[0], 0, -y_array[0]
            ),
            dtype=float,
        )
        points = np.stack((x_array, y_array), axis=1)

        # Add important points to trajectory
        important_mds = np.array(self.reader.read_important_mds())
        important_x = np.interp(important_mds, md_array, x_array)
        important_y = np.interp(important_mds, md_array, y_array)
        important_points = np.stack((important_x, important_y), axis=1)

        points = np.concatenate((points, important_points), axis=0)

        # remove duplicates
        _, unique_indices = np.unique(points[:, 1], return_index=True)
        points = points[unique_indices[np.argsort(points[unique_indices, 1])[::-1]]]

        # remove points above the seabed
        start_position = self.get_well_start_position()
        points = points[np.abs(points[:, 1]) >= start_position.GetValue(LENGTH_UNIT)]

        # remove points too close to each other, keeping the first and last points
        filtered_points = [points[0]]
        min_distance = MINIMUM_DISTANCE_BETWEEN_TRAJECTORY_POINTS.GetValue(LENGTH_UNIT)
        for point in points[1:-1]:
            if np.abs(point[1] - filtered_points[-1][1]) >= min_distance:
                filtered_points.append(point)
        filtered_points.append(points[-1])
        points = np.array(filtered_points)

        interpolated_points = [points[0]]
        for i in range(1, len(points)):
            previous_point = interpolated_points[-1]
            current_point = points[i]
            distance = np.linalg.norm(current_point - previous_point)
            if distance > max_distance:
                num_segments = int(np.ceil(distance / max_distance))
                new_points = np.linspace(previous_point, current_point, num_segments + 1)[1:]
                interpolated_points.extend(new_points)
            else:
                interpolated_points.append(current_point)
        x_new = [point[0] for point in interpolated_points]
        y_new = [point[1] for point in interpolated_points]
        return {"x": Array(x_new, LENGTH_UNIT), "y": Array(y_new, LENGTH_UNIT)}
