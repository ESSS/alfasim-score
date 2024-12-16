import pytest
from pathlib import Path
from pytest_regressions.file_regression import FileRegressionFixture

from alfasim_score.converter.alfacase.alfasim_score_converter import AlfasimScoreConverter


@pytest.mark.parametrize(
    "score_filename", ["score_input_natural_flow", "score_input_injection_operation"]
)
def test_create_alfacase_file(
    shared_datadir: Path, datadir: Path, file_regression: FileRegressionFixture, score_filename: str
) -> None:
    score_input = shared_datadir / f"{score_filename}.json"
    converted_alfacase_filepath = datadir / f"{score_filename}.alfacase"
    converter = AlfasimScoreConverter(score_input, Path("score_output/dummy.json"))
    converter.generate_alfasim_input_file(converted_alfacase_filepath)
    file_regression.check(
        converted_alfacase_filepath.read_text(encoding="utf-8"),
        encoding="utf-8",
        extension=".alfacase",
    )
