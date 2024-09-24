from typing import Any
from typing import Dict
from typing import List
from typing import Union

import numpy as np
from barril.curve.curve import Curve
from barril.units import Array
from barril.units import Scalar
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from pathlib import Path

from alfasim_score.constants import AIR_DENSITY_STANDARD
from alfasim_score.constants import WATER_DENSITY_STANDARD
from alfasim_score.units import DENSITY_UNIT
from alfasim_score.units import FRACTION_UNIT
from alfasim_score.units import LENGTH_UNIT
from alfasim_score.units import PRESSURE_UNIT
from alfasim_score.units import VOLUME_UNIT


class WellItemType(str, Enum):
    DRILLING = "DRILLING"
    CASING = "CASING"
    JETTING = "JETTING"
    NONE = "NONE"


class WellItemFunction(str, Enum):
    CONDUCTOR = "CONDUCTOR"
    SURFACE = "SURFACE"
    INTERMEDIATE = "INTERMEDIATE"
    PRODUCTION = "PRODUCTION"
    OPEN = "OPEN"


# NOTE: The lift method with pump is not used in the alfasim_score
#       because the pump is supposed to be out of the well on the sea bed.
class LiftMethod(str, Enum):
    NATURAL_FLOW = "NATURALFLOW"
    GAS_LIFT = "GASLIFT"


# TODO 1992: need more examples of SCORE files to know the label for other models
#       the model is in the file tree in the path operation/thermal_data/fluid_type
class ModelFluidType(str, Enum):
    BLACK_OIL = "BLACK_OIL"
    WATER = "Water"


class FluidType(str, Enum):
    OIL = "OIL"
    WATER = "WATER"
    GAS = "GAS"


class OperationType(str, Enum):
    PRODUCTION = "PRODUCTION"
    INJECTION = "INJECTION"

    @classmethod
    def _missing_(cls, value):  # type: ignore
        available = ", ".join([repr(m.value) for m in cls])
        raise ValueError(f"{value} is not a valid {cls.__name__}. Valid types: {available}")


class FluidModelType(str, Enum):
    PVT = "PVT"
    ZAMORA = "Zamora"


class AnnulusModeType(str, Enum):
    UNDISTURBED = "Undisturbed"
    DRILLING = "Drilling"


@dataclass
class FluidModelPvt:
    name: str

    def to_dict(self) -> Dict[str, Union[str, Scalar]]:
        """Convert data to dict in order to write data to the alfacase."""
        return {
            "name": self.name,
            "fluid_type": FluidModelType.PVT.value,
        }


@dataclass
class FluidModelZamora:
    name: str
    a_1: Scalar
    a_2: Scalar
    b_1: Scalar
    b_2: Scalar
    c_1: Scalar
    c_2: Scalar

    def to_dict(self) -> Dict[str, Union[str, Scalar]]:
        """Convert data to dict in order to write data to the alfacase."""
        return {
            "name": self.name,
            "fluid_type": FluidModelType.ZAMORA.value,
            "a1_zamora": self.a_1,
            "a2_zamora": self.a_2,
            "b1_zamora": self.b_1,
            "b2_zamora": self.b_2,
            "c1_zamora": self.c_1,
            "c2_zamora": self.c_2,
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
class AnnulusTable:
    fluid_names: List[str] = field(default_factory=lambda: [])
    fluid_ids: List[float] = field(default_factory=lambda: [])
    initial_depths: Array = Array([], LENGTH_UNIT)
    final_depths: Array = Array([], LENGTH_UNIT)

    def to_dict(self, annulus_type: str) -> Dict[str, Any]:
        """Convert data to dict in order to write data to the alfacase."""
        columns = {
            f"fluid_id_{annulus_type}": self.fluid_ids,
            f"initial_depth_{annulus_type}": self.initial_depths,
            f"final_depth_{annulus_type}": self.final_depths,
        }
        return {"columns": columns}


@dataclass
class Annulus:
    is_active: bool = False
    mode_type: AnnulusModeType = AnnulusModeType.UNDISTURBED
    initial_top_pressure: Scalar = Scalar(0.0, PRESSURE_UNIT)
    is_open_seabed: bool = False
    annulus_table: AnnulusTable = AnnulusTable()
    has_fluid_return: bool = False
    initial_leakoff: Scalar = Scalar(0.0, VOLUME_UNIT)
    has_relief_pressure: bool = False
    relief_pressure: Scalar = Scalar(0.0, PRESSURE_UNIT)
    relief_position: Scalar = Scalar(0.0, LENGTH_UNIT)

    def to_dict(self, annulus_type: str) -> Dict[str, Any]:
        """Convert data to dict in order to write data to the alfacase."""
        # TODO PWPA-2152: make sure all names match (plugin and converter) than remove this mapped names
        plugin_key_names = {
            "is_active": "is_active",
            "mode_type": "mode_type",
            "initial_top_pressure": "initial_top_pressure",
            "is_open_seabed": "open_sea",
            "annulus_table": "annulus_table",
            "has_fluid_return": "fluid_return",
            "initial_leakoff": "initial_leakoff",
            "has_relief_pressure": "relief_pressure_check",
            "relief_pressure": "pressure_relief",
            "relief_position": "relief_position",
        }
        output = {
            f"{plugin_key_names[key]}_{annulus_type}": (
                self.annulus_table.to_dict(annulus_type) if key == "annulus_table" else value
            )
            for key, value in asdict(self).items()
        }
        # the annular A doesn't have these parameters in plugin
        if annulus_type == "A":
            output.pop("pressure_relief_A")
            output.pop("relief_position_A")
        return output


@dataclass
class Annuli:
    annulus_A: Annulus = Annulus()
    annulus_B: Annulus = Annulus()
    annulus_C: Annulus = Annulus()
    annulus_D: Annulus = Annulus()
    annulus_E: Annulus = Annulus()

    def to_dict(self) -> Dict[str, Any]:
        """Convert data to dict in order to write data to the alfacase."""
        data = {}
        for annulus_type in "ABCDE":
            data.update(getattr(self, f"annulus_{annulus_type}").to_dict(annulus_type))
        return data


def prepare_for_regression(values: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare Scalar and Array to the be used in regression test."""
    regression_values = {}
    for key, value in values.items():
        if isinstance(value, Scalar):
            regression_values[key] = {
                "value": value.value,
                "unit": value.unit,
            }
        elif isinstance(value, Array):
            regression_values[key] = {
                "values": value.values,
                "unit": value.unit,
            }
        elif isinstance(value, Curve):
            regression_values[key] = {
                "image_values": value.image.values,
                "image_unit": value.image.unit,
                "domain_values": value.domain.values,
                "domain_unit": value.domain.unit,
            }
        elif isinstance(value, Enum):
            regression_values[key] = value.value
        else:
            regression_values[key] = value

    return regression_values


def convert_quota_to_tvd(quota: Scalar, air_gap: Scalar) -> Scalar:
    """Convert quota value to TVD given the air gap."""
    tvd = np.abs(quota.GetValue(LENGTH_UNIT)) + air_gap.GetValue(LENGTH_UNIT)
    return Scalar(tvd, LENGTH_UNIT)


def convert_api_gravity_to_oil_density(api_gravity: Scalar) -> Scalar:
    """Calculate the oil standard condition density based on API density."""
    specific_gravity = 141.5 / (api_gravity.GetValue(FRACTION_UNIT) + 131.5)
    return WATER_DENSITY_STANDARD * specific_gravity


def convert_gas_gravity_to_gas_density(gas_gravity: Scalar) -> Scalar:
    """Calculate the gas density based on gas gravity value."""
    return Scalar(
        AIR_DENSITY_STANDARD.GetValue(DENSITY_UNIT) * gas_gravity.GetValue(), DENSITY_UNIT
    )


def filter_duplicated_materials_by_name(
    material_list: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Remove the duplicated materials parsed by the reader."""
    filtered = {material["name"]: material for material in material_list}
    return list(filtered.values())
