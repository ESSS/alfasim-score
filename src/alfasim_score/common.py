from typing import Any
from typing import Dict

import numpy as np
from barril.curve.curve import Curve
from barril.units import Array
from barril.units import Scalar
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from alfasim_score.constants import AIR_DENSITY_STANDARD
from alfasim_score.constants import WATER_DENSITY_STANDARD
from alfasim_score.units import DENSITY_UNIT
from alfasim_score.units import FRACTION_UNIT
from alfasim_score.units import LENGTH_UNIT


class WellItemType(str, Enum):
    DRILLING = "DRILLING"
    CASING = "CASING"
    JETTING = "JETTING"
    NONE = "NONE"


class WellItemFunction(str, Enum):
    CONDUCTOR = "CONDUCTOR"
    SURFACE = "SURFACE"
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


# TODO: maybe this should go in the plugin
class FluidModelType(str, Enum):
    PVT = "PVT"
    ZAMORA = "ZAMORA"


@dataclass
class FluidModelZamora:
    name: str
    a_1: Scalar
    a_2: Scalar
    b_1: Scalar
    b_2: Scalar
    c_1: Scalar
    c_2: Scalar

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "a1_zamora": self.a_1,
            "a2_zamora": self.a_2,
            "b1_zamora": self.b_1,
            "b2_zamora": self.b_2,
            "c1_zamora": self.c_1,
            "c2_zamora": self.c_2,
            "pvt_table_content": Path(""),
        }


# TODO: maybe this should go in the plugin
@dataclass
class FluidModelPvt:
    name: str
    file_path: Path

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "a1_zamora": Scalar(0.0, "lbm/galUS"),
            "a2_zamora": Scalar(0.0, "-"),
            "b1_zamora": Scalar(0.0, "-"),
            "b2_zamora": Scalar(0.0, "-"),
            "c1_zamora": Scalar(0.0, "-"),
            "c2_zamora": Scalar(0.0, "-"),
            "pvt_table_content": self.file_path,
        }
