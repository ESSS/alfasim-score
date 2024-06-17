from alfasim_sdk import AnnulusDescription
from alfasim_sdk import FormationDescription
from alfasim_sdk import ProfileDescription
from alfasim_sdk import WellDescription
from alfasim_sdk import XAndYDescription
from barril.units import Scalar

from alfasim_score.constants import ANNULUS_TOP_NODE_NAME
from alfasim_score.constants import WELLBORE_BOTTOM_NODE
from alfasim_score.constants import WELLBORE_TOP_NODE
from alfasim_score.converter.alfacase.score_input_reader import ScoreInputReader
from alfasim_score.units import LENGTH_UNIT


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

    # TODO PWPA-1937: implement this method
    def _convert_annulus(self) -> AnnulusDescription:
        return AnnulusDescription(has_annulus_flow=False, top_node=ANNULUS_TOP_NODE_NAME)

    # TODO PWPA-1934: implement this method
    def _convert_formation(self) -> AnnulusDescription:
        return FormationDescription(reference_y_coordinate=Scalar(0.0, "m", "length"))

    def build_well(self) -> WellDescription:
        return WellDescription(
            name=self.well_name,
            profile=self._convert_well_trajectory(),
            annulus=self._convert_annulus(),
            formation=self._convert_formation(),
            top_node=WELLBORE_TOP_NODE,
            bottom_node=WELLBORE_BOTTOM_NODE,
        )
