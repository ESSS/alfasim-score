from typing import Any

import json
import pytest
from pathlib import Path
from pytest_regressions.num_regression import NumericRegressionFixture

from alfasim_score.converter.alfacase.convert_alfacase import ScoreAlfacaseConverter
from alfasim_score.converter.alfacase.score_input_reader import ScoreInputReader
from alfasim_score.converter.fixtures import score_input_example


def test_convert_well_trajectory(
    num_regression: NumericRegressionFixture,
    score_input_example: ScoreInputReader,
) -> None:
    builder = ScoreAlfacaseConverter(score_input_example)
    well_description = builder.build_well()
    num_regression.check(
        {
            "x": well_description.profile.x_and_y.x.GetValues("m"),
            "y": well_description.profile.x_and_y.y.GetValues("m"),
        }
    )
