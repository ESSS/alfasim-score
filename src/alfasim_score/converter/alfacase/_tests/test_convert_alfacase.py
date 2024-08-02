import pytest
from alfasim_sdk import convert_description_to_alfacase
from pathlib import Path
from pytest_regressions.file_regression import FileRegressionFixture

from alfasim_score.converter.alfacase.converter_main import convert_score_to_alfacase


@pytest.mark.parametrize(
    "score_filename", ["score_input_natural_flow", "score_input_injection_operation"]
)
def test_create_alfacase_file(
    shared_datadir: Path, datadir: Path, file_regression: FileRegressionFixture, score_filename: str
) -> None:
    score_input = shared_datadir / f"{score_filename}.json"
    alfacase_output = datadir / f"{score_filename}.alfacase"
    convert_score_to_alfacase(score_input, alfacase_output)
    file_regression.check(
        alfacase_output.read_text(encoding="utf-8"), encoding="utf-8", extension=".alfacase"
    )
