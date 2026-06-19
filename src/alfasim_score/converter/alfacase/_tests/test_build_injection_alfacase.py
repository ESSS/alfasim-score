from alfasim_sdk._internal.alfacase.alfacase import _convert_description_to_yaml
from pytest_regressions.file_regression import FileRegressionFixture

from alfasim_score.converter.alfacase.injection_operation import InjectionOperationBuilder


def test_create_alfacase_injection(
    file_regression: FileRegressionFixture,
    injection_operation: InjectionOperationBuilder,
) -> None:
    case_description = injection_operation.generate_operation_alfacase_description()
    file_regression.check(
        _convert_description_to_yaml(case_description), encoding="utf-8", extension=".alfacase"
    )
