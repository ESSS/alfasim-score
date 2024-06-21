from typing import Any
from typing import Dict

from barril.units import Array
from barril.units import Scalar
from enum import Enum


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
        elif isinstance(value, Enum):
            regression_values[key] = value.value
        else:
            regression_values[key] = value

    return regression_values
