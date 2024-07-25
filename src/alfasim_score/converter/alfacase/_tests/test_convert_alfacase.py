from typing import Union

from alfasim_sdk import convert_description_to_alfacase
from pytest_regressions.file_regression import FileRegressionFixture

from alfasim_score.converter.alfacase.base_operation import BaseOperationBuilder
from alfasim_score.converter.alfacase.convert_alfacase import ScoreAlfacaseConverter
from alfasim_score.converter.alfacase.production_operation import ProductionOperationBuilder


def test_create_alfacase_gas_lift(
    file_regression: FileRegressionFixture,
    alfacase_gas_lift: ScoreAlfacaseConverter,
) -> None:
    case_description = alfacase_gas_lift.build_base_alfacase_description()
    file_regression.check(
        convert_description_to_alfacase(case_description), encoding="utf-8", extension=".alfacase"
    )


def test_create_alfacase_natural_flow(
    file_regression: FileRegressionFixture,
    alfacase_natural_flow: ScoreAlfacaseConverter,
) -> None:
    case_description = alfacase_natural_flow.build_base_alfacase_description()
    file_regression.check(
        convert_description_to_alfacase(case_description), encoding="utf-8", extension=".alfacase"
    )


def test_create_alfacase_gas_lift_with_operation(
    file_regression: FileRegressionFixture,
    production_operation_gas_lift: ProductionOperationBuilder,
) -> None:
    case_description = production_operation_gas_lift.generate_operation_alfacase_description()
    file_regression.check(
        convert_description_to_alfacase(case_description), encoding="utf-8", extension=".alfacase"
    )


def test_create_alfacase_natural_flow_with_operation(
    file_regression: FileRegressionFixture,
    production_operation_natural_flow: ProductionOperationBuilder,
) -> None:
    case_description = production_operation_natural_flow.generate_operation_alfacase_description()
    file_regression.check(
        convert_description_to_alfacase(case_description), encoding="utf-8", extension=".alfacase"
    )
