from typing import Any
from typing import Dict
from typing import List

import numpy as np
from alfasim_sdk import PluginDescription
from barril.units import Array
from barril.units import Scalar

from alfasim_score.common import WellItemFunction
from alfasim_score.common import filter_duplicated_materials_by_name
from alfasim_score.constants import HAS_FLUID_RETURN
from alfasim_score.converter.alfacase.apb_plugin_data import Annuli
from alfasim_score.converter.alfacase.apb_plugin_data import Annulus
from alfasim_score.converter.alfacase.apb_plugin_data import AnnulusDepthTable
from alfasim_score.converter.alfacase.apb_plugin_data import AnnulusTemperatureTable
from alfasim_score.converter.alfacase.apb_plugin_data import FluidModelPvt
from alfasim_score.converter.alfacase.apb_plugin_data import Options
from alfasim_score.converter.alfacase.apb_plugin_data import PluginReferences
from alfasim_score.converter.alfacase.apb_plugin_data import SolidMechanicalProperties
from alfasim_score.converter.alfacase.apb_plugin_data import ThermalPropertyUpdateMode
from alfasim_score.converter.alfacase.score_input_data import ScoreInputData
from alfasim_score.converter.alfacase.score_input_reader import ScoreInputReader
from alfasim_score.units import LENGTH_UNIT
from alfasim_score.units import PRESSURE_UNIT
from alfasim_score.units import TEMPERATURE_UNIT


class ScoreAPBPluginConverter:
    def __init__(self, score_input_data: ScoreInputData):
        self.score_data = score_input_data

    def _build_annular_temperature_table(
        self, final_temperature_depth: Scalar
    ) -> AnnulusTemperatureTable:
        """
        Calculate the temperature of fluids based on temperature of formation coming from SCORE input file.
        It uses the well vertical positions in order to interpolates the temperatures of formation and it maps
        each measured depth to the temperature of formation in that position.
        """
        formation_temperature_data = self.score_data.reader.read_formation_temperatures()
        formation_depths = (
            np.abs(formation_temperature_data["elevations"].GetValues())
            + self.score_data.general_data["air_gap"].GetValue()
        )
        formation_temperatures = formation_temperature_data["temperatures"].GetValues()
        trajectory = self.score_data.reader.read_well_trajectory()
        x = np.abs(trajectory["x"])
        y = np.abs(trajectory["y"])

        md = [y[0]]
        for i in range(1, len(x)):
            dx = x[i] - x[i - 1]
            dy = y[i] - y[i - 1]
            md.append(md[-1] + np.sqrt(dx**2 + dy**2))
        md = np.array(md)

        formation_md_score_reference = Array(
            np.interp(formation_depths, y, md),
            LENGTH_UNIT,
        )

        formation_md_alfasim_reference = Array(
            [
                self.score_data.get_position_in_well(Scalar(depth, LENGTH_UNIT)).GetValue()
                for depth in formation_md_score_reference.GetValues(LENGTH_UNIT)
            ],
            LENGTH_UNIT,
        )

        annulus_depth_md_alfasim_reference = [
            self.score_data.get_position_in_well(Scalar(depth, LENGTH_UNIT)).GetValue()
            for depth in formation_md_score_reference.GetValues(LENGTH_UNIT)
            if self.score_data.get_position_in_well(Scalar(depth, LENGTH_UNIT)).GetValue()
            < final_temperature_depth.GetValue()
        ]

        if final_temperature_depth.GetValue() not in annulus_depth_md_alfasim_reference:
            annulus_depth_md_alfasim_reference.append(final_temperature_depth.GetValue())
        annulus_depth_md_alfasim_reference = Array(annulus_depth_md_alfasim_reference, LENGTH_UNIT)

        annulus_temperature = Array(
            np.interp(
                annulus_depth_md_alfasim_reference,
                formation_md_alfasim_reference,
                formation_temperatures,
            ),
            TEMPERATURE_UNIT,
        )

        return AnnulusTemperatureTable(
            depths=annulus_depth_md_alfasim_reference, temperatures=annulus_temperature
        )

    def _build_annular_fluid_depth_table(
        self, fluids_data: List[Dict[str, Any]]
    ) -> AnnulusDepthTable:
        """Build the table with fluids in the annular."""
        initial_depths = []
        final_depths = []
        fluid_ids = []
        for fluid in fluids_data:
            # in the SCORE input file when top and base measured distance are equal means that there is no fluid there
            if fluid["top_md"] < fluid["base_md"]:
                initial_depths.append(
                    self.score_data.get_position_in_well(fluid["top_md"]).GetValue()
                )
                final_depths.append(
                    self.score_data.get_position_in_well(fluid["base_md"]).GetValue()
                )
                fluid_ids.append(int(self.score_data.get_fluid_id(fluid["name"])))
        return AnnulusDepthTable(
            Array(initial_depths, LENGTH_UNIT),
            Array(final_depths, LENGTH_UNIT),
            PluginReferences(fluid_ids),
        )

    def _convert_annuli(self) -> Annuli:
        """
        Covert the annuli with data from SCORE file.
        """
        # It uses the data in list in the operation/thermal_data/annuli_data to define the A, B, C, D, E annulus
        # therefore it's considered here that they sorted in the input SCORE file.
        annuli_data = self.score_data.reader.read_operation_annuli_data().copy()
        initial_conditions_data = self.score_data.reader.read_initial_condition()
        annuli = Annuli()
        if annuli_data:
            # the annulus A uses data from tubing_strings section of SCORE file
            tubing_fluids_data = self.score_data.reader.read_tubing_fluid_data()
            annulus_data = annuli_data.pop(0)
            final_temperature_depth = Scalar(
                self._build_annular_fluid_depth_table(tubing_fluids_data).final_depths.GetValues()[
                    0
                ],
                LENGTH_UNIT,
            )
            annuli.annulus_a = Annulus(
                is_active=True,
                mode_type=initial_conditions_data["mode"],
                initial_top_pressure=annulus_data["initial_top_pressure"],
                is_open_seabed=False,
                annulus_depth_table=self._build_annular_fluid_depth_table(tubing_fluids_data),
                annulus_temperature_table=self._build_annular_temperature_table(
                    final_temperature_depth
                ),
                has_fluid_return=HAS_FLUID_RETURN,
                initial_leakoff=annulus_data["leakoff_volume"],
            )

        # create a list with the casings that are in the SCORE file
        casings_data = {
            casing["function"]: casing for casing in self.score_data.reader.read_casings()
        }
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
        for annulus_label, annulus_data in zip(["b", "c", "d", "e"], annuli_data):
            while casings:
                casing = casings.pop()
                if self.score_data.has_annular_fluid(casing["annular_fluids"]):
                    is_open_seabed = casing["function"] == WellItemFunction.SURFACE
                    final_temperature_depth = Scalar(
                        self._build_annular_fluid_depth_table(
                            casing["annular_fluids"]
                        ).final_depths.GetValues()[0],
                        LENGTH_UNIT,
                    )
                    water_depth_pressure = (
                        self.score_data.get_seabed_hydrostatic_pressure()
                        if is_open_seabed
                        else Scalar(0.0, PRESSURE_UNIT)
                    )
                    setattr(
                        annuli,
                        f"annulus_{annulus_label}",
                        Annulus(
                            is_active=True,
                            mode_type=initial_conditions_data["mode"],
                            initial_top_pressure=annulus_data["initial_top_pressure"],
                            is_open_seabed=is_open_seabed,
                            annulus_depth_table=self._build_annular_fluid_depth_table(
                                casing["annular_fluids"]
                            ),
                            annulus_temperature_table=self._build_annular_temperature_table(
                                final_temperature_depth
                            ),
                            has_fluid_return=HAS_FLUID_RETURN,
                            initial_leakoff=annulus_data["leakoff_volume"],
                            has_pressure_relief=casing["pressure_relief"]["is_active"],
                            pressure_relief=casing["pressure_relief"]["pressure"],
                            relief_position=self.score_data.get_position_in_well(
                                casing["pressure_relief"]["position"]
                            ),
                            water_depth_pressure=water_depth_pressure,
                        ),
                    )
        return annuli

    def _convert_solid_mechanical_properties(self) -> List[SolidMechanicalProperties]:
        """Convert list of mechanical properties of solid materials from SCORE file."""
        solid_materials = []
        material_list = (
            self.score_data.reader.read_cement_material()
            + self.score_data.reader.read_casing_materials()
            + self.score_data.reader.read_tubing_materials()
            + self.score_data.reader.read_lithology_materials()
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

    def _convert_fluids(self) -> List[FluidModelPvt]:
        """Convert the fluids used in the annuli."""
        # NOTE: for now the converter only uses PVT table model
        return [FluidModelPvt(name) for name in self.score_data.get_all_annular_fluid_names()]

    def _convert_options(self) -> Options:
        return Options(
            thermal_property_update_mode=ThermalPropertyUpdateMode.FIRST_TIME_STEP,
            is_gas_lift_on=self.score_data.has_gas_lift(),
        )

    def build_plugin_description(self) -> PluginDescription:
        """Generate the configured node with data of the current operation."""
        annuli = self._convert_annuli()
        fluids = self._convert_fluids()
        materials = self._convert_solid_mechanical_properties()
        options = self._convert_options()
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
            "Options": {"name": "Options", **options.to_dict()},
        }
        return PluginDescription(
            name="apb",
            gui_models=gui_models,
            is_enabled=True,
        )
