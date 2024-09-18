from typing import Any
from typing import Dict
from typing import Union

from barril.units import Array
from barril.units import Scalar
from dataclasses import asdict
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class FluidModelType(str, Enum):
    PVT = "PVT"
    ZAMORA = "Zamora"


class AnnulusModeType(str, Enum):
    UNDISTURBED = "Undisturbed"
    DRILLING = "Drilling"


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
            "a1_zamora": self.a_1,
            "a2_zamora": self.a_2,
            "b1_zamora": self.b_1,
            "b2_zamora": self.b_2,
            "c1_zamora": self.c_1,
            "c2_zamora": self.c_2,
        }


@dataclass
class FluidModelPvt:
    name: str
    file_path: Path

    def to_dict(self) -> Dict[str, Union[str, Path]]:
        """Convert data to dict in order to write data to the alfacase."""
        return {
            "name": self.name,
            "pvt_table_content": self.file_path,
        }


@dataclass
class Material:
    name: str
    young_modulus: Scalar
    poisson_ratio: Scalar
    thermal_expansion_coefficient: Scalar

    def to_dict(self) -> Dict[str, Any]:
        """Convert data to dict in order to write data to the alfacase."""
        return asdict(self)


@dataclass
class Annuli:
    name: str
    annulus_A: Annulus
    annulus_B: Annulus = Annulus()
    annulus_C: Annulus = Annulus()
    annulus_D: Annulus = Annulus()
    annulus_E: Annulus = Annulus()

    def to_dict(self) -> Dict[str, Any]:
        """Convert data to dict in order to write data to the alfacase."""
        data = {"name": self.name}
        for annulus_type in "ABCDE":
            data.update(getattr(self, f"annulus_{annulus_type}").to_dict())
        return data


@dataclass
class Annulus:
    is_active: bool = False
    mode_type: AnnulusModeType = AnnulusModeType.UNDISTURBED
    initial_top_pressure: Scalar = Scalar(0.0, "Pa")
    is_opensea: bool = False
    annulus_table: AnnulusTable = AnnulusTable()
    has_fluid_return: bool = False
    initial_leakoff: Scalar = Scalar(0.0, "m3")
    has_relief_pressure: bool = False
    # None for the annulus A
    relief_pressure: Union[None, Scalar] = None
    relief_position: Union[None, Scalar] = None

    def to_dict(self, annulus_type: str) -> Dict[str, Any]:
        """Convert data to dict in order to write data to the alfacase."""
        plugin_key_names = {
            "is_active": "active_annulus",
            "mode_type": "mode_type",
            "initial_top_pressure": "initial_top_pressure",
            "is_opensea": "opensea",
            "has_fluid_return": "fluid_return",
            "initial_leakoff": "initial_leakoff",
            "has_relief_pressure": "relief_pressure_check",
            "relief_pressure": "pressure_relief",
            "relief_position": "relief_position",
        }
        return {
            f"{plugin_key_names[key]}_{annulus_type}": (
                value.to_dict(annulus_type) if isinstance(value, AnnulusTable) else value
            )
            for key, value in asdict(self).items()
        }


@dataclass
class AnnulusTable:
    fluid_id: list[int] = []
    initial_depth: Array = Array([], "m")
    final_depth: Array = Array([], "m")

    def to_dict(self, annulus_type: str) -> Dict[str, Any]:
        """Convert data to dict in order to write data to the alfacase."""
        return {"columns": {f"{key}_{annulus_type}": value for key, value in asdict(self).items()}}
