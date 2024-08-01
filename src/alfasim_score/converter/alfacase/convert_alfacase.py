from typing import List

from alfasim_sdk import AnnulusDescription
from alfasim_sdk import CaseDescription
from alfasim_sdk import CasingDescription
from alfasim_sdk import CasingSectionDescription
from alfasim_sdk import EnvironmentDescription
from alfasim_sdk import EnvironmentPropertyDescription
from alfasim_sdk import FormationDescription
from alfasim_sdk import FormationLayerDescription
from alfasim_sdk import MaterialDescription
from alfasim_sdk import MaterialType
from alfasim_sdk import NodeCellType
from alfasim_sdk import NodeDescription
from alfasim_sdk import OpenHoleDescription
from alfasim_sdk import PackerDescription
from alfasim_sdk import PipeEnvironmentHeatTransferCoefficientModelType
from alfasim_sdk import PipeThermalModelType
from alfasim_sdk import PipeThermalPositionInput
from alfasim_sdk import ProfileDescription
from alfasim_sdk import TubingDescription
from alfasim_sdk import WellDescription
from alfasim_sdk import XAndYDescription
from barril.units import Scalar

from alfasim_score.common import convert_quota_to_tvd
from alfasim_score.constants import CASING_DEFAULT_ROUGHNESS
from alfasim_score.constants import CEMENT_NAME
from alfasim_score.constants import FLUID_DEFAULT_NAME
from alfasim_score.constants import GAS_LIFT_MASS_NODE_NAME
from alfasim_score.constants import REFERENCE_VERTICAL_COORDINATE
from alfasim_score.constants import ROCK_DEFAULT_HEAT_TRANSFER_COEFFICIENT
from alfasim_score.constants import ROCK_DEFAULT_ROUGHNESS
from alfasim_score.constants import TUBING_DEFAULT_ROUGHNESS
from alfasim_score.constants import WELLBORE_BOTTOM_NODE_NAME
from alfasim_score.constants import WELLBORE_NAME
from alfasim_score.constants import WELLBORE_TOP_NODE_NAME
from alfasim_score.converter.alfacase.score_input_reader import ScoreInputReader
from alfasim_score.units import LENGTH_UNIT
from alfasim_score.units import TEMPERATURE_UNIT


def filter_duplicated_materials(
    material_list: List[MaterialDescription],
) -> List[MaterialDescription]:
    """Remove the duplicated materials parsed by the reader."""
    filtered = {material.name: material for material in material_list}
    return list(filtered.values())


def get_section_top_of_filler(
    filler_depth: Scalar, hanger_depth: Scalar, final_depth: Scalar
) -> Scalar:
    """Get the depth of filler in the current casing section."""
    if filler_depth > final_depth:
        return final_depth
    if filler_depth <= hanger_depth:
        return hanger_depth
    return filler_depth


class ScoreAlfacaseConverter:
    def __init__(self, score_reader: ScoreInputReader):
        self.score_input = score_reader
        self.general_data = score_reader.read_general_data()
        self.well_start_position = self.general_data["water_depth"] + self.general_data["air_gap"]

    def get_position_in_well(self, position: Scalar) -> Scalar:
        """Get the position relative to the well start position."""
        return position - self.well_start_position

    def _convert_well_trajectory(self) -> ProfileDescription:
        """
        Convert the trajectory for the imported well.
        NOTE: all positions don't start to count as zero at ANM, but they use the same values
        from the input SCORE file.
        """
        x, y = self.score_input.read_well_trajectory()
        return ProfileDescription(x_and_y=XAndYDescription(x=x, y=y))

    def _convert_materials(self) -> List[MaterialDescription]:
        """Convert list of materials from SCORE file."""
        material_descriptions = []
        material_list = (
            self.score_input.read_cement_material()
            + self.score_input.read_casing_materials()
            + self.score_input.read_tubing_materials()
            + self.score_input.read_lithology_materials()
            + self.score_input.read_packer_fluid()
        )
        for material in material_list:
            material_descriptions.append(
                MaterialDescription(
                    name=material["name"],
                    material_type=MaterialType(material["type"]),
                    density=material["density"],
                    thermal_conductivity=material["thermal_conductivity"],
                    heat_capacity=material["specific_heat"],
                    expansion=material["thermal_expansion"],
                )
            )
        return filter_duplicated_materials(material_descriptions)

    def _convert_formation(self) -> FormationDescription:
        """Create the description for the formations."""
        layers = [
            FormationLayerDescription(
                name=f"formation_{i}",
                start=convert_quota_to_tvd(
                    formation["top_elevation"], self.general_data["air_gap"]
                ),
                material=formation["material"],
            )
            for i, formation in enumerate(self.score_input.read_formations(), start=1)
        ]
        return FormationDescription(
            reference_y_coordinate=REFERENCE_VERTICAL_COORDINATE, layers=layers
        )

    def _convert_well_environment(self) -> EnvironmentDescription:
        """Create the description for the formations environment."""
        environment_description = []
        temperature_profile = self.score_input.read_formation_temperatures()
        for elevation, temperature in zip(
            temperature_profile["elevations"].GetValues(LENGTH_UNIT),
            temperature_profile["temperatures"].GetValues(TEMPERATURE_UNIT),
        ):
            depth_tvd = convert_quota_to_tvd(
                Scalar(elevation, LENGTH_UNIT), self.general_data["air_gap"]
            )
            temperature = Scalar(temperature, TEMPERATURE_UNIT)
            environment_description.append(
                EnvironmentPropertyDescription(
                    position=depth_tvd,
                    temperature=temperature,
                    type=PipeEnvironmentHeatTransferCoefficientModelType.WallsAndEnvironment,
                    heat_transfer_coefficient=ROCK_DEFAULT_HEAT_TRANSFER_COEFFICIENT,
                )
            )
        return EnvironmentDescription(
            thermal_model=PipeThermalModelType.SteadyState,
            position_input_mode=PipeThermalPositionInput.Tvd,
            reference_y_coordinate=REFERENCE_VERTICAL_COORDINATE,
            tvd_properties_table=environment_description,
        )

    def _convert_casing_list(self) -> List[CasingSectionDescription]:
        """Create the description for the casings."""
        casing_sections = []
        for casing in self.score_input.read_casings():
            for i, section in enumerate(casing["sections"], 1):
                hanger_depth = self.get_position_in_well(section["top_md"])
                settings_depth = self.get_position_in_well(section["base_md"])
                filler_depth = self.get_position_in_well(casing["top_of_cement"])
                top_of_filler = get_section_top_of_filler(
                    filler_depth, hanger_depth, settings_depth
                )
                casing_sections.append(
                    CasingSectionDescription(
                        name=f"{casing['function'].value}_{casing['type'].value}_{i}",
                        hanger_depth=hanger_depth,
                        settings_depth=settings_depth,
                        hole_diameter=casing["hole_diameter"],
                        outer_diameter=section["outer_diameter"],
                        inner_diameter=section["inner_diameter"],
                        inner_roughness=CASING_DEFAULT_ROUGHNESS,
                        material=section["material"],
                        top_of_filler=top_of_filler,
                        filler_material=CEMENT_NAME,
                        # TODO PWPA-1970: review this fluid default with fluid actually used by SCORE file
                        material_above_filler=FLUID_DEFAULT_NAME,
                    )
                )
                i += 1
        return casing_sections

    def _convert_tubing_list(self) -> List[TubingDescription]:
        """Create the description for the tubing list."""
        tubing_sections = []
        for i, tubing in enumerate(self.score_input.read_tubing(), start=1):
            tubing_sections.append(
                TubingDescription(
                    name=f"TUBING_{i}",
                    length=tubing["base_md"] - tubing["top_md"],
                    outer_diameter=tubing["outer_diameter"],
                    inner_diameter=tubing["inner_diameter"],
                    inner_roughness=TUBING_DEFAULT_ROUGHNESS,
                    material=tubing["material"],
                )
            )
        return tubing_sections

    def _convert_packer_list(self) -> List[PackerDescription]:
        """Create the description for the packers."""
        packers = []
        for packer in self.score_input.read_packers():
            packers.append(
                PackerDescription(
                    name=packer["name"],
                    position=self.get_position_in_well(packer["position"]),
                    # TODO PWPA-1970: review this fluid default with fluid actually used by SCORE file
                    material_above=FLUID_DEFAULT_NAME,
                )
            )
        return packers

    def _convert_open_hole_list(self) -> List[OpenHoleDescription]:
        """Create the description for the open hole."""
        open_hole_list = []
        start_position = Scalar(
            max([casing["shoe_md"].GetValue() for casing in self.score_input.read_casings()]),
            LENGTH_UNIT,
            "length",
        )
        for i, open_hole in enumerate(self.score_input.read_open_hole(), start=1):
            open_hole_list.append(
                OpenHoleDescription(
                    name=f"OPEN_HOLE_{i}",
                    length=open_hole["final_md"] - start_position,
                    diameter=open_hole["hole_diameter"],
                    inner_roughness=ROCK_DEFAULT_ROUGHNESS,
                )
            )
            start_position = open_hole["final_md"]
        return open_hole_list

    def _convert_casings(self) -> CasingDescription:
        """Create the description for the casings."""
        return CasingDescription(
            casing_sections=self._convert_casing_list(),
            tubings=self._convert_tubing_list(),
            packers=self._convert_packer_list(),
            open_holes=self._convert_open_hole_list(),
        )

    def _build_default_nodes(self) -> List[NodeDescription]:
        """Create the description for the node list."""
        nodes = [
            NodeDescription(
                name=WELLBORE_TOP_NODE_NAME,
                node_type=NodeCellType.MassSource,
            ),
            NodeDescription(
                name=WELLBORE_BOTTOM_NODE_NAME,
                node_type=NodeCellType.Pressure,
            ),
            NodeDescription(
                name=GAS_LIFT_MASS_NODE_NAME,
                node_type=NodeCellType.MassSource,
            ),
        ]
        return nodes

    def _build_default_annulus(self) -> AnnulusDescription:
        """Create the description for the node list."""
        return AnnulusDescription(has_annulus_flow=False, top_node=GAS_LIFT_MASS_NODE_NAME)

    def _build_well(self) -> WellDescription:
        """Create the description for the well."""
        return WellDescription(
            name=WELLBORE_NAME,
            stagnant_fluid=FLUID_DEFAULT_NAME,
            profile=self._convert_well_trajectory(),
            casing=self._convert_casings(),
            annulus=self._build_default_annulus(),
            formation=self._convert_formation(),
            top_node=WELLBORE_TOP_NODE_NAME,
            bottom_node=WELLBORE_BOTTOM_NODE_NAME,
            environment=self._convert_well_environment(),
        )

    def build_base_alfacase_description(self) -> CaseDescription:
        """Create the minimal alfacase description with well geometry/materials and the default nodes."""
        return CaseDescription(
            name=self.general_data["case_name"],
            nodes=self._build_default_nodes(),
            wells=[self._build_well()],
            materials=self._convert_materials(),
        )
