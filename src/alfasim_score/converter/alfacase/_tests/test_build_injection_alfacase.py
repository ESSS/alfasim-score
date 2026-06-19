from alfasim_sdk import generate_alfacase_file
from pathlib import Path
from pytest_regressions.file_regression import FileRegressionFixture

from alfasim_score.converter.alfacase.injection_operation import InjectionOperationBuilder


def test_create_alfacase_injection(
    file_regression: FileRegressionFixture,
    tmp_path: Path,
    injection_operation: InjectionOperationBuilder,
) -> None:
    case_description = injection_operation.generate_operation_alfacase_description()
    alfacase_file = tmp_path / "case.alfacase"
    generate_alfacase_file(case_description, alfacase_file)
    file_regression.check(
        alfacase_file.read_text(encoding="utf-8"), encoding="utf-8", extension=".alfacase"
    )
