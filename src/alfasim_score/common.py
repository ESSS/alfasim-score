from typing import Any
from typing import Dict

from barril.curve.curve import Curve
from barril.units import Array
from barril.units import Scalar
from enum import Enum


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
