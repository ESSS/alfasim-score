from alfasim_sdk import CaseDescription
from alfasim_sdk import CaseOutputDescription
from alfasim_sdk import EnergyModel
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
from alfasim_sdk import TableInputType
from alfasim_sdk import TemperaturesContainerDescription
from alfasim_sdk import TrendsOutputDescription
from alfasim_sdk import VelocitiesContainerDescription
from alfasim_sdk import VolumeFractionsContainerDescription
from alfasim_sdk._internal.constants import FLUID_GAS
from alfasim_sdk._internal.constants import FLUID_OIL
from alfasim_sdk._internal.constants import FLUID_WATER
from barril.units import Array
from copy import deepcopy
from pathlib import Path

from alfasim_score.common import ModelFluidType
from alfasim_score.constants import GAS_LIFT_MASS_NODE_NAME
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
        self.default_output_profiles = [
            "elevation",
            "holdup",
            "liquid volumetric flow rate std",
            "mixture temperature",
            "pressure",
            "environment temperature",
        ]

    def _get_fluid_model_name(self) -> str:
        """Get the name of the fluid model used for this operation."""
        return self.score_input.read_fluid_name()

    def configure_pvt_model(self, alfacase: CaseDescription) -> None:
        """Configure the pvt fluid for the model."""
        pass

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
        pass

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
