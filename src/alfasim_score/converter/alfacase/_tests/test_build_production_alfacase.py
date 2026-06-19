from alfasim_sdk import generate_alfacase_file
from pathlib import Path
from pytest_regressions.file_regression import FileRegressionFixture

from alfasim_score.converter.alfacase.production_operation import ProductionOperationBuilder


def test_create_alfacase_gas_lift_production(
    file_regression: FileRegressionFixture,
    tmp_path: Path,
    production_operation_gas_lift: ProductionOperationBuilder,
) -> None:
    case_description = production_operation_gas_lift.generate_operation_alfacase_description()
    alfacase_file = tmp_path / "case.alfacase"
    generate_alfacase_file(case_description, alfacase_file)
    file_regression.check(
        alfacase_file.read_text(encoding="utf-8"), encoding="utf-8", extension=".alfacase"
    )


def test_create_alfacase_natural_flow_production(
    file_regression: FileRegressionFixture,
    tmp_path: Path,
    production_operation_natural_flow: ProductionOperationBuilder,
) -> None:
    case_description = production_operation_natural_flow.generate_operation_alfacase_description()
    alfacase_file = tmp_path / "case.alfacase"
    generate_alfacase_file(case_description, alfacase_file)
    file_regression.check(
        alfacase_file.read_text(encoding="utf-8"), encoding="utf-8", extension=".alfacase"
    )


def test_create_alfacase_steady_state_production(
    file_regression: FileRegressionFixture,
    tmp_path: Path,
    production_operation_steady_state: ProductionOperationBuilder,
) -> None:
    case_description = production_operation_steady_state.generate_operation_alfacase_description()
    alfacase_file = tmp_path / "case.alfacase"
    generate_alfacase_file(case_description, alfacase_file)
    file_regression.check(
        alfacase_file.read_text(encoding="utf-8"), encoding="utf-8", extension=".alfacase"
    )


def test_create_alfacase_pseudo_transient_production(
    file_regression: FileRegressionFixture,
    tmp_path: Path,
    production_operation_pseudo_transient: ProductionOperationBuilder,
) -> None:
    case_description = (
        production_operation_pseudo_transient.generate_operation_alfacase_description()
    )
    alfacase_file = tmp_path / "case.alfacase"
    generate_alfacase_file(case_description, alfacase_file)
    file_regression.check(
        alfacase_file.read_text(encoding="utf-8"), encoding="utf-8", extension=".alfacase"
    )
