from pytest_regressions.num_regression import NumericRegressionFixture

from alfasim_score.converter.alfacase.convert_alfacase import ScoreAlfacaseConverter
from alfasim_score.converter.alfacase.score_input_reader import ScoreInputReader


def test_convert_well_trajectory(
    num_regression: NumericRegressionFixture,
    score_input_gas_lift: ScoreInputReader,
) -> None:
    builder = ScoreAlfacaseConverter(score_input_gas_lift)
    well_trajectory = builder._convert_well_trajectory()
    num_regression.check(
        {
            "x": well_trajectory.x_and_y.x.GetValues(),
            "y": well_trajectory.x_and_y.y.GetValues(),
        }
    )
