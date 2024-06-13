from typing import Any

import json
import pytest
from pathlib import Path
from pytest_regressions.num_regression import NumericRegressionFixture

from alfasim_score.converter.alfacase.convert_alfacase import AlfacaseConverter
from alfasim_score.converter.alfacase.score_input_reader import ScoreInputReader


@pytest.fixture
def score_input_example(shared_datadir: Path) -> ScoreInputReader:
    return ScoreInputReader(shared_datadir / "score_input_example.json")


def test_convert_well_trajectory(
    num_regression: NumericRegressionFixture,
    score_input_example: ScoreInputReader,
) -> None:
    builder = AlfacaseConverter(score_input_example)
    well_description = builder.build_well()
    num_regression.check(
        {
            "x": well_description.profile.x_and_y.x.GetValues("m"),
            "y": well_description.profile.x_and_y.y.GetValues("m"),
        }
    )
