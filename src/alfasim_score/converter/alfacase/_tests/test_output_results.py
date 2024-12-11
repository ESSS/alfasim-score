from pathlib import Path
from pytest_regressions.file_regression import FileRegressionFixture

from alfasim_score.common import AnnulusLabel
from alfasim_score.converter.alfacase.alfasim_score_converter import AlfasimScoreConverter


def test_generate_output_file_results(
    shared_datadir: Path, datadir: Path, file_regression: FileRegressionFixture
) -> None:
    alfasim_results_directory = shared_datadir / "case.data"
    # dummy input file just to have the reader for this test
    score_input_filepath = shared_datadir / "score_input_natural_flow.json"
    output_filepath = datadir / "output_score.json"
    converter = AlfasimScoreConverter(score_input_filepath, output_filepath)
    # change the element name to match this test result well name
    converter.output_builder.element_name = "7-SRR-2-RJS (2022-07-28_15-01-27)"
    # TODO: remember to get these annuli inside the output class
    converter.output_builder.active_annuli = [AnnulusLabel.A, AnnulusLabel.B, AnnulusLabel.C]
    converter.generate_score_output_file(alfasim_results_directory)
    output_content = converter.output_builder.score_output_filepath.read_text(encoding="utf-8")
    file_regression.check(output_content, extension=".json", encoding="utf-8")
