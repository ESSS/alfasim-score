from typing import Dict

import attr
from alfasim_sdk import CaseDescription
from alfasim_sdk import CaseOutputDescription
from alfasim_sdk import EnergyModel
from alfasim_sdk import GasLiftValveEquipmentDescription
from alfasim_sdk import GlobalTrendDescription
from alfasim_sdk import HydrodynamicModelType
from alfasim_sdk import InitialConditionsDescription
from alfasim_sdk import InitialPressuresDescription
from alfasim_sdk import InitialTemperaturesDescription
from alfasim_sdk import InitialVelocitiesDescription
from alfasim_sdk import InitialVolumeFractionsDescription
from alfasim_sdk import MassInflowSplitType
from alfasim_sdk import MassSourceNodePropertiesDescription
from alfasim_sdk import MassSourceType
from alfasim_sdk import MultiInputType
from alfasim_sdk import NodeCellType
from alfasim_sdk import NodeDescription
from alfasim_sdk import OutputAttachmentLocation
from alfasim_sdk import PhysicsDescription
from alfasim_sdk import PressureContainerDescription
from alfasim_sdk import PressureNodePropertiesDescription
from alfasim_sdk import ProfileOutputDescription
from alfasim_sdk import PvtModelCorrelationDescription
from alfasim_sdk import PvtModelsDescription
from alfasim_sdk import TableInputType
from alfasim_sdk import TemperaturesContainerDescription
from alfasim_sdk import TrendsOutputDescription
from alfasim_sdk import ValveType
from alfasim_sdk import VelocitiesContainerDescription
from alfasim_sdk import VolumeFractionsContainerDescription
from alfasim_sdk._internal.constants import FLUID_GAS
from alfasim_sdk._internal.constants import FLUID_OIL
from alfasim_sdk._internal.constants import FLUID_WATER
from barril.units import Array
from barril.units import Scalar
from copy import deepcopy
from pathlib import Path

from alfasim_score.common import LiftMethod
from alfasim_score.common import ModelFluidType
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
from alfasim_score.constants import WELLBORE_NAME
from alfasim_score.constants import WELLBORE_TOP_NODE_NAME
from alfasim_score.converter.alfacase.convert_alfacase import ScoreAlfacaseConverter
from alfasim_score.converter.alfacase.score_input_reader import ScoreInputReader
from alfasim_score.units import FRACTION_UNIT
from alfasim_score.units import LENGTH_UNIT
from alfasim_score.units import PRESSURE_UNIT
from alfasim_score.units import TEMPERATURE_UNIT
from alfasim_score.units import VELOCITY_UNIT


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

    def _get_fluid_model_name(self) -> ModelFluidType:
        """Get the name of the fluid model used for this operation."""
        return self.score_input.read_operation_fluid_data()["name"]

    def configure_pvt_model(self, alfacase: CaseDescription) -> None:
        """Configure the black-oil fluid for the model."""
        fluid_data = self.score_input.read_operation_fluid_data()
        alfacase.pvt_models = PvtModelsDescription(
            correlations={
                fluid_data["name"]: PvtModelCorrelationDescription(
                    oil_density_std=convert_api_gravity_to_oil_density(fluid_data["api_gravity"]),
                    gas_density_std=convert_gas_gravity_to_gas_density(fluid_data["gas_gravity"]),
                    rs_sat=fluid_data["gas_oil_ratio"],
                    h2s_mol_frac=H2S_MOLAR_FRACTION_DEFAULT,
                    co2_mol_frac=CO2_MOLAR_FRACTION_DEFAULT,
                )
            }
        )

    def configure_well_initial_conditions(self, alfacase: CaseDescription) -> None:
        """Configure the well initial conditions with default values."""
        well_length = self.alfacase_converter.get_position_in_well(
            self.score_input.read_general_data()["final_md"]
        )
        operation_data = self.score_input.read_operation_data()
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
                            formation_data["temperatures"].GetValues(TEMPERATURE_UNIT)[0],
                            operation_data["flow_initial_temperature"].GetValue(TEMPERATURE_UNIT),
                        ],
                        TEMPERATURE_UNIT,
                    ),
                ),
            ),
        )

    def configure_outputs(self, alfacase: CaseDescription) -> None:
        """Configure the outputs for the case."""
        alfacase.outputs = CaseOutputDescription(
            trends=TrendsOutputDescription(
                global_trends=[GlobalTrendDescription(curve_names=["timestep"])]
            ),
            profiles=[
                ProfileOutputDescription(
                    curve_names=[],
                    location=OutputAttachmentLocation.Main,
                    element_name=WELLBORE_NAME,
                )
            ],
        )

    # TODO PWPA-1996: review the configurations done here.
    def configure_physics(self, alfacase: CaseDescription) -> None:
        """Configure the description for the physics data."""
        alfacase.physics = PhysicsDescription(
            hydrodynamic_model=HydrodynamicModelType.ThreeLayersGasOilWater,
            energy_model=EnergyModel.GlobalModel,
        )

    def configure_nodes(self, alfacase: CaseDescription) -> None:
        """Configure the nodes data. Default configuration is done by the alfacase converter."""
        alfacase.nodes = [
            NodeDescription(
                name=WELLBORE_TOP_NODE_NAME,
                node_type=NodeCellType.MassSource,
                pvt_model=self._get_fluid_model_name(),
                mass_source_properties=MassSourceNodePropertiesDescription(
                    temperature_input_type=MultiInputType.Constant,
                    source_type=MassSourceType.AllVolumetricFlowRates,
                    volumetric_flow_rates_std={
                        FLUID_GAS: NULL_VOLUMETRIC_FLOW_RATE,
                        FLUID_OIL: NULL_VOLUMETRIC_FLOW_RATE,
                        FLUID_WATER: NULL_VOLUMETRIC_FLOW_RATE,
                    },
                ),
            ),
            NodeDescription(
                name=WELLBORE_BOTTOM_NODE_NAME,
                node_type=NodeCellType.Pressure,
                pvt_model=self._get_fluid_model_name(),
                pressure_properties=PressureNodePropertiesDescription(
                    split_type=MassInflowSplitType.Pvt,
                ),
            ),
            NodeDescription(
                name=GAS_LIFT_MASS_NODE_NAME,
                node_type=NodeCellType.MassSource,
                pvt_model=self._get_fluid_model_name(),
                mass_source_properties=MassSourceNodePropertiesDescription(
                    temperature_input_type=MultiInputType.Constant,
                    source_type=MassSourceType.AllVolumetricFlowRates,
                    volumetric_flow_rates_std={
                        FLUID_GAS: NULL_VOLUMETRIC_FLOW_RATE,
                        FLUID_OIL: NULL_VOLUMETRIC_FLOW_RATE,
                        FLUID_WATER: NULL_VOLUMETRIC_FLOW_RATE,
                    },
                ),
            ),
        ]

    def configure_annulus(self, alfacase: CaseDescription) -> None:
        """
        Configure the annulus data.
        Default configuration is done by the alfacase converter.
        """
        pass

    def generate_operation_alfacase_description(self) -> CaseDescription:
        """Generate the configured node with data of the current operation."""
        alfacase_configured = deepcopy(self.base_alfacase)
        self.configure_physics(alfacase_configured)
        self.configure_pvt_model(alfacase_configured)
        self.configure_outputs(alfacase_configured)
        self.configure_nodes(alfacase_configured)
        self.configure_well_initial_conditions(alfacase_configured)
        self.configure_annulus(alfacase_configured)
        return alfacase_configured
