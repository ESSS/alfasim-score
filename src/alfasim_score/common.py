from typing import Any
from typing import Dict

import numpy as np
from barril.curve.curve import Curve
from barril.units import Array
from barril.units import Scalar
from enum import Enum

from alfasim_score.units import DENSITY_UNIT
from alfasim_score.units import FRACTION_UNIT
from alfasim_score.units import LENGTH_UNIT


class WellItemType(str, Enum):
    DRILLING = "DRILLING"
    CASING = "CASING"
    NONE = "NONE"


class WellItemFunction(str, Enum):
    CONDUCTOR = "CONDUCTOR"
    SURFACE = "SURFACE"
    PRODUCTION = "PRODUCTION"
    OPEN = "OPEN"


# TODO PWPA-1983: need more examples of SCORE files to know the label for method
#       the method is in the file tree in the path operation/data/method
class LiftMethod(str, Enum):
    # NATURAL_FLOW = "???"
    # BCS_PUMP = "???"
    GAS_LIFT = "GASLIFT"


# TODO: need more examples of SCORE files to know the label for other models
#       the model is in the file tree in the path operation/thermal_data/fluid_type
class ModelFluidType(str, Enum):
    BLACK_OIL = "BLACK_OIL"


def prepare_for_regression(values: Dict[str, Any]) -> Dict[str, Any]:
    """ "Prepare Scalar and Array to the be used in regression test"""
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
    """Convert quota value to TVD given the air_gap"""
    tvd = np.abs(quota.GetValue(LENGTH_UNIT)) + air_gap.GetValue(LENGTH_UNIT)
    return Scalar(tvd, LENGTH_UNIT)


def convert_api_to_oil_density(api_gravity: Scalar) -> Scalar:
    """Calculate the oil standard condition density based on API density"""
    return Scalar(141.5 / (api_gravity.GetValue(FRACTION_UNIT) + 131.5), DENSITY_UNIT)


def convert_gas_gravity_to_gas_density(gas_gravity: Scalar) -> Scalar:
    # TODO: check this calculation it's using dirrect value of air density at std
    return gas_gravity * 1.225
