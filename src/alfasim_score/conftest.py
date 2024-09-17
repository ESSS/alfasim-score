from typing import Any

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


# TODO: these data for fixtures could be inherited from the plugin apb
class ModeType(Enum):
    UNDISTURBED = "Undisturbed"
    DRILLING = "Drilling"


class FluidType(Enum):
    PVT = "PVT"
    ZAMORA = "Zamora"


@pytest.fixture
def annulus_data() -> dict[str, Any]:
    return {
        "active_annulus_A": True,
        "mode_type_A": ModeType.UNDISTURBED.value,
        "initial_top_pressure_A": Scalar(2121.0, "Pa"),
        "opensea_A": False,
        "annulus_table_A": {
            "columns": {
                "initial_depth_A": Array([212.0, 321.0], "m"),
                "final_depth_A": Array([2121.0, 2121.0], "m"),
                "fluid_id_A": Array([1.0, 2.0], "-"),
            }
        },
        "fluid_return_A": False,
        "initial_leakoff_A": Scalar(121.0, "m3"),
        "relief_pressure_A": True,
        "active_annulus_B": True,
        "mode_type_B": ModeType.UNDISTURBED.value,
        "initial_top_pressure_B": Scalar(121.0, "Pa"),
        "opensea_B": False,
        "annulus_table_B": {
            "columns": {
                "initial_depth_B": Array([1.0], "m"),
                "final_depth_B": Array([1.0], "m"),
                "fluid_id_B": Array([2.0], "-"),
            }
        },
        "fluid_return_B": False,
        "initial_leakoff_B": Scalar(121.0, "m3"),
        "relief_pressure_check_B": True,
        "pressure_relief_B": Scalar(22.0, "Pa"),
        "relief_position_B": Scalar(121.0, "m"),
        "active_annulus_C": True,
        "mode_type_C": ModeType.DRILLING,
        "initial_top_pressure_C": Scalar(1562.0, "Pa"),
        "opensea_C": True,
        "annulus_table_C": {
            "columns": {
                "initial_depth_C": Array([15151.0], "m"),
                "final_depth_C": Array([16526262.0], "m"),
                "fluid_id_C": Array([1.0], "-"),
            }
        },
        "fluid_return_C": True,
        "initial_leakoff_C": Scalar(26262.0, "m3"),
        "relief_pressure_check_C": True,
        "pressure_relief_C": Scalar(262.0, "Pa"),
        "relief_position_C": Scalar(4189.0, "m"),
        "active_annulus_D": False,
        "mode_type_D": ModeType.UNDISTURBED.value,
        "initial_top_pressure_D": Scalar(0.0, "bar"),
        "opensea_D": False,
        "fluid_return_D": False,
        "initial_leakoff_D": Scalar(0.0, "m3"),
        "relief_pressure_check_D": False,
        "pressure_relief_D": Scalar(0.0, "kgf/cm2"),
        "relief_position_D": Scalar(0.0, "m"),
        "active_annulus_E": False,
        "mode_type_E": ModeType.UNDISTURBED.value,
        "initial_top_pressure_E": Scalar(0.0, "bar"),
        "opensea_E": False,
        "fluid_return_E": False,
        "initial_leakoff_E": Scalar(0.0, "m3"),
        "relief_pressure_check_E": False,
        "pressure_relief_E": Scalar(0.0, "kgf/cm2"),
        "relief_position_E": Scalar(0.0, "m"),
    }


@pytest.fixture
def fluid_data(shared_datadir: Path) -> list[dict[str, Any]]:
    return [
        {
            "name": "D2 Mexico",
            "fluid_type": FluidType.ZAMORA.value,
            "a1_zamora": Scalar(7.0465, "kg/m3"),
            "a2_zamora": Scalar(0.00325, "-"),
            "b1_zamora": Scalar(2.98e-10, "-"),
            "b2_zamora": Scalar(-0.00263, "-"),
            "c1_zamora": Scalar(5.12e-08, "-"),
            "c2_zamora": Scalar(-5.58e-13, "-"),
        },
        {
            "name": "Mineral Oil",
            "fluid_type": FluidType.PVT.value,
            "a1_zamora": Scalar(0.0, "lbm/galUS"),
            "a2_zamora": Scalar(0.0, "-"),
            "b1_zamora": Scalar(0.0, "-"),
            "b2_zamora": Scalar(0.0, "-"),
            "c1_zamora": Scalar(0.0, "-"),
            "c2_zamora": Scalar(0.0, "-"),
            "pvt_table_content": shared_datadir / "3phase_constant.tab",
        },
    ]


@pytest.fixture
def material_data() -> list[dict[str, Any]]:
    return [
        {
            "name": "Carbon Steel",
            "young_modulus": Scalar(140.0, "GPa"),
            "poisson_ratio": Scalar(0.29, "-"),
            "thermal_expansion_coefficient": Scalar(1.1e-05, "1/K"),
        },
        {
            "name": "Cement",
            "young_modulus": Scalar(50.0, "GPa"),
            "poisson_ratio": Scalar(0.2, "-"),
            "thermal_expansion_coefficient": Scalar(1e-05, "1/K"),
        },
    ]


@pytest.fixture
def apb_plugin_description(
    annulus_data: dict[str, Any],
    fluid_data: list[dict[str, Any]],
    material_data: list[dict[str, Any]],
) -> PluginDescription:
    gui_models = {
        "AnnulusDataModel": {"name": "Annulus Data Model", **annulus_data},
        "FluidContainer": {
            "name": "Annulus Fluids Container",
            "_children_list": fluid_data,
        },
        "MechanicalContainer": {
            "name": "Mechanical Properties",
            "_children_list": material_data,
        },
    }

    return PluginDescription(
        name="apb",
        gui_models=gui_models,
        is_enabled=True,
    )
