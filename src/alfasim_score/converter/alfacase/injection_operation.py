import attr
import numpy as np
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
from alfasim_score.converter.alfacase.score_input_reader import ScoreInputReader
from alfasim_score.units import FRACTION_UNIT
from alfasim_score.units import TEMPERATURE_UNIT


class InjectionOperationBuilder(BaseOperationBuilder):
    def __init__(self, score_input_reader: ScoreInputReader):
        super().__init__(score_input_reader)
        self.operation_type = OperationType.INJECTION
        assert (
            self.general_data["type"] == self.operation_type
        ), f"The created operation is injection, but the imported operation is configured as {self.general_data['type']}."

    def is_injecting(self, fluid_type: FluidType) -> bool:
        """Check if the operation has water or gas injected into the well."""
        has_inlet_flow = self.general_data["flow_rate"].GetValue() > 0.0
        return has_inlet_flow and self.general_data["fluid_type"] == fluid_type

    def configure_well_initial_conditions(self, alfacase: CaseDescription) -> None:
        """Configure the well initial conditions with default values."""
        super().configure_well_initial_conditions(alfacase)
        formation_data = self.score_input.read_formation_temperatures()
        # once the simulation is configured as steady state regime for injection,
        # the expected value of injected phase is 1.0 when the steady state is reached
        gas_fraction = 1.0 if self.is_injecting(FluidType.GAS) else 0.0
        water_fraction = 1.0 if self.is_injecting(FluidType.WATER) else 0.0
        alfacase.wells[0].initial_conditions = attr.evolve(
            alfacase.wells[0].initial_conditions,
            # the factor multiplied by the bottom pressure is arbitrary, just to set an initial value
            pressures=self.create_well_initial_pressures(
                self.general_data["flow_initial_pressure"],
                1.2 * self.general_data["flow_initial_pressure"],
            ),
            volume_fractions=self.create_well_initial_volume_fractions(
                Scalar(0.0, FRACTION_UNIT),
                Scalar(gas_fraction, FRACTION_UNIT),
                Scalar(water_fraction, FRACTION_UNIT),
            ),
            temperatures=self.create_well_initial_temperatures(
                self.general_data["flow_initial_temperature"],
                Scalar(formation_data["temperatures"][-1], TEMPERATURE_UNIT),
            ),
        )

    def configure_nodes(self, alfacase: CaseDescription) -> None:
        """Configure the nodes with data from SCORE operation."""
        super().configure_nodes(alfacase)
        default_nodes = {node.name: node for node in alfacase.nodes}
        configured_nodes = [
            attr.evolve(
                default_nodes.pop(WELLBORE_TOP_NODE_NAME),
                node_type=NodeCellType.Pressure,
                pressure_properties=PressureNodePropertiesDescription(
                    temperature=self.general_data["flow_initial_temperature"],
                    pressure=self.general_data["flow_initial_pressure"],
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
                            -1.0 * self.general_data["flow_rate"]
                            if self.is_injecting(FluidType.GAS)
                            else NULL_VOLUMETRIC_FLOW_RATE
                        ),
                        FLUID_OIL: NULL_VOLUMETRIC_FLOW_RATE,
                        FLUID_WATER: (
                            -1.0 * self.general_data["flow_rate"]
                            if self.is_injecting(FluidType.WATER)
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
