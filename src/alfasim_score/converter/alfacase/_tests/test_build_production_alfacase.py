from alfasim_sdk import convert_description_to_alfacase
from pytest_regressions.file_regression import FileRegressionFixture

from alfasim_score.converter.alfacase.production_operation import ProductionOperationBuilder


def test_create_alfacase_gas_lift_production(
    file_regression: FileRegressionFixture,
    production_operation_gas_lift: ProductionOperationBuilder,
) -> None:
    case_description = production_operation_gas_lift.generate_operation_alfacase_description()
    file_regression.check(
        convert_description_to_alfacase(case_description), encoding="utf-8", extension=".alfacase"
    )


def test_create_alfacase_natural_flow_production(
    file_regression: FileRegressionFixture,
    production_operation_natural_flow: ProductionOperationBuilder,
) -> None:
    case_description = production_operation_natural_flow.generate_operation_alfacase_description()
    file_regression.check(
        convert_description_to_alfacase(case_description), encoding="utf-8", extension=".alfacase"
    )
