from typing import List

import attr
from alfasim_sdk import MassInflowSplitType
from alfasim_sdk import MassSourceNodePropertiesDescription
from alfasim_sdk import MassSourceType
from alfasim_sdk import MultiInputType
from alfasim_sdk import NodeDescription
from alfasim_sdk import PressureNodePropertiesDescription
from alfasim_sdk._internal.constants import GAS_PHASE
from alfasim_sdk._internal.constants import OIL_PHASE
from alfasim_sdk._internal.constants import WATER_PHASE

from alfasim_score.constants import GAS_LIFT_MASS_NODE_NAME
from alfasim_score.constants import NULL_VOLUMETRIC_FLOW_RATE
from alfasim_score.constants import WELLBORE_BOTTOM_NODE_NAME
from alfasim_score.constants import WELLBORE_TOP_NODE_NAME
from alfasim_score.converter.alfacase.convert_alfacase import ScoreAlfacaseConverter
from alfasim_score.converter.alfacase.score_input_reader import ScoreInputReader


class BaseOperationBuilder(ScoreAlfacaseConverter):
    def __init__(self, score_reader: ScoreInputReader):
        super().__init__(score_reader)

    def build_nodes(self) -> List[NodeDescription]:
        operation_data = self.score_input.read_operation_data()
        default_nodes = {node.name: node for node in super().build_nodes()}
        configured_nodes = [
            attr.evolve(
                default_nodes.pop(WELLBORE_TOP_NODE_NAME),
                mass_source_properties=MassSourceNodePropertiesDescription(
                    temperature_input_type=MultiInputType.Constant,
                    source_type=MassSourceType.AllVolumetricFlowRates,
                    volumetric_flow_rates_std={
                        GAS_PHASE: -1.0
                        * operation_data["gas_oil_ratio"].GetValue()
                        * operation_data["oil_flow_rate"],
                        OIL_PHASE: -1.0 * operation_data["oil_flow_rate"],
                        WATER_PHASE: -1.0 * operation_data["water_flow_rate"],
                    },
                ),
            ),
            attr.evolve(
                default_nodes.pop(WELLBORE_BOTTOM_NODE_NAME),
                pressure_properties=PressureNodePropertiesDescription(
                    temperature=operation_data["flow_initial_temperature"],
                    pressure=operation_data["flow_initial_pressure"],
                    split_type=MassInflowSplitType.Pvt,
                ),
            ),
        ]
        if GAS_LIFT_MASS_NODE_NAME in default_nodes:
            gas_lift_data = self.score_input.read_operation_method_data()
            configured_nodes.append(
                attr.evolve(
                    default_nodes.pop(GAS_LIFT_MASS_NODE_NAME),
                    mass_source_properties=MassSourceNodePropertiesDescription(
                        temperature_input_type=MultiInputType.Constant,
                        temperature=gas_lift_data["well_head_temperature"],
                        source_type=MassSourceType.AllVolumetricFlowRates,
                        volumetric_flow_rates_std={
                            GAS_PHASE: gas_lift_data["well_head_flow"],
                            OIL_PHASE: NULL_VOLUMETRIC_FLOW_RATE,
                            WATER_PHASE: NULL_VOLUMETRIC_FLOW_RATE,
                        },
                    ),
                )
            )
        return configured_nodes