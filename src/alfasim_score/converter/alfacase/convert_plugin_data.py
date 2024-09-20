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
from alfasim_score.common import FluidModelPvt
from alfasim_score.common import FluidModelZamora
from alfasim_score.common import SolidMechanicalProperties
from alfasim_score.common import filter_duplicated_materials_by_name
from alfasim_score.converter.alfacase.score_input_reader import ScoreInputReader


class ScoreAPBPluginConverter:
    def __init__(self, score_reader: ScoreInputReader):
        self.score_input = score_reader
        # self.general_data = score_reader.read_general_data()
        # self.well_start_position = self.general_data["water_depth"] + self.general_data["air_gap"]

    def _convert_annuli(self) -> Annuli:
        return Annuli(Annulus())

    def _convert_fluids_pvt_data(self) -> List[Union[FluidModelZamora, FluidModelPvt]]:
        """Convert list of mechanical properties of solid materials from SCORE file."""
        fluid_materials: List[Union[FluidModelZamora, FluidModelPvt]] = []
        # TODO: get the fluids and pvt data tabel for each fluid
        return fluid_materials

    def _convert_solid_mechanical_properties(self) -> List[SolidMechanicalProperties]:
        """Convert list of mechanical properties of solid materials from SCORE file."""
        solid_materials = []
        material_list = (
            self.score_input.read_cement_material()
            + self.score_input.read_casing_materials()
            + self.score_input.read_tubing_materials()
            + self.score_input.read_lithology_materials()
        )
        for material in material_list:
            solid_materials.append(
                SolidMechanicalProperties(
                    name=material["name"],
                    young_modulus=material["young_modulus"],
                    poisson_ratio=material["poisson_ratio"],
                    thermal_expansion_coefficient=material["thermal_expansion"],
                )
            )
        return solid_materials

    def build_plugin_description(self) -> PluginDescription:
        """Generate the configured node with data of the current operation."""
        annuli = self._convert_annuli()
        fluids = self._convert_fluids_pvt_data()
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
