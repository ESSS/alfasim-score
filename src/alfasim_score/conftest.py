from typing import Any
from typing import Union

import pytest
from alfasim_sdk import PluginDescription
from barril.units import Array
from barril.units import Scalar
from enum import Enum
from pathlib import Path

from alfasim_score.converter.alfacase.base_operation import BaseOperationBuilder
from alfasim_score.converter.alfacase.convert_alfacase import ScoreAlfacaseConverter
from alfasim_score.converter.alfacase.injection_operation import InjectionOperationBuilder
from alfasim_score.converter.alfacase.production_operation import ProductionOperationBuilder
from alfasim_score.converter.alfacase.score_input_reader import ScoreInputReader
from alfasim_score.converter.plugin_data import Annuli
from alfasim_score.converter.plugin_data import Annulus
from alfasim_score.converter.plugin_data import AnnulusModeType
from alfasim_score.converter.plugin_data import AnnulusTable
from alfasim_score.converter.plugin_data import FluidModelPvt
from alfasim_score.converter.plugin_data import FluidModelZamora
from alfasim_score.converter.plugin_data import Material

SCORE_GAS_LIFT_EXAMPLE_FILENAME = "score_input_gas_lift.json"
SCORE_NATURAL_FLOW_EXAMPLE_FILENAME = "score_input_natural_flow.json"
SCORE_INJECTION_EXAMPLE_FILENAME = "score_input_injection_operation.json"


@pytest.fixture
def score_input_gas_lift(shared_datadir: Path) -> ScoreInputReader:
    return ScoreInputReader(shared_datadir / SCORE_GAS_LIFT_EXAMPLE_FILENAME)


@pytest.fixture
def alfacase_gas_lift(score_input_gas_lift: ScoreInputReader) -> ScoreAlfacaseConverter:
    return ScoreAlfacaseConverter(score_input_gas_lift)


@pytest.fixture
def base_operation_gas_lift(shared_datadir: Path) -> BaseOperationBuilder:
    return BaseOperationBuilder(shared_datadir / SCORE_GAS_LIFT_EXAMPLE_FILENAME)


@pytest.fixture
def production_operation_gas_lift(shared_datadir: Path) -> ProductionOperationBuilder:
    return ProductionOperationBuilder(shared_datadir / SCORE_GAS_LIFT_EXAMPLE_FILENAME)


@pytest.fixture
def production_operation_natural_flow(shared_datadir: Path) -> ProductionOperationBuilder:
    return ProductionOperationBuilder(shared_datadir / SCORE_NATURAL_FLOW_EXAMPLE_FILENAME)


@pytest.fixture
def injection_operation(shared_datadir: Path) -> InjectionOperationBuilder:
    return InjectionOperationBuilder(shared_datadir / SCORE_INJECTION_EXAMPLE_FILENAME)


class ModeType(Enum):
    UNDISTURBED = "Undisturbed"
    DRILLING = "Drilling"


class FluidType(Enum):
    PVT = "PVT"
    ZAMORA = "Zamora"


@pytest.fixture
def annulus_data() -> Annuli:
    return Annuli(
        annulus_A=Annulus(
            is_active=True,
            mode_type=AnnulusModeType.UNDISTURBED,
            initial_top_pressure=Scalar(2121.0, "Pa"),
            is_open_seabed=False,
            annulus_table=AnnulusTable(
                initial_depth=Array([212.0, 321.0], "m"),
                final_depth=Array([2121.0, 2121.0], "m"),
                fluid_id=Array([1.0, 2.0], "-"),
            ),
            has_fluid_return=False,
            initial_leakoff=Scalar(121.0, "m3"),
            relief_pressure=True,
        ),
        annulus_B=Annulus(
            is_active=True,
            mode_type=AnnulusModeType.UNDISTURBED,
            initial_top_pressure=Scalar(121.0, "Pa"),
            is_open_seabed=False,
            annulus_table=AnnulusTable(
                initial_depth=Array([1.0], "m"),
                final_depth=Array([2.0], "m"),
                fluid_id=Array([2.0], "-"),
            ),
            has_fluid_return=False,
            initial_leakoff=Scalar(121.0, "m3"),
            has_relief_pressure=True,
            relief_pressure=Scalar(22.0, "Pa"),
            relief_position=Scalar(121.0, "m"),
        ),
        annulus_C=Annulus(
            is_active=True,
            mode_type=AnnulusModeType.DRILLING,
            initial_top_pressure=Scalar(1562.0, "Pa"),
            is_open_seabed=True,
            annulus_table=AnnulusTable(
                initial_depth=Array([15151.0], "m"),
                final_depth=Array([16526262.0], "m"),
                fluid_id=Array([1.0], "-"),
            ),
            has_fluid_return=True,
            initial_leakoff=Scalar(26262.0, "m3"),
            has_relief_pressure=True,
            relief_pressure=Scalar(262.0, "Pa"),
            relief_position=Scalar(4189.0, "m"),
        ),
        annulus_D=Annulus(
            is_active=True,
            mode_type=AnnulusModeType.UNDISTURBED,
            initial_top_pressure=Scalar(0.0, "bar"),
            is_open_seabed=False,
            annulus_table=AnnulusTable(),
            has_fluid_return=False,
            initial_leakoff=Scalar(0.0, "m3"),
            has_relief_pressure=False,
            relief_pressure=Scalar(0.0, "kgf/cm2"),
            relief_position=Scalar(0.0, "m"),
        ),
        annulus_E=Annulus(
            is_active=True,
            mode_type=AnnulusModeType.UNDISTURBED,
            initial_top_pressure=Scalar(0.0, "bar"),
            is_open_seabed=False,
            annulus_table=AnnulusTable(),
            has_fluid_return=False,
            initial_leakoff=Scalar(0.0, "m3"),
            has_relief_pressure=False,
            relief_pressure=Scalar(0.0, "kgf/cm2"),
            relief_position=Scalar(0.0, "m"),
        ),
    )


@pytest.fixture
def fluid_data(shared_datadir: Path) -> list[Union[FluidModelZamora, FluidModelPvt]]:
    return [
        FluidModelZamora(
            "D2 Mexico",
            Scalar(7.0465, "kg/m3"),
            Scalar(0.00325, "-"),
            Scalar(2.98e-10, "-"),
            Scalar(-0.00263, "-"),
            Scalar(5.12e-08, "-"),
            Scalar(-5.58e-13, "-"),
        ),
        FluidModelPvt(shared_datadir / "3phase_constant.tab"),
    ]


@pytest.fixture
def material_data() -> list[Material]:
    return [
        Material(
            "Carbon Steel",
            Scalar(140.0, "GPa"),
            Scalar(0.29, "-"),
            Scalar(1.1e-05, "1/K"),
        ),
        Material(
            "Cement",
            Scalar(50.0, "GPa"),
            Scalar(0.2, "-"),
            Scalar(1e-05, "1/K"),
        ),
    ]


@pytest.fixture
def apb_plugin_description(
    annuli_data: Annuli,
    fluids_data: list[Union[FluidModelZamora, FluidModelPvt]],
    materials_data: list[Material],
) -> None:
    annuli = annuli_data.to_dict()
    annuli["name"] = "Annulus Data Model"
    gui_models = {
        "AnnulusDataModel": annuli,
        "FluidContainer": {
            "name": "Annulus Fluids Container",
            "_children_list": [fluid.to_dict() for fluid in fluids_data],
        },
        "MechanicalContainer": {
            "name": "Mechanical Properties",
            "_children_list": [material.to_dict() for material in materials_data],
        },
    }
    return PluginDescription(
        name="apb",
        gui_models=gui_models,
        is_enabled=True,
    )
