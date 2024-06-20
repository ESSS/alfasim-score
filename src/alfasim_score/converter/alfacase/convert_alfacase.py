from typing import List

from alfasim_sdk import AnnulusDescription
from alfasim_sdk import CasingDescription
from alfasim_sdk import CasingSectionDescription
from alfasim_sdk import FormationDescription
from alfasim_sdk import MaterialDescription
from alfasim_sdk import MaterialType
from alfasim_sdk import OpenHoleDescription
from alfasim_sdk import PackerDescription
from alfasim_sdk import ProfileDescription
from alfasim_sdk import TubingDescription
from alfasim_sdk import WellDescription
from alfasim_sdk import XAndYDescription
from barril.units import Scalar

from alfasim_score.constants import ANNULUS_TOP_NODE_NAME
from alfasim_score.constants import CASING_DEFAULT_ROUGHNESS
from alfasim_score.constants import CEMENT_NAME
from alfasim_score.constants import ROCK_DEFAULT_ROUGHNESS
from alfasim_score.constants import TUBING_DEFAULT_ROUGHNESS
from alfasim_score.constants import WELLBORE_BOTTOM_NODE
from alfasim_score.constants import WELLBORE_TOP_NODE
from alfasim_score.converter.alfacase.score_input_reader import ScoreInputReader
from alfasim_score.units import LENGTH_UNIT


def filter_duplicated_materials(
    material_list: List[MaterialDescription],
) -> List[MaterialDescription]:
    """Remove the duplicated materials parsed by the reader"""
    filtered = {material.name: material for material in material_list}
    return list(filtered.values())


class ScoreAlfacaseConverter:
    def __init__(self, score_reader: ScoreInputReader):
        self.score_input = score_reader
        self.well_name = score_reader.input_content["name"]

    def _convert_well_trajectory(self) -> ProfileDescription:
        """
        Convert the trajectory for the imported well.
        NOTE: all positions don't start to count as zero at ANM, but they use the same values
        from the input SCORE file.
        """
        x, y = self.score_input.read_well_trajectory()
        return ProfileDescription(x_and_y=XAndYDescription(x=x, y=y))

    def convert_materials(self) -> List[MaterialDescription]:
        """Convert list of materials from SCORE file"""
        material_descriptions = []
        material_list = (
            self.score_input.read_cement_material()
            + self.score_input.read_casing_materials()
            + self.score_input.read_tubing_materials()
            + self.score_input.read_lithology_materials()
        )

        for data in material_list:
            material_descriptions.append(
                MaterialDescription(
                    name=data["name"],
                    material_type=MaterialType.Solid,
                    density=data["density"],
                    thermal_conductivity=data["thermal_conductivity"],
                    heat_capacity=data["specific_heat"],
                    expansion=data["thermal_expansion"],
                )
            )
        return filter_duplicated_materials(material_descriptions)

    # TODO PWPA-1937: implement this method
    def _convert_annulus(self) -> AnnulusDescription:
        return AnnulusDescription(has_annulus_flow=False, top_node=ANNULUS_TOP_NODE_NAME)

    # TODO PWPA-1934: implement this method
    def _convert_formation(self) -> AnnulusDescription:
        return FormationDescription(reference_y_coordinate=Scalar(0.0, "m", "length"))

    def _convert_casing_list(self) -> List[CasingSectionDescription]:
        """Create the description for the casings."""
        casing_sections = []
        i = 1
        for data in self.score_input.read_casings():
            for section in data["sections"]:
                casing_sections.append(
                    CasingSectionDescription(
                        name=f"{data['function']}_{data['type']}_{i}",
                        hanger_depth=section["top_md"],
                        settings_depth=section["base_md"],
                        hole_diameter=data["hole_diameter"],
                        outer_diameter=section["outer_diameter"],
                        inner_diameter=section["inner_diameter"],
                        inner_roughness=CASING_DEFAULT_ROUGHNESS,
                        material=section["material"],
                        top_of_filler=data["top_of_cement"],
                        filler_material=CEMENT_NAME,
                        material_above_filler=data["material_above_filler"],
                    )
                )
                i += 1
        return casing_sections

    def _convert_tubing_list(self) -> List[TubingDescription]:
        """Create the description for the tubing list."""
        tubing_sections = []
        for i, data in enumerate(self.score_input.read_tubing(), start=1):
            tubing_sections.append(
                TubingDescription(
                    name=f"TUBING_{i}",
                    length=data["base_md"] - data["top_md"],
                    outer_diameter=data["outer_diameter"],
                    inner_diameter=data["inner_diameter"],
                    inner_roughness=TUBING_DEFAULT_ROUGHNESS,
                    material=data["material"],
                )
            )
        return tubing_sections

    def _convert_packer_list(self) -> List[PackerDescription]:
        """Create the description for the packers."""
        packers = []
        for data in self.score_input.read_packers():
            packers.append(
                PackerDescription(
                    name=data["name"],
                    position=data["position"],
                    material_above=data["material_above"],
                )
            )
        return packers

    def _convert_open_hole_list(self) -> List[OpenHoleDescription]:
        """Create the description for the open hole."""
        open_hole = []
        start_position = Scalar(
            max([data["shoe_md"].GetValue() for data in self.score_input.read_casings()]),
            LENGTH_UNIT,
            "length",
        )
        for i, data in enumerate(self.score_input.read_open_hole(), start=1):
            open_hole.append(
                OpenHoleDescription(
                    name=f"OPEN_HOLE_{i}",
                    length=data["final_md"] - start_position,
                    diameter=data["hole_diameter"],
                    inner_roughness=ROCK_DEFAULT_ROUGHNESS,
                )
            )
            start_position = data["final_md"]
        return open_hole

    def _convert_casings(self) -> WellDescription:
        """Create the description for the casings."""
        return CasingDescription(
            casing_sections=self._convert_casing_list(),
            tubings=self._convert_tubing_list(),
            packers=self._convert_packer_list(),
            open_holes=self._convert_open_hole_list(),
        )

    def build_well(self) -> WellDescription:
        """Create the description for the well."""
        return WellDescription(
            name=self.well_name,
            profile=self._convert_well_trajectory(),
            casing=self._convert_casings(),
            annulus=self._convert_annulus(),
            formation=self._convert_formation(),
            top_node=WELLBORE_TOP_NODE,
            bottom_node=WELLBORE_BOTTOM_NODE,
        )
