import attr
import pytest
from alfasim_sdk import PipeThermalModelType
from alfasim_sdk import PipeThermalPositionInput
from pytest_regressions.data_regression import DataRegressionFixture

from alfasim_score.common import prepare_for_regression
from alfasim_score.constants import REFERENCE_VERTICAL_COORDINATE
from alfasim_score.converter.alfacase.convert_alfacase import ScoreAlfacaseConverter
from alfasim_score.converter.alfacase.score_input_reader import ScoreInputReader


def test_convert_well_environment(
    data_regression: DataRegressionFixture,
    score_input_gas_lift: ScoreInputReader,
) -> None:
    builder = ScoreAlfacaseConverter(score_input_gas_lift)
    environment = builder._convert_well_environment()

    assert environment.thermal_model == PipeThermalModelType.SteadyState
    assert environment.position_input_mode == PipeThermalPositionInput.Tvd
    assert environment.reference_y_coordinate.GetValue() == pytest.approx(
        REFERENCE_VERTICAL_COORDINATE.GetValue()
    )
    data_regression.check(
        [
            prepare_for_regression(attr.asdict(environment))
            for environment in environment.tvd_properties_table
        ]
    )
