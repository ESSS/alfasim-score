from typing import Any
from typing import Dict
from typing import List

from barril.units import Scalar

from alfasim_score.common import AnnulusLabel
from alfasim_score.common import LiftMethod
from alfasim_score.constants import ANNULUS_DEPTH_TOLERANCE
from alfasim_score.converter.alfacase.score_input_reader import ScoreInputReader


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
        well_start_position = self.general_data["water_depth"] + self.general_data["air_gap"]
        return position - well_start_position

    def get_all_annular_fluid_names(self) -> List[str]:
        """Get the list of fluid names registered as annulus fluids in tubing and casing of SCORE data."""
        all_fluids = set([fluid["name"] for fluid in self.reader.read_tubing_fluid_data()])
        for casings in self.reader.read_casings():
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

    def get_well_length(self) -> Scalar:
        """Calculate the well length configured in SCORE file."""
        return self.get_position_in_well(self.reader.read_general_data()["final_md"])

    def get_annuli_list(self) -> List[AnnulusLabel]:
        """Get the list of active annuli configured in the input file"""
        annuli_data = self.reader.read_operation_annuli_data()
        total_annuli = len(annuli_data)
        return list(AnnulusLabel)[:total_annuli]
