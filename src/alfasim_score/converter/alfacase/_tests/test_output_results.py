import pytest
from pathlib import Path
from pytest_mock import MockerFixture
from pytest_regressions.file_regression import FileRegressionFixture

from alfasim_score.common import AnnulusLabel
from alfasim_score.converter.alfacase.alfasim_score_converter import AlfasimScoreConverter


@pytest.mark.parametrize(
    "case_filename, input_filename, element_name",
    [
        pytest.param(
            "case.data",
            "score_input_natural_flow.json",
            "7-SRR-2-RJS (2022-07-28_15-01-27)",
            id="natural_flow",
        ),
        pytest.param(
            "case2.data", "score_input_B_relief_C_open.json", "WELLBORE", id="B_relief_C_open"
        ),
    ],
)
def test_generate_output_file_results(
    shared_datadir: Path,
    datadir: Path,
    file_regression: FileRegressionFixture,
    mocker: MockerFixture,
    case_filename: str,
    input_filename: str,
    element_name: str,
) -> None:
    alfasim_results_path = shared_datadir / case_filename
    score_input_file = shared_datadir / input_filename
    output_file = datadir / "output_score.json"
    converter = AlfasimScoreConverter(score_input_file, output_file)

    mocker.patch.object(
        converter.score_data,
        "get_annuli_list",
        return_value=[AnnulusLabel.A, AnnulusLabel.B, AnnulusLabel.C],
    )

    converter.output_builder.element_name = element_name
    converter.generate_score_output_file(alfasim_results_path)
    output_content = converter.output_builder.score_output_filepath.read_text(encoding="utf-8")
    file_regression.check(output_content, extension=".json", encoding="utf-8")
