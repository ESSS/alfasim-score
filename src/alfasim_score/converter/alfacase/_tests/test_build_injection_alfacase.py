from alfasim_sdk import convert_description_to_alfacase
from pytest_regressions.file_regression import FileRegressionFixture

from alfasim_score.converter.alfacase.injection_operation import InjectionOperationBuilder


def test_create_alfacase_injection(
    file_regression: FileRegressionFixture,
    injection_operation: InjectionOperationBuilder,
) -> None:
    case_description = injection_operation.generate_operation_alfacase_description()
    file_regression.check(
        convert_description_to_alfacase(case_description), encoding="utf-8", extension=".alfacase"
    )
