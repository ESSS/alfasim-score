from barril.units import Scalar
from pytest_regressions.data_regression import DataRegressionFixture

from alfasim_score.common import AnnulusLabel
from alfasim_score.converter.alfacase.score_input_data import ScoreInputData
from alfasim_score.units import PRESSURE_UNIT


def test_get_annuli_list(
    data_regression: DataRegressionFixture,
    score_data_gas_lift: ScoreInputData,
) -> None:
    assert score_data_gas_lift.get_annuli_list() == [AnnulusLabel.A, AnnulusLabel.B]


def test_get_seabed_hydrostatic_pressure(
    score_data_gas_lift: ScoreInputData,
) -> None:
    assert score_data_gas_lift.get_seabed_hydrostatic_pressure() == Scalar(20562115.0, "Pa")
