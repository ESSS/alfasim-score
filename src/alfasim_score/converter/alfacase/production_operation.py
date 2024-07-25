import attr
from alfasim_sdk import AnnulusEquipmentDescription
from alfasim_sdk import CaseDescription
from alfasim_sdk import InitialConditionsDescription
from alfasim_sdk import InitialPressuresDescription
from alfasim_sdk import InitialTemperaturesDescription
from alfasim_sdk import InitialVelocitiesDescription
from alfasim_sdk import InitialVolumeFractionsDescription
from alfasim_sdk import MassInflowSplitType
from alfasim_sdk import MassSourceNodePropertiesDescription
from alfasim_sdk import MassSourceType
from alfasim_sdk import MultiInputType
from alfasim_sdk import PressureContainerDescription
from alfasim_sdk import PressureNodePropertiesDescription
from alfasim_sdk import TableInputType
from alfasim_sdk import TemperaturesContainerDescription
from alfasim_sdk import VelocitiesContainerDescription
from alfasim_sdk import VolumeFractionsContainerDescription
from alfasim_sdk._internal.constants import FLUID_GAS
from alfasim_sdk._internal.constants import FLUID_OIL
from alfasim_sdk._internal.constants import FLUID_WATER
from barril.units import Array
from barril.units import Scalar
from pathlib import Path

from alfasim_score.common import OperationType
from alfasim_score.constants import GAS_LIFT_MASS_NODE_NAME
from alfasim_score.constants import NULL_VOLUMETRIC_FLOW_RATE
from alfasim_score.constants import WELLBORE_BOTTOM_NODE_NAME
from alfasim_score.constants import WELLBORE_TOP_NODE_NAME
from alfasim_score.converter.alfacase.base_operation import BaseOperationBuilder
from alfasim_score.units import FRACTION_UNIT
from alfasim_score.units import LENGTH_UNIT
from alfasim_score.units import PRESSURE_UNIT
from alfasim_score.units import TEMPERATURE_UNIT
from alfasim_score.units import VELOCITY_UNIT


class ProductionOperationBuilder(BaseOperationBuilder):
    def __init__(self, score_filepath: Path):
        super().__init__(score_filepath)
        assert (
            self.operation_type == OperationType.PRODUCTION
        ), f"The created operation is production operation, but the imported operation is configured as {self.operation_type}."
        # TODO: check exported variables
        # self.default_output_profiles = []

    def configure_nodes(self, alfacase: CaseDescription) -> None:
        """Configure the nodes with data from SCORE operation."""
        operation_data = self.score_input.read_operation_data()
        default_nodes = {node.name: node for node in alfacase.nodes}
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
                pvt_model=self.alfacase_converter.get_fluid_model_name(),
            ),
            attr.evolve(
                default_nodes.pop(WELLBORE_BOTTOM_NODE_NAME),
                pressure_properties=PressureNodePropertiesDescription(
                    temperature=operation_data["flow_initial_temperature"],
                    pressure=operation_data["flow_initial_pressure"],
                    split_type=MassInflowSplitType.Pvt,
                ),
                pvt_model=self.alfacase_converter.get_fluid_model_name(),
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
                    pvt_model=self.alfacase_converter.get_fluid_model_name(),
                )
            )
        else:
            # just use the original gas lift node with zero flow rate
            configured_nodes.append(default_nodes.pop(GAS_LIFT_MASS_NODE_NAME))
        alfacase.nodes = configured_nodes

    def configure_annulus(self, alfacase: CaseDescription) -> None:
        """Configure the annulus with data from SCORE operation."""
        initial_temperature = Scalar(15.0, TEMPERATURE_UNIT)
        initial_pressure = Scalar(5000.0, PRESSURE_UNIT)
        if self.has_gas_lift():
            operation_data = self.score_input.read_operation_method_data()
            initial_pressure = operation_data["well_head_pressure"]
            initial_temperature = operation_data["well_head_temperature"]
        alfacase.wells[0].annulus = attr.evolve(
            alfacase.wells[0].annulus,
            has_annulus_flow=self.has_gas_lift(),
            equipment=AnnulusEquipmentDescription(
                gas_lift_valves=self._get_gas_lift_valves(),
            ),
            initial_conditions=InitialConditionsDescription(
                pressures=InitialPressuresDescription(
                    position_input_type=TableInputType.length,
                    table_length=PressureContainerDescription(
                        positions=Array([0.0], LENGTH_UNIT),
                        pressures=Array([initial_pressure.GetValue()], PRESSURE_UNIT),
                    ),
                ),
                volume_fractions=InitialVolumeFractionsDescription(
                    position_input_type=TableInputType.length,
                    table_length=VolumeFractionsContainerDescription(
                        positions=Array([0.0], LENGTH_UNIT),
                        fractions={
                            FLUID_GAS: Array([1.0], FRACTION_UNIT),
                            FLUID_OIL: Array([0.0], FRACTION_UNIT),
                            FLUID_WATER: Array([0.0], FRACTION_UNIT),
                        },
                    ),
                ),
                velocities=InitialVelocitiesDescription(
                    position_input_type=TableInputType.length,
                    table_length=VelocitiesContainerDescription(
                        positions=Array([0.0], LENGTH_UNIT),
                        velocities={
                            FLUID_GAS: Array([0.0], VELOCITY_UNIT),
                            FLUID_OIL: Array([0.0], VELOCITY_UNIT),
                            FLUID_WATER: Array([0.0], VELOCITY_UNIT),
                        },
                    ),
                ),
                temperatures=InitialTemperaturesDescription(
                    position_input_type=TableInputType.length,
                    table_length=TemperaturesContainerDescription(
                        positions=Array([0.0], LENGTH_UNIT),
                        temperatures=Array([initial_temperature.GetValue()], TEMPERATURE_UNIT),
                    ),
                ),
            ),
        )
