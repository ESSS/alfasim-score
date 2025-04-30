from typing import Union

from alfasim_sdk import CaseDescription
from alfasim_sdk import CaseOutputDescription
from alfasim_sdk import EnergyModel
from alfasim_sdk import GlobalTrendDescription
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
from alfasim_sdk import NodeCellType
from alfasim_sdk import NodeDescription
from alfasim_sdk import NumericalOptionsDescription
from alfasim_sdk import OutputAttachmentLocation
from alfasim_sdk import PhysicsDescription
from alfasim_sdk import PressureContainerDescription
from alfasim_sdk import PressureNodePropertiesDescription
from alfasim_sdk import ProfileOutputDescription
from alfasim_sdk import PvtModelsDescription
from alfasim_sdk import SimulationRegimeType
from alfasim_sdk import TableInputType
from alfasim_sdk import TemperaturesContainerDescription
from alfasim_sdk import TimeOptionsDescription
from alfasim_sdk import TrendsOutputDescription
from alfasim_sdk import VelocitiesContainerDescription
from alfasim_sdk import VolumeFractionsContainerDescription
from alfasim_sdk._internal.constants import FLUID_GAS
from alfasim_sdk._internal.constants import FLUID_OIL
from alfasim_sdk._internal.constants import FLUID_WATER
from barril.units import Array
from barril.units import Scalar
from copy import deepcopy
from pathlib import Path

from alfasim_score.common import OperationType
from alfasim_score.constants import GAS_LIFT_MASS_NODE_NAME
from alfasim_score.constants import INITIAL_TIMESTEP
from alfasim_score.constants import MAXIMUM_TIMESTEP
from alfasim_score.constants import MAXIMUM_TIMESTEP_CHANGE_FACTOR
from alfasim_score.constants import MINIMUM_TIMESTEP
from alfasim_score.constants import NULL_VOLUMETRIC_FLOW_RATE
from alfasim_score.constants import NUMERICAL_TOLERANCE
from alfasim_score.constants import WELLBORE_BOTTOM_NODE_NAME
from alfasim_score.constants import WELLBORE_NAME
from alfasim_score.constants import WELLBORE_TOP_NODE_NAME
from alfasim_score.converter.alfacase.convert_alfacase import ScoreAlfacaseConverter
from alfasim_score.converter.alfacase.convert_plugin_data import ScoreAPBPluginConverter
from alfasim_score.converter.alfacase.score_input_data import ScoreInputData
from alfasim_score.converter.alfacase.score_input_reader import ScoreInputReader
from alfasim_score.units import FRACTION_UNIT
from alfasim_score.units import LENGTH_UNIT
from alfasim_score.units import PRESSURE_UNIT
from alfasim_score.units import TEMPERATURE_UNIT
from alfasim_score.units import VELOCITY_UNIT


class BaseOperationBuilder:
    def __init__(self, score_input_data: ScoreInputData):
        self.operation_type: Union[None, OperationType] = None
        self.score_data = score_input_data
        self.base_alfacase = ScoreAlfacaseConverter(
            self.score_data
        ).build_base_alfacase_description()
        self.plugin_converters = [ScoreAPBPluginConverter(self.score_data)]
        self.default_output_profiles = [
            "elevation",
            "holdup",
            "liquid volumetric flow rate std",
            "mixture temperature",
            "pressure",
            "environment temperature",
            "annulus_a_temperature",
            "annulus_b_temperature",
            "annulus_c_temperature",
            "annulus_d_temperature",
            "annulus_e_temperature",
            "annulus_a_pressure",
            "annulus_b_pressure",
            "annulus_c_pressure",
            "annulus_d_pressure",
            "annulus_e_pressure",
            "wall_0_temperature",
            "wall_1_temperature",
            "wall_2_temperature",
            "wall_3_temperature",
            "wall_4_temperature",
            "wall_5_temperature",
        ]

    def assert_operation_type(self, operation: OperationType) -> None:
        """Make sure the configured operation is the same of that configured in SCORE input."""
        score_configured_operation = self.score_data.operation_data["type"]
        assert (
            operation == score_configured_operation
        ), f"The created operation is production, but the imported operation is configured as {score_configured_operation}."

    def create_well_initial_pressures(
        self, top_pressure: Scalar, bottom_pressure: Scalar
    ) -> InitialPressuresDescription:
        """Create the initial pressures description."""
        well_length = self.score_data.get_well_length()
        return InitialPressuresDescription(
            position_input_type=TableInputType.length,
            table_length=PressureContainerDescription(
                positions=Array([0.0, well_length.GetValue(LENGTH_UNIT)], LENGTH_UNIT),
                pressures=Array(
                    [top_pressure.GetValue(PRESSURE_UNIT), bottom_pressure.GetValue(PRESSURE_UNIT)],
                    PRESSURE_UNIT,
                ),
            ),
        )

    def create_well_initial_temperatures(
        self, top_temperature: Scalar, bottom_temperature: Scalar
    ) -> InitialTemperaturesDescription:
        """Create the initial temperatures description."""
        well_length = self.score_data.get_well_length()
        return InitialTemperaturesDescription(
            position_input_type=TableInputType.length,
            table_length=TemperaturesContainerDescription(
                positions=Array([0.0, well_length.GetValue()], LENGTH_UNIT),
                temperatures=Array(
                    [
                        top_temperature.GetValue(TEMPERATURE_UNIT),
                        bottom_temperature.GetValue(TEMPERATURE_UNIT),
                    ],
                    TEMPERATURE_UNIT,
                ),
            ),
        )

    def create_well_initial_volume_fractions(
        self, oil_fraction: Scalar, gas_fraction: Scalar, water_fraction: Scalar
    ) -> InitialVolumeFractionsDescription:
        """Create the initial volume fractions description."""
        return InitialVolumeFractionsDescription(
            position_input_type=TableInputType.length,
            table_length=VolumeFractionsContainerDescription(
                positions=Array([0.0], LENGTH_UNIT),
                fractions={
                    FLUID_OIL: Array([oil_fraction.GetValue(FRACTION_UNIT)], FRACTION_UNIT),
                    FLUID_GAS: Array([gas_fraction.GetValue(FRACTION_UNIT)], FRACTION_UNIT),
                    FLUID_WATER: Array([water_fraction.GetValue(FRACTION_UNIT)], FRACTION_UNIT),
                },
            ),
        )

    def configure_pvt_model(self, alfacase: CaseDescription) -> None:
        """
        Configure the pvt fluid for the model.
        This method do not include the pvt tables provided by SCORE because they are
        already used in the proper plugin section otherwise ALFAsim complains about duplication.
        """
        operation_fluid = self.score_data.operation_data["fluid"]
        tables = {"base": Path(f"{operation_fluid}.tab")}
        alfacase.pvt_models = PvtModelsDescription(
            default_model="base",
            tables=tables,
        )

    def configure_outputs(self, alfacase: CaseDescription) -> None:
        """Configure the outputs for the case."""
        alfacase.outputs = CaseOutputDescription(
            trends=TrendsOutputDescription(
                global_trends=[GlobalTrendDescription(curve_names=["timestep"])]
            ),
            profiles=[
                ProfileOutputDescription(
                    curve_names=self.default_output_profiles,
                    location=OutputAttachmentLocation.Main,
                    element_name=WELLBORE_NAME,
                )
            ],
        )

    def configure_well_initial_conditions(self, alfacase: CaseDescription) -> None:
        """Configure the well initial conditions with default values."""
        alfacase.wells[0].initial_conditions = InitialConditionsDescription(
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
        )

    def configure_physics(self, alfacase: CaseDescription) -> None:
        """Configure the description for the physics data."""
        alfacase.physics = PhysicsDescription(
            hydrodynamic_model=HydrodynamicModelType.ThreeLayersGasOilWater,
            energy_model=EnergyModel.GlobalModel,
            # TODO: Switch to transient because the steady-state simulation is not converging.
            # Need to check how this setting comes from SCORE,
            # since it's unclear why we always assume steady-state for the production.
            simulation_regime=SimulationRegimeType.Transient,
            initial_condition_strategy=InitialConditionStrategyType.Constant,
        )

    def configure_time_options(self, alfacase: CaseDescription) -> None:
        """Configure the description for the time options data."""
        alfacase.time_options = TimeOptionsDescription(
            final_time=self.score_data.operation_data["duration"],
            initial_timestep=INITIAL_TIMESTEP,
            minimum_timestep=MINIMUM_TIMESTEP,
            maximum_timestep=MAXIMUM_TIMESTEP,
        )

    def configure_numerical_options(self, alfacase: CaseDescription) -> None:
        """Configure the description for the numerical options data."""
        alfacase.numerical_options = NumericalOptionsDescription(
            maximum_timestep_change_factor=MAXIMUM_TIMESTEP_CHANGE_FACTOR,
            tolerance=NUMERICAL_TOLERANCE,
        )

    def configure_nodes(self, alfacase: CaseDescription) -> None:
        """Configure the nodes data. Default configuration is done by the alfacase converter."""
        alfacase.nodes = [
            NodeDescription(
                name=WELLBORE_TOP_NODE_NAME,
                node_type=NodeCellType.MassSource,
                pvt_model=self.score_data.operation_data["fluid"],
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
                pvt_model=self.score_data.operation_data["fluid"],
                pressure_properties=PressureNodePropertiesDescription(
                    split_type=MassInflowSplitType.Pvt,
                ),
            ),
            NodeDescription(
                name=GAS_LIFT_MASS_NODE_NAME,
                node_type=NodeCellType.MassSource,
                pvt_model=self.score_data.operation_data["fluid"],
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

    def configure_plugin_descriptions(
        self,
        alfacase: CaseDescription,
    ) -> None:
        """Configure in the case description the data for configured plugin list."""
        for plugin_converter in self.plugin_converters:
            alfacase.plugins.append(plugin_converter.build_plugin_description())

    def generate_operation_alfacase_description(self) -> CaseDescription:
        """Generate the configured alfacase description for the current operation."""
        alfacase_configured = deepcopy(self.base_alfacase)
        self.configure_physics(alfacase_configured)
        self.configure_time_options(alfacase_configured)
        self.configure_numerical_options(alfacase_configured)
        self.configure_pvt_model(alfacase_configured)
        self.configure_outputs(alfacase_configured)
        self.configure_nodes(alfacase_configured)
        self.configure_well_initial_conditions(alfacase_configured)
        self.configure_annulus(alfacase_configured)
        self.configure_plugin_descriptions(alfacase_configured)
        return alfacase_configured
