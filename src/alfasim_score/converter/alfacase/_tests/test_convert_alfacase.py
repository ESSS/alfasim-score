from alfasim_sdk import convert_description_to_alfacase
from pytest_regressions.file_regression import FileRegressionFixture

from alfasim_score.converter.alfacase.base_operation import BaseOperationBuilder
from alfasim_score.converter.alfacase.convert_alfacase import ScoreAlfacaseConverter
from alfasim_score.converter.alfacase.score_input_reader import ScoreInputReader


def test_create_alfacase(
    file_regression: FileRegressionFixture,
    score_input_example: ScoreInputReader,
) -> None:
    builder = ScoreAlfacaseConverter(score_input_example)
    case_description = builder.build_case_description()
    file_regression.check(
        convert_description_to_alfacase(case_description), encoding="utf-8", extension=".alfacase"
    )


def test_create_alfacase_with_operation(
    file_regression: FileRegressionFixture,
    score_input_example: ScoreInputReader,
) -> None:
    builder = BaseOperationBuilder(score_input_example)
    case_description = builder.build_case_description()
    file_regression.check(
        convert_description_to_alfacase(case_description), encoding="utf-8", extension=".alfacase"
    )
