from pytest_regressions.data_regression import DataRegressionFixture

from alfasim_score.common import prepare_for_regression
from alfasim_score.converter.alfacase.convert_alfacase import ScoreAlfacaseConverter
from alfasim_score.converter.alfacase.score_input_reader import ScoreInputReader


def test_convert_formation(
    data_regression: DataRegressionFixture,
    score_input_example: ScoreInputReader,
) -> None:
    builder = ScoreAlfacaseConverter(score_input_example)
    formations = builder._convert_formation()

    data_regression.check(
        [
            prepare_for_regression(
                {
                    "name": formation.name,
                    "start": formation.start,
                    "material": formation.material,
                }
            )
            for formation in formations.layers
        ]
    )
