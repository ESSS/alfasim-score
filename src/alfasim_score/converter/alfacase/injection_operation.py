import attr
from alfasim_sdk import CaseDescription
from alfasim_sdk import MassInflowSplitType
from alfasim_sdk import MassSourceNodePropertiesDescription
from alfasim_sdk import MassSourceType
from alfasim_sdk import MultiInputType
from alfasim_sdk import NodeCellType
from alfasim_sdk import PressureNodePropertiesDescription
from alfasim_sdk._internal.constants import FLUID_GAS
from alfasim_sdk._internal.constants import FLUID_OIL
from alfasim_sdk._internal.constants import FLUID_WATER
from barril.units import Scalar
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

    def configure_well_initial_conditions(self, alfacase: CaseDescription) -> None:
        """Configure the well initial conditions with default values."""
        super().configure_well_initial_conditions(alfacase)
        operation_data = self.score_input.read_injection_operation_data()
        formation_data = self.score_input.read_formation_temperatures()
        # once the simulation is configured as steady state regime for injection,
        # the expected value of injected phase is 1.0 when the steady state is reached
        gas_fraction = 1.0 if operation_data["fluid_type"] == FluidType.GAS else 0.0
        water_fraction = 1.0 if operation_data["fluid_type"] == FluidType.WATER else 0.0
        alfacase.wells[0].initial_conditions = attr.evolve(
            alfacase.wells[0].initial_conditions,
            # the factor multiplied for the top pressure is arbitrary, just to set an initial value
            pressures=self.create_well_initial_pressures(
                operation_data["flow_initial_pressure"],
                1.2 * operation_data["flow_initial_pressure"],
            ),
            volume_fractions=self.create_well_initial_volume_fractions(
                Scalar(0.0, FRACTION_UNIT),
                Scalar(gas_fraction, FRACTION_UNIT),
                Scalar(water_fraction, FRACTION_UNIT),
            ),
            temperatures=self.create_well_initial_temperatures(
                operation_data["flow_initial_temperature"],
                Scalar(formation_data["temperatures"][-1], TEMPERATURE_UNIT),
            ),
        )

    def configure_nodes(self, alfacase: CaseDescription) -> None:
        """Configure the nodes with data from SCORE operation."""
        super().configure_nodes(alfacase)
        operation_data = self.score_input.read_injection_operation_data()
        default_nodes = {node.name: node for node in alfacase.nodes}
        configured_nodes = [
            attr.evolve(
                default_nodes.pop(WELLBORE_TOP_NODE_NAME),
                node_type=NodeCellType.Pressure,
                pressure_properties=PressureNodePropertiesDescription(
                    temperature=operation_data["flow_initial_temperature"],
                    pressure=operation_data["flow_initial_pressure"],
                    split_type=MassInflowSplitType.Pvt,
                ),
                pvt_model=self._get_fluid_model_name(),
            ),
            attr.evolve(
                default_nodes.pop(WELLBORE_BOTTOM_NODE_NAME),
                node_type=NodeCellType.MassSource,
                mass_source_properties=MassSourceNodePropertiesDescription(
                    temperature_input_type=MultiInputType.Constant,
                    source_type=MassSourceType.AllVolumetricFlowRates,
                    volumetric_flow_rates_std={
                        FLUID_GAS: (
                            -1.0 * operation_data["flow_rate"]
                            if operation_data["fluid_type"] == FluidType.GAS
                            else NULL_VOLUMETRIC_FLOW_RATE
                        ),
                        FLUID_OIL: NULL_VOLUMETRIC_FLOW_RATE,
                        FLUID_WATER: (
                            -1.0 * operation_data["flow_rate"]
                            if operation_data["fluid_type"] == FluidType.WATER
                            else NULL_VOLUMETRIC_FLOW_RATE
                        ),
                    },
                ),
                pvt_model=self._get_fluid_model_name(),
            ),
        ]
        # just use the original gas lift node with zero flow rate
        configured_nodes.append(default_nodes.pop(GAS_LIFT_MASS_NODE_NAME))
        alfacase.nodes = configured_nodes
