import attr
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
from pathlib import Path

from alfasim_score.common import FluidType
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


class InjectionOperationBuilder(BaseOperationBuilder):
    def __init__(self, score_filepath: Path):
        super().__init__(score_filepath)
        self.operation_type = OperationType.INJECTION
        score_operation_type = self.score_input.read_operation_type()
        assert (
            self.operation_type == score_operation_type
        ), f"The created operation is injection, but the imported operation is configured as {score_operation_type}."
        # TODO: check exported variables
        # self.default_output_profiles = []

    def configure_well_initial_conditions(self, alfacase: CaseDescription) -> None:
        """Configure the well initial conditions with default values."""
        well_length = self.alfacase_converter.get_position_in_well(
            self.score_input.read_general_data()["final_md"]
        )
        operation_data = self.score_input.read_injection_operation_data()
        formation_data = self.score_input.read_formation_temperatures()
        initial_bottom_pressure = operation_data["flow_initial_pressure"].GetValue(PRESSURE_UNIT)
        # the factor multiplied for the top pressure is arbitrary, just to set an initial value
        initial_top_pressure = 0.6 * initial_bottom_pressure
        alfacase.wells[0].initial_conditions = InitialConditionsDescription(
            pressures=InitialPressuresDescription(
                position_input_type=TableInputType.length,
                table_length=PressureContainerDescription(
                    positions=Array([0.0, well_length.GetValue()], LENGTH_UNIT),
                    pressures=Array([initial_top_pressure, initial_bottom_pressure], PRESSURE_UNIT),
                ),
            ),
            volume_fractions=InitialVolumeFractionsDescription(
                position_input_type=TableInputType.length,
                table_length=VolumeFractionsContainerDescription(
                    positions=Array([0.0], LENGTH_UNIT),
                    fractions={
                        FLUID_GAS: Array([0.1], FRACTION_UNIT),
                        FLUID_OIL: Array([0.9], FRACTION_UNIT),
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
                    positions=Array([0.0, well_length.GetValue()], LENGTH_UNIT),
                    temperatures=Array(
                        [
                            operation_data["flow_initial_temperature"].GetValue(TEMPERATURE_UNIT),
                            formation_data["temperatures"].GetValues(TEMPERATURE_UNIT)[-1],
                        ],
                        TEMPERATURE_UNIT,
                    ),
                ),
            ),
        )

    def configure_nodes(self, alfacase: CaseDescription) -> None:
        """Configure the nodes with data from SCORE operation."""
        operation_data = self.score_input.read_injection_operation_data()
        default_nodes = {node.name: node for node in alfacase.nodes}
        # TODO: review the fractions depending on injected fluid, in case of gas (or oil?)
        # TODO: review the nodes top, bottom in the pressure/mass type regard
        configured_nodes = [
            attr.evolve(
                default_nodes.pop(WELLBORE_TOP_NODE_NAME),
                mass_source_properties=MassSourceNodePropertiesDescription(
                    temperature_input_type=MultiInputType.Constant,
                    source_type=MassSourceType.AllVolumetricFlowRates,
                    volumetric_flow_rates_std={
                        FLUID_GAS: NULL_VOLUMETRIC_FLOW_RATE,
                        FLUID_OIL: NULL_VOLUMETRIC_FLOW_RATE,
                        FLUID_WATER: (
                            operation_data["flow_rate"]
                            if operation_data["fluid_type"] == FluidType.WATER
                            else NULL_VOLUMETRIC_FLOW_RATE
                        ),
                    },
                ),
                pvt_model=self._get_fluid_model_name(),
            ),
            attr.evolve(
                default_nodes.pop(WELLBORE_BOTTOM_NODE_NAME),
                pressure_properties=PressureNodePropertiesDescription(
                    temperature=operation_data["flow_initial_temperature"],
                    pressure=operation_data["flow_initial_pressure"],
                    split_type=MassInflowSplitType.Pvt,
                ),
                pvt_model=self._get_fluid_model_name(),
            ),
        ]
        # just use the original gas lift node with zero flow rate
        configured_nodes.append(default_nodes.pop(GAS_LIFT_MASS_NODE_NAME))
        alfacase.nodes = configured_nodes
