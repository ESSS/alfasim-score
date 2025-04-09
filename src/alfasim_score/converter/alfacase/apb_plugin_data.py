from typing import Any
from typing import Dict
from typing import List
from typing import Union

from barril.units import Array
from barril.units import Scalar
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from enum import Enum

from alfasim_score.common import AnnulusLabel
from alfasim_score.common import AnnulusModeType
from alfasim_score.common import FluidModelType
from alfasim_score.units import LENGTH_UNIT
from alfasim_score.units import PRESSURE_UNIT
from alfasim_score.units import TEMPERATURE_UNIT
from alfasim_score.units import VOLUME_UNIT


class ThermalPropertyUpdateMode(str, Enum):
    DISABLED = "Disabled"
    FIRST_TIME_STEP = "First time step"
    ALL_TIME_STEP = "All time steps"


@dataclass
class PluginReferences:
    id_values: List[int]

    def to_dict(self) -> Dict[str, Union[str, Scalar]]:
        """Convert data to dict in order to write data to the alfacase."""
        return {
            "plugin_item_ids": self.id_values,
            "container_key": "FluidContainer",
        }


@dataclass
class FluidModelPvt:
    name: str

    def to_dict(self) -> Dict[str, Union[str, Scalar]]:
        """Convert data to dict in order to write data to the alfacase."""
        return {
            "name": self.name,
            "fluid_type": FluidModelType.PVT.value,
            "pvt_table_content": f"{self.name}.tab",
        }


@dataclass
class SolidMechanicalProperties:
    name: str
    young_modulus: Scalar
    poisson_ratio: Scalar
    thermal_expansion_coefficient: Scalar

    def to_dict(self) -> Dict[str, Any]:
        """Convert data to dict in order to write data to the alfacase."""
        return asdict(self)


@dataclass
class AnnulusDepthTable:
    initial_depths: Array = field(default_factory=lambda: Array([], LENGTH_UNIT))
    final_depths: Array = field(default_factory=lambda: Array([], LENGTH_UNIT))
    fluid_references: PluginReferences = field(default_factory=lambda: PluginReferences([]))

    def to_dict(self, annulus_label: AnnulusLabel) -> Dict[str, Any]:
        """Convert data to dict in order to write data to the alfacase."""
        columns = {
            f"fluid_initial_measured_depth_{annulus_label.value}": self.initial_depths,
            f"fluid_final_measured_depth_{annulus_label.value}": self.final_depths,
            f"fluid_name_{annulus_label.value}": self.fluid_references.to_dict(),
        }
        return {"columns": columns}


@dataclass
class AnnulusTemperatureTable:
    depths: Array = field(default_factory=lambda: Array([], LENGTH_UNIT))
    temperatures: Array = field(default_factory=lambda: Array([], TEMPERATURE_UNIT))

    def to_dict(self, annulus_label: AnnulusLabel) -> Dict[str, Any]:
        """Convert data to dict in order to write data to the alfacase."""
        columns = {
            f"temperature_depth_{annulus_label.value}": self.depths,
            f"temperature_{annulus_label.value}": self.temperatures,
        }
        return {"columns": columns}


@dataclass
class Annulus:
    is_active: bool = False
    mode_type: AnnulusModeType = AnnulusModeType.UNDISTURBED
    initial_top_pressure: Scalar = Scalar(0.0, PRESSURE_UNIT)
    is_open_seabed: bool = False
    annulus_depth_table: AnnulusDepthTable = field(default_factory=lambda: AnnulusDepthTable())
    annulus_temperature_table: AnnulusTemperatureTable = field(
        default_factory=lambda: AnnulusTemperatureTable()
    )
    has_fluid_return: bool = False
    initial_leakoff: Scalar = Scalar(0.0, VOLUME_UNIT)
    has_pressure_relief: bool = False
    pressure_relief: Scalar = Scalar(0.0, PRESSURE_UNIT)
    relief_position: Scalar = Scalar(0.0, LENGTH_UNIT)

    def to_dict(self, annulus_label: AnnulusLabel) -> Dict[str, Any]:
        """Convert data to dict in order to write data to the alfacase."""
        output = {}
        for key, value in asdict(self).items():
            if key == "annulus_depth_table":
                value = self.annulus_depth_table.to_dict(annulus_label)
            elif key == "annulus_temperature_table":
                value = self.annulus_temperature_table.to_dict(annulus_label)
            output[f"{key}_{annulus_label.value}"] = value

        # the annular A doesn't have these parameters in plugin
        if annulus_label == AnnulusLabel.A:
            output.pop("pressure_relief_a")
            output.pop("relief_position_a")
        return output


@dataclass
class Annuli:
    annulus_a: Annulus = field(default_factory=lambda: Annulus())
    annulus_b: Annulus = field(default_factory=lambda: Annulus())
    annulus_c: Annulus = field(default_factory=lambda: Annulus())
    annulus_d: Annulus = field(default_factory=lambda: Annulus())
    annulus_e: Annulus = field(default_factory=lambda: Annulus())

    def to_dict(self) -> Dict[str, Any]:
        """Convert data to dict in order to write data to the alfacase."""
        data = {}
        for annulus_label in AnnulusLabel:
            data.update(getattr(self, f"annulus_{annulus_label.value}").to_dict(annulus_label))
        return data


@dataclass
class Options:
    thermal_property_update_mode: ThermalPropertyUpdateMode
    is_gas_lift_on: bool

    def to_dict(self) -> Dict[str, Any]:
        """Convert data to dict in order to write data to the alfacase."""
        return asdict(self)
