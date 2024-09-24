from typing import Any
from typing import Dict
from typing import List
from typing import Union

from alfasim_sdk import PluginDescription
from barril.units import Array
from barril.units import Scalar
from dataclasses import asdict
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from alfasim_score.common import Annuli
from alfasim_score.common import Annulus
from alfasim_score.common import AnnulusModeType
from alfasim_score.common import AnnulusTable
from alfasim_score.common import FluidModelPvt
from alfasim_score.common import FluidModelZamora
from alfasim_score.common import SolidMechanicalProperties
from alfasim_score.common import WellItemFunction
from alfasim_score.common import filter_duplicated_materials_by_name
from alfasim_score.constants import ANNULUS_DEPTH_TOLERANCE
from alfasim_score.constants import HAS_FLUID_RETURN
from alfasim_score.converter.alfacase.score_input_reader import ScoreInputReader
from alfasim_score.units import LENGTH_UNIT


class ScoreAPBPluginConverter:
    def __init__(self, score_reader: ScoreInputReader):
        self.score_input = score_reader
        self.general_data = score_reader.read_general_data()
        self.well_start_position = self.general_data["water_depth"] + self.general_data["air_gap"]

    def get_position_in_well(self, position: Scalar) -> Scalar:
        """
        Get the position relative to the well start position.
        This method is a helper function to convert SCORE measured positions to the reference in well head
        because this is the reference ALFAsim uses for well.
        """
        return position - self.well_start_position

    def get_all_annular_fluid_names(self) -> List[str]:
        """Get the list of fluid names registered as annulus fluids in tubing and casing of SCORE data."""
        all_fluids = set([fluid["name"] for fluid in self.score_input.read_tubing_fluid_data()])
        for casings in self.score_input.read_casings():
            for fluid in casings["annular_fluids"]:
                all_fluids.add(fluid["name"])
        return sorted(all_fluids)

    def get_fluid_id(self, fluid_name: str) -> int:
        """
        Get the fluid id.
        This method is used because the fluids need to have an id number because the fluid in the
        plugin is identified by this number instead of its name.
        """
        return self.get_all_annular_fluid_names().index(fluid_name)

    def _build_annular_fluid_table(self, fluids_data: List[Dict[str, Any]]) -> AnnulusTable:
        """Build the table with fluids in the annular."""
        fluid_names = []
        fluid_ids = []
        initial_depths = []
        final_depths = []
        for fluid in fluids_data:
            # in the SCORE input file when top and base measured distance are equal means that there is no fluid there
            if fluid["top_md"] < fluid["base_md"]:
                fluid_names.append(fluid["name"])
                fluid_ids.append(float(self.get_fluid_id(fluid["name"])))
                initial_depths.append(self.get_position_in_well(fluid["top_md"]).GetValue())
                final_depths.append(self.get_position_in_well(fluid["base_md"]).GetValue())
        return AnnulusTable(
            fluid_names,
            fluid_ids,
            Array(initial_depths, LENGTH_UNIT),
            Array(final_depths, LENGTH_UNIT),
        )

    def _has_annular_fluid(self, fluids_data: List[Dict[str, Any]]) -> bool:
        """
        Check if there is fluid in the annular.
        The current criterea is to use a threshold value of ANNULUS_DEPTH_TOLERANCE to define
        if the annulus should be considered active.
        """
        return any([fluid["extension"] > ANNULUS_DEPTH_TOLERANCE for fluid in fluids_data])

    def _convert_annuli(self) -> Annuli:
        """
        Covert the annuli with data from SCORE file.
        """
        # It uses the data in list in the operation/thermal_data/annuli_data to define the A, B, C, D, E annulus
        # therefore it's considered here that they sorted in the input SCORE file.
        annuli_data = self.score_input.read_operation_annuli_data().copy()
        initial_conditions_data = self.score_input.read_initial_condition()
        annuli = Annuli()
        if annuli_data:
            # the annulus A uses data from tubing_strings section of SCORE file
            tubing_fluids = self.score_input.read_tubing_fluid_data()
            annulus_data = annuli_data.pop(0)
            annuli.annulus_A = Annulus(
                is_active=True,
                mode_type=initial_conditions_data["mode"],
                initial_top_pressure=annulus_data["initial_top_pressure"],
                is_open_seabed=False,
                annulus_table=self._build_annular_fluid_table(tubing_fluids),
                has_fluid_return=HAS_FLUID_RETURN,
                initial_leakoff=annulus_data["leakoff_volume"],
            )

        # create a list with the casings that are in the SCORE file
        casings_data = {casing["function"]: casing for casing in self.score_input.read_casings()}
        all_casing_types = [
            WellItemFunction.CONDUCTOR,
            WellItemFunction.SURFACE,
            WellItemFunction.INTERMEDIATE,
            WellItemFunction.PRODUCTION,
        ]
        casings = [
            casings_data[casing_type]
            for casing_type in all_casing_types
            if casing_type in casings_data
        ]
        # It iterates the data in the section operation/thermal_data/annuli_data and use it to check
        # correspondent annulus iterating over the casings in order to check which of them are active by checking there is annular fluid.
        for annulus_label, annulus_data in zip(["B", "C", "D", "E"], annuli_data):
            while casings:
                casing = casings.pop()
                if self._has_annular_fluid(casing["annular_fluids"]):
                    is_open_seabed = casing["function"] == WellItemFunction.SURFACE
                    setattr(
                        annuli,
                        f"annulus_{annulus_label}",
                        Annulus(
                            is_active=True,
                            mode_type=initial_conditions_data["mode"],
                            initial_top_pressure=annulus_data["initial_top_pressure"],
                            is_open_seabed=is_open_seabed,
                            annulus_table=self._build_annular_fluid_table(casing["annular_fluids"]),
                            has_fluid_return=HAS_FLUID_RETURN,
                            initial_leakoff=annulus_data["leakoff_volume"],
                            has_relief_pressure=casing["pressure_relief"]["is_active"],
                            relief_pressure=casing["pressure_relief"]["pressure"],
                            relief_position=self.get_position_in_well(
                                casing["pressure_relief"]["position"]
                            ),
                        ),
                    )
        return annuli

    def _convert_solid_mechanical_properties(self) -> List[SolidMechanicalProperties]:
        """Convert list of mechanical properties of solid materials from SCORE file."""
        solid_materials = []
        material_list = (
            self.score_input.read_cement_material()
            + self.score_input.read_casing_materials()
            + self.score_input.read_tubing_materials()
            + self.score_input.read_lithology_materials()
        )
        for material in filter_duplicated_materials_by_name(material_list):
            solid_materials.append(
                SolidMechanicalProperties(
                    name=material["name"],
                    young_modulus=material["young_modulus"],
                    poisson_ratio=material["poisson_ratio"],
                    thermal_expansion_coefficient=material["thermal_expansion"],
                )
            )
        return solid_materials

    def _convert_fluids(self) -> List[Union[FluidModelPvt, FluidModelZamora]]:
        """Convert the fluids used in the annuli."""
        # NOTE: for now the converter only uses PVT table model
        return [FluidModelPvt(name) for name in self.get_all_annular_fluid_names()]

    def build_plugin_description(self) -> PluginDescription:
        """Generate the configured node with data of the current operation."""
        annuli = self._convert_annuli()
        fluids = self._convert_fluids()
        materials = self._convert_solid_mechanical_properties()
        gui_models = {
            "AnnulusDataModel": {
                "name": "Annulus Data Model",
                **annuli.to_dict(),
            },
            "FluidContainer": {
                "name": "Annulus Fluids Container",
                "_children_list": [fluid.to_dict() for fluid in fluids],
            },
            "MechanicalContainer": {
                "name": "Mechanical Properties",
                "_children_list": [material.to_dict() for material in materials],
            },
        }
        return PluginDescription(
            name="apb",
            gui_models=gui_models,
            is_enabled=True,
        )
