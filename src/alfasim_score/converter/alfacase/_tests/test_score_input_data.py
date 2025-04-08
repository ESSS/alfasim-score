import attr
from pytest_regressions.data_regression import DataRegressionFixture

from alfasim_score.common import AnnulusLabel
from alfasim_score.common import prepare_for_regression
from alfasim_score.converter.alfacase.convert_alfacase import ScoreAlfacaseConverter
from alfasim_score.converter.alfacase.score_input_data import ScoreInputData


def test_get_annuli_list(
    data_regression: DataRegressionFixture,
    score_data_gas_lift: ScoreInputData,
) -> None:
    assert score_data_gas_lift.get_annuli_list() == [AnnulusLabel.A, AnnulusLabel.B]
