from typing import Dict

import attr
from alfasim_sdk import CaseDescription
from alfasim_sdk import GasLiftValveEquipmentDescription
from alfasim_sdk import OutputAttachmentLocation
from alfasim_sdk import ProfileOutputDescription
from alfasim_sdk import ValveType
from copy import deepcopy
from pathlib import Path

from alfasim_score.common import LiftMethod
from alfasim_score.common import OperationType
from alfasim_score.constants import GAS_LIFT_VALVE_DEFAULT_DELTA_P_MIN
from alfasim_score.constants import GAS_LIFT_VALVE_DEFAULT_DIAMETER
from alfasim_score.constants import GAS_LIFT_VALVE_DEFAULT_DISCHARGE
from alfasim_score.constants import GAS_LIFT_VALVE_NAME
from alfasim_score.constants import WELLBORE_NAME
from alfasim_score.converter.alfacase.convert_alfacase import ScoreAlfacaseConverter
from alfasim_score.converter.alfacase.score_input_reader import ScoreInputReader


class BaseOperationBuilder:
    def __init__(self, score_filepath: Path):
        self.score_input = ScoreInputReader(score_filepath)
        self.alfacase_converter = ScoreAlfacaseConverter(self.score_input)
        self.base_alfacase = self.alfacase_converter.build_base_alfacase_description()
        self.operation_type = self.score_input.read_operation_data()["type"]
        self.default_output_profiles = [
            "elevation",
            "flow pattern",
            "gas phase volume fraction",
            "holdup",
            "liquid mass flow rate",
            "liquid volumetric flow rate std",
            "mixture temperature",
            "oil phase volume fraction",
            "pressure",
            "total gas mass flow rate",
            "total gas volumetric flow rate std",
            "total mass flow rate",
            "total oil mass flow rate",
            "total oil volumetric flow rate std",
            "total water mass flow rate",
            "total water volumetric flow rate std",
            "water phase volume fraction",
        ]

    def has_gas_lift(self) -> bool:
        """Check the operation has gas lift."""
        return self.score_input.read_operation_data()["lift_method"] == LiftMethod.GAS_LIFT

    def _get_gas_lift_valves(self) -> Dict[str, GasLiftValveEquipmentDescription]:
        """Create the gas lift valves for the annulus."""
        if not self.has_gas_lift():
            return {}
        gas_lift_data = self.score_input.read_operation_method_data()
        valves = {
            f"{GAS_LIFT_VALVE_NAME}_1": GasLiftValveEquipmentDescription(
                position=self.alfacase_converter.get_position_in_well(gas_lift_data["valve_depth"]),
                diameter=GAS_LIFT_VALVE_DEFAULT_DIAMETER,
                valve_type=ValveType.CheckValve,
                delta_p_min=GAS_LIFT_VALVE_DEFAULT_DELTA_P_MIN,
                discharge_coefficient=GAS_LIFT_VALVE_DEFAULT_DISCHARGE,
            )
        }
        return valves

    def configure_nodes(self, alfacase: CaseDescription) -> None:
        """Configure the nodes data. Default configuration is done by the alfacase converter."""
        pass

    def configure_annulus(self, alfacase: CaseDescription) -> None:
        """Configure the annulus data. Default configuration is done by the alfacase converter."""
        pass

    def configure_output_profiles(self, alfacase: CaseDescription) -> None:
        """Build the output profiles data for the well."""
        alfacase.outputs = attr.evolve(
            alfacase.outputs,
            profiles=[
                ProfileOutputDescription(
                    curve_names=self.default_output_profiles,
                    location=OutputAttachmentLocation.Main,
                    element_name=WELLBORE_NAME,
                )
            ],
        )

    def generate_operation_alfacase_description(self) -> CaseDescription:
        """Generate the configured node with data of the current operation."""
        alfacase_configured = deepcopy(self.base_alfacase)
        self.configure_nodes(alfacase_configured)
        self.configure_annulus(alfacase_configured)
        self.configure_output_profiles(alfacase_configured)
        return alfacase_configured
