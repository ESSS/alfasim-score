from pathlib import Path
from pytest_mock import MockerFixture
from pytest_regressions.file_regression import FileRegressionFixture

from alfasim_score.common import AnnulusLabel
from alfasim_score.converter.alfacase.alfasim_score_converter import AlfasimScoreConverter


def test_generate_output_file_results(
    shared_datadir: Path,
    datadir: Path,
    file_regression: FileRegressionFixture,
    mocker: MockerFixture,
) -> None:
    alfasim_results_path = shared_datadir / "case.data"
    # dummy input file just to have the reader for this test
    score_input_file = shared_datadir / "score_input_natural_flow.json"
    output_file = datadir / "output_score.json"
    converter = AlfasimScoreConverter(score_input_file, output_file)
    mocker.patch.object(
        converter.score_data,
        "get_annuli_list",
        return_value=[AnnulusLabel.A, AnnulusLabel.B, AnnulusLabel.C],
    )
    # change the element name to match this test result well name
    converter.output_builder.element_name = "7-SRR-2-RJS (2022-07-28_15-01-27)"
    converter.generate_score_output_file(alfasim_results_path)
    output_content = converter.output_builder.score_output_filepath.read_text(encoding="utf-8")
    file_regression.check(output_content, extension=".json", encoding="utf-8")
