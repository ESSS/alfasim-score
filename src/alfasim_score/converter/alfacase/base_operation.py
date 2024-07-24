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
from alfasim_sdk import OutputAttachmentLocation
from alfasim_sdk import PressureContainerDescription
from alfasim_sdk import PressureNodePropertiesDescription
from alfasim_sdk import ProfileOutputDescription
from alfasim_sdk import TableInputType
from alfasim_sdk import TemperaturesContainerDescription
from alfasim_sdk import ValveType
from alfasim_sdk import VelocitiesContainerDescription
from alfasim_sdk import VolumeFractionsContainerDescription
from alfasim_sdk import WellDescription
from alfasim_sdk._internal.constants import FLUID_GAS
from alfasim_sdk._internal.constants import FLUID_OIL
from alfasim_sdk._internal.constants import FLUID_WATER
from barril.units import Array
from barril.units import Scalar

from alfasim_score.common import LiftMethod
from alfasim_score.constants import GAS_LIFT_MASS_NODE_NAME
from alfasim_score.constants import GAS_LIFT_VALVE_DEFAULT_DELTA_P_MIN
from alfasim_score.constants import GAS_LIFT_VALVE_DEFAULT_DIAMETER
from alfasim_score.constants import GAS_LIFT_VALVE_DEFAULT_DISCHARGE
from alfasim_score.constants import GAS_LIFT_VALVE_NAME
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


class BaseOperationBuilder(ScoreAlfacaseConverter):
    def __init__(self, score_reader: ScoreInputReader):
        super().__init__(score_reader)
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
                position=self.get_position_in_well(gas_lift_data["valve_depth"]),
                diameter=GAS_LIFT_VALVE_DEFAULT_DIAMETER,
                valve_type=ValveType.CheckValve,
                delta_p_min=GAS_LIFT_VALVE_DEFAULT_DELTA_P_MIN,
                discharge_coefficient=GAS_LIFT_VALVE_DEFAULT_DISCHARGE,
            )
        }
        return valves

    def build_annulus(self) -> AnnulusDescription:
        """Configure the annulus with data from SCORE operation."""
        operation_data = self.score_input.read_operation_method_data()
        initial_temperature = Scalar(15.0, TEMPERATURE_UNIT)
        initial_pressure = Scalar(5000.0, PRESSURE_UNIT)
        if self.has_gas_lift():
            initial_temperature = operation_data["well_head_temperature"]
            initial_pressure = operation_data["well_head_pressure"]
        return AnnulusDescription(
            has_annulus_flow=self.has_gas_lift(),
            pvt_model=self.get_fluid_model_name(),
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
        well_length = self.get_position_in_well(self.score_input.read_general_data()["final_md"])
        operation_data = self.score_input.read_operation_data()
        formation_data = self.score_input.read_formation_temperatures()
        initial_bottom_pressure = operation_data["flow_initial_pressure"].GetValue(PRESSURE_UNIT)
        # the factor multiplied for the top pressure is arbitrary, just to set an initial value
        initial_top_pressure = 0.6 * initial_bottom_pressure
        return attr.evolve(
            super().build_well(),
            pvt_model=self.get_fluid_model_name(),
            initial_conditions=InitialConditionsDescription(
                pressures=InitialPressuresDescription(
                    position_input_type=TableInputType.length,
                    table_length=PressureContainerDescription(
                        positions=Array([0.0, well_length.GetValue()], LENGTH_UNIT),
                        pressures=Array(
                            [initial_top_pressure, initial_bottom_pressure], PRESSURE_UNIT
                        ),
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
                                operation_data["flow_initial_temperature"].GetValue(
                                    TEMPERATURE_UNIT
                                ),
                            ],
                            TEMPERATURE_UNIT,
                        ),
                    ),
                ),
            ),
        )

    def build_output_profiles(self) -> List[ProfileOutputDescription]:
        """Build the output profiles data for the well."""
        return [
            ProfileOutputDescription(
                curve_names=self.default_output_profiles,
                location=OutputAttachmentLocation.Main,
                element_name=WELLBORE_NAME,
            )
        ]
