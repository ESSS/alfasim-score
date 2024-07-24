from typing import Union

from alfasim_sdk import convert_description_to_alfacase
from pytest_regressions.file_regression import FileRegressionFixture

from alfasim_score.converter.alfacase.base_operation import BaseOperationBuilder
from alfasim_score.converter.alfacase.convert_alfacase import ScoreAlfacaseConverter
from alfasim_score.converter.alfacase.score_input_reader import ScoreInputReader


def build_alfacase_regression_file(
    file_regression: FileRegressionFixture,
    alfacase: ScoreAlfacaseConverter,
) -> None:
    case_description = alfacase.build_case_description()
    file_regression.check(
        convert_description_to_alfacase(case_description), encoding="utf-8", extension=".alfacase"
    )


def test_create_alfacase_gas_lift(
    file_regression: FileRegressionFixture,
    alfacase_gas_lift: ScoreAlfacaseConverter,
) -> None:
    build_alfacase_regression_file(file_regression, alfacase_gas_lift)


def test_create_alfacase_natural_flow(
    file_regression: FileRegressionFixture,
    alfacase_natural_flow: ScoreAlfacaseConverter,
) -> None:
    build_alfacase_regression_file(file_regression, alfacase_natural_flow)


def test_create_alfacase_gas_lift_with_operation(
    file_regression: FileRegressionFixture,
    operation_gas_lift: BaseOperationBuilder,
) -> None:
    build_alfacase_regression_file(file_regression, operation_gas_lift)


def test_create_alfacase_natural_flow_with_operation(
    file_regression: FileRegressionFixture,
    operation_natural_flow: BaseOperationBuilder,
) -> None:
    build_alfacase_regression_file(file_regression, operation_natural_flow)
