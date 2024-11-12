import json
import pandas as pd
import pytest
from barril.units import Scalar
from pathlib import Path
from pytest_regressions.file_regression import FileRegressionFixture

from alfasim_score.common import AnnulusLabel
from alfasim_score.converter.alfacase.score_output_generator import ScoreOutputGenerator


def test_generate_output_file_results(
    shared_datadir: Path, datadir: Path, file_regression: FileRegressionFixture
) -> None:
    alfasim_results_directory = shared_datadir / "case.data"
    well_start_position = Scalar(2072, "m")
    active_annuli = [AnnulusLabel.A, AnnulusLabel.B, AnnulusLabel.C]
    #It was defined to use 6 wall layers as output from Alfasim
    layers = list(range(6))
    output_generator = ScoreOutputGenerator(
        alfasim_results_directory, well_start_position, active_annuli, layers
    )
    output_generator.element_name = "7-SRR-2-RJS (2022-07-28_15-01-27)"
    output_filepath = datadir / "output_score.json"
    output_generator.generate_output_file(datadir / "output_score.json")
    output_content = output_filepath.read_text(encoding="utf-8")
    file_regression.check(output_content, extension=".json", encoding="utf-8")
