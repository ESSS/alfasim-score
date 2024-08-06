from typing import Dict

import attr
import numpy as np
from alfasim_sdk import AnnulusEquipmentDescription
from alfasim_sdk import CaseDescription
from alfasim_sdk import GasLiftValveEquipmentDescription
from alfasim_sdk import HydrodynamicModelType
from alfasim_sdk import InitialConditionsDescription
from alfasim_sdk import InitialConditionStrategyType
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
from alfasim_sdk import PvtModelCorrelationDescription
from alfasim_sdk import PvtModelsDescription
from alfasim_sdk import SimulationRegimeType
from alfasim_sdk import TableInputType
from alfasim_sdk import TemperaturesContainerDescription
from alfasim_sdk import ValveType
from alfasim_sdk import VelocitiesContainerDescription
from alfasim_sdk import VolumeFractionsContainerDescription
from alfasim_sdk._internal.constants import FLUID_GAS
from alfasim_sdk._internal.constants import FLUID_OIL
from alfasim_sdk._internal.constants import FLUID_WATER
from barril.units import Array
from barril.units import Scalar
from pathlib import Path

from alfasim_score.common import LiftMethod
from alfasim_score.common import OperationType
from alfasim_score.common import convert_api_gravity_to_oil_density
from alfasim_score.common import convert_gas_gravity_to_gas_density
from alfasim_score.constants import CO2_MOLAR_FRACTION_DEFAULT
from alfasim_score.constants import GAS_LIFT_MASS_NODE_NAME
from alfasim_score.constants import GAS_LIFT_VALVE_DEFAULT_DELTA_P_MIN
from alfasim_score.constants import GAS_LIFT_VALVE_DEFAULT_DIAMETER
from alfasim_score.constants import GAS_LIFT_VALVE_DEFAULT_DISCHARGE
from alfasim_score.constants import GAS_LIFT_VALVE_NAME
from alfasim_score.constants import H2S_MOLAR_FRACTION_DEFAULT
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
        self.operation_type = OperationType.PRODUCTION
        self.lift_method_data = self.score_input.read_operation_method_data()
        self.produced_fluid_data = self.score_input.read_operation_fluid_data()
        assert (
            self.general_data["type"] == self.operation_type
        ), f"The created operation is production, but the imported operation is configured as {self.general_data['type']}."

    def has_gas_lift(self) -> bool:
        """Check if the operation has gas lift."""
        return self.general_data["lift_method"] == LiftMethod.GAS_LIFT

    def has_water(self, alfacase: CaseDescription) -> bool:
        """Check if the operation has water in the well."""
        has_inlet_water = self.general_data["water_flow_rate"].GetValue() > 0.0
        has_initial_water = np.any(
            alfacase.wells[0].initial_conditions.volume_fractions.table_length.fractions.get(
                FLUID_WATER, 0.0
            )
            > 0.0
        )
        return has_inlet_water or has_initial_water

    def _get_gas_lift_valves(self) -> Dict[str, GasLiftValveEquipmentDescription]:
        """Create the gas lift valves for the annulus."""
        if not self.has_gas_lift():
            return {}
        valves = {
            f"{GAS_LIFT_VALVE_NAME}_1": GasLiftValveEquipmentDescription(
                position=self.alfacase_converter.get_position_in_well(
                    self.lift_method_data["valve_depth"]
                ),
                diameter=GAS_LIFT_VALVE_DEFAULT_DIAMETER,
                valve_type=ValveType.CheckValve,
                delta_p_min=GAS_LIFT_VALVE_DEFAULT_DELTA_P_MIN,
                discharge_coefficient=GAS_LIFT_VALVE_DEFAULT_DISCHARGE,
            )
        }
        return valves

    def configure_pvt_model(self, alfacase: CaseDescription) -> None:
        """Configure the black-oil fluid for the model."""
        super().configure_pvt_model(alfacase)
        alfacase.pvt_models = PvtModelsDescription(
            correlations={
                self.produced_fluid_data["name"]: PvtModelCorrelationDescription(
                    oil_density_std=convert_api_gravity_to_oil_density(
                        self.produced_fluid_data["api_gravity"]
                    ),
                    gas_density_std=convert_gas_gravity_to_gas_density(
                        self.produced_fluid_data["gas_gravity"]
                    ),
                    rs_sat=self.produced_fluid_data["gas_oil_ratio"],
                    h2s_mol_frac=H2S_MOLAR_FRACTION_DEFAULT,
                    co2_mol_frac=CO2_MOLAR_FRACTION_DEFAULT,
                )
            }
        )

    def configure_well_initial_conditions(self, alfacase: CaseDescription) -> None:
        """Configure the well initial conditions with default values."""
        super().configure_well_initial_conditions(alfacase)
        formation_data = self.score_input.read_formation_temperatures()
        alfacase.wells[0].initial_conditions = attr.evolve(
            alfacase.wells[0].initial_conditions,
            # the factor multiplied by the top pressure is arbitrary, just to set an initial value
            pressures=self.create_well_initial_pressures(
                0.6 * self.general_data["flow_initial_pressure"],
                self.general_data["flow_initial_pressure"],
            ),
            volume_fractions=self.create_well_initial_volume_fractions(
                Scalar(0.9, FRACTION_UNIT),
                Scalar(0.1, FRACTION_UNIT),
                Scalar(0.0, FRACTION_UNIT),
            ),
            temperatures=self.create_well_initial_temperatures(
                Scalar(formation_data["temperatures"][0], TEMPERATURE_UNIT),
                self.general_data["flow_initial_temperature"],
            ),
        )

    def configure_physics(self, alfacase: CaseDescription) -> None:
        """Configure the description for the physics data."""
        super().configure_physics(alfacase)
        alfacase.physics = attr.evolve(
            alfacase.physics,
            hydrodynamic_model=(
                HydrodynamicModelType.ThreeLayersGasOilWater
                if self.has_water(alfacase)
                else HydrodynamicModelType.FourFields
            ),
            simulation_regime=(
                SimulationRegimeType.Transient
                if self.has_gas_lift()
                else SimulationRegimeType.SteadyState
            ),
        )

    def configure_nodes(self, alfacase: CaseDescription) -> None:
        """Configure the nodes with data from SCORE operation."""
        super().configure_nodes(alfacase)
        default_nodes = {node.name: node for node in alfacase.nodes}
        configured_nodes = [
            attr.evolve(
                default_nodes.pop(WELLBORE_TOP_NODE_NAME),
                mass_source_properties=MassSourceNodePropertiesDescription(
                    temperature_input_type=MultiInputType.Constant,
                    source_type=MassSourceType.AllVolumetricFlowRates,
                    volumetric_flow_rates_std={
                        FLUID_GAS: -1.0
                        * self.general_data["gas_oil_ratio"].GetValue()
                        * self.general_data["oil_flow_rate"],
                        FLUID_OIL: -1.0 * self.general_data["oil_flow_rate"],
                        FLUID_WATER: -1.0 * self.general_data["water_flow_rate"],
                    },
                ),
                pvt_model=self._get_fluid_model_name(),
            ),
            attr.evolve(
                default_nodes.pop(WELLBORE_BOTTOM_NODE_NAME),
                pressure_properties=PressureNodePropertiesDescription(
                    temperature=self.general_data["flow_initial_temperature"],
                    pressure=self.general_data["flow_initial_pressure"],
                    split_type=MassInflowSplitType.Pvt,
                ),
                pvt_model=self._get_fluid_model_name(),
            ),
        ]
        gas_lift_node = default_nodes.pop(GAS_LIFT_MASS_NODE_NAME)
        if self.has_gas_lift():
            gas_lift_node = attr.evolve(
                gas_lift_node,
                mass_source_properties=MassSourceNodePropertiesDescription(
                    temperature_input_type=MultiInputType.Constant,
                    temperature=self.lift_method_data["well_head_temperature"],
                    source_type=MassSourceType.AllVolumetricFlowRates,
                    volumetric_flow_rates_std={
                        FLUID_GAS: self.lift_method_data["well_head_flow"],
                        FLUID_OIL: NULL_VOLUMETRIC_FLOW_RATE,
                        FLUID_WATER: NULL_VOLUMETRIC_FLOW_RATE,
                    },
                ),
                pvt_model=self._get_fluid_model_name(),
            )
        configured_nodes.append(gas_lift_node)
        alfacase.nodes = configured_nodes

    def configure_annulus(self, alfacase: CaseDescription) -> None:
        """Configure the annulus with data from SCORE operation."""
        super().configure_annulus(alfacase)
        initial_temperature = Scalar(15.0, TEMPERATURE_UNIT)
        initial_pressure = Scalar(5000.0, PRESSURE_UNIT)
        if self.has_gas_lift():
            initial_pressure = self.lift_method_data["well_head_pressure"]
            initial_temperature = self.lift_method_data["well_head_temperature"]
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
