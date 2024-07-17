from typing import Dict
from typing import List

import attr
from alfasim_sdk import AnnulusDescription
from alfasim_sdk import AnnulusEquipmentDescription
from alfasim_sdk import GasLiftValveEquipmentDescription
from alfasim_sdk import InitialConditionsDescription
from alfasim_sdk import InitialPressuresDescription
from alfasim_sdk import InitialTemperaturesDescription
from alfasim_sdk import InitialVelocitiesDescription
from alfasim_sdk import InitialVolumeFractionsDescription
from alfasim_sdk import MassInflowSplitType
from alfasim_sdk import MassSourceNodePropertiesDescription
from alfasim_sdk import MassSourceType
from alfasim_sdk import MultiInputType
from alfasim_sdk import NodeDescription
from alfasim_sdk import PressureContainerDescription
from alfasim_sdk import PressureNodePropertiesDescription
from alfasim_sdk import TableInputType
from alfasim_sdk import ValveType
from alfasim_sdk import WellDescription
from alfasim_sdk._internal.constants import FLUID_GAS
from alfasim_sdk._internal.constants import FLUID_OIL
from alfasim_sdk._internal.constants import FLUID_WATER

from alfasim_score.common import LiftMethod
from alfasim_score.common import ModelFluidType
from alfasim_score.constants import GAS_LIFT_MASS_NODE_NAME
from alfasim_score.constants import GAS_LIFT_VALVE_DEFAULT_DELTA_P_MIN
from alfasim_score.constants import GAS_LIFT_VALVE_DEFAULT_DIAMETER
from alfasim_score.constants import GAS_LIFT_VALVE_DEFAULT_DISCHARGE
from alfasim_score.constants import GAS_LIFT_VALVE_NAME
from alfasim_score.constants import NULL_VOLUMETRIC_FLOW_RATE
from alfasim_score.constants import WELLBORE_BOTTOM_NODE_NAME
from alfasim_score.constants import WELLBORE_TOP_NODE_NAME
from alfasim_score.converter.alfacase.convert_alfacase import ScoreAlfacaseConverter
from alfasim_score.converter.alfacase.score_input_reader import ScoreInputReader


class BaseOperationBuilder(ScoreAlfacaseConverter):
    def __init__(self, score_reader: ScoreInputReader):
        super().__init__(score_reader)

    def has_gas_lift(self) -> bool:
        """Check the operation has gas lift."""
        return self.score_input.read_operation_data()["lift_method"] == LiftMethod.GAS_LIFT

    def _get_gas_lift_valves(self) -> Dict[str, GasLiftValveEquipmentDescription]:
        """Create the gas lift valves for the annulus."""
        gas_lift_data = self.score_input.read_operation_method_data()
        valves = {
            f"{GAS_LIFT_VALVE_NAME}_1": GasLiftValveEquipmentDescription(
                position=self._get_position_in_well(gas_lift_data["valve_depth"]),
                diameter=GAS_LIFT_VALVE_DEFAULT_DIAMETER,
                valve_type=ValveType.CheckValve,
                delta_p_min=GAS_LIFT_VALVE_DEFAULT_DELTA_P_MIN,
                discharge_coefficient=GAS_LIFT_VALVE_DEFAULT_DISCHARGE,
            )
        }
        return valves

    def build_annulus(self) -> AnnulusDescription:
        """Configure the annulus with data from SCORE operation."""
        return AnnulusDescription(
            has_annulus_flow=self.has_gas_lift(),
            pvt_model=self.get_fluid_model_name(),
            equipment=AnnulusEquipmentDescription(
                gas_lift_valves=self._get_gas_lift_valves(),
            ),
            top_node=GAS_LIFT_MASS_NODE_NAME,
        )

    def build_nodes(self) -> List[NodeDescription]:
        """ "Configure the nodes with data from SCORE operation."""
        operation_data = self.score_input.read_operation_data()
        default_nodes = {node.name: node for node in super().build_nodes()}
        configured_nodes = [
            attr.evolve(
                default_nodes.pop(WELLBORE_TOP_NODE_NAME),
                mass_source_properties=MassSourceNodePropertiesDescription(
                    temperature_input_type=MultiInputType.Constant,
                    source_type=MassSourceType.AllVolumetricFlowRates,
                    volumetric_flow_rates_std={
                        FLUID_GAS: -1.0
                        * operation_data["gas_oil_ratio"].GetValue()
                        * operation_data["oil_flow_rate"],
                        FLUID_OIL: -1.0 * operation_data["oil_flow_rate"],
                        FLUID_WATER: -1.0 * operation_data["water_flow_rate"],
                    },
                ),
                pvt_model=self.get_fluid_model_name(),
            ),
            attr.evolve(
                default_nodes.pop(WELLBORE_BOTTOM_NODE_NAME),
                pressure_properties=PressureNodePropertiesDescription(
                    temperature=operation_data["flow_initial_temperature"],
                    pressure=operation_data["flow_initial_pressure"],
                    split_type=MassInflowSplitType.Pvt,
                ),
                pvt_model=self.get_fluid_model_name(),
            ),
        ]
        if self.has_gas_lift():
            gas_lift_data = self.score_input.read_operation_method_data()
            configured_nodes.append(
                attr.evolve(
                    default_nodes.pop(GAS_LIFT_MASS_NODE_NAME),
                    mass_source_properties=MassSourceNodePropertiesDescription(
                        temperature_input_type=MultiInputType.Constant,
                        temperature=gas_lift_data["well_head_temperature"],
                        source_type=MassSourceType.AllVolumetricFlowRates,
                        volumetric_flow_rates_std={
                            FLUID_GAS: gas_lift_data["well_head_flow"],
                            FLUID_OIL: NULL_VOLUMETRIC_FLOW_RATE,
                            FLUID_WATER: NULL_VOLUMETRIC_FLOW_RATE,
                        },
                    ),
                    pvt_model=self.get_fluid_model_name(),
                )
            )
        return configured_nodes

    def build_well(self) -> WellDescription:
        """Create the description for the well."""
        return attr.evolve(
            super().build_well(),
            pvt_model=self.get_fluid_model_name(),
        )
