import attr
from pytest_regressions.data_regression import DataRegressionFixture

from alfasim_score.common import prepare_for_regression
from alfasim_score.converter.alfacase.convert_alfacase import ScoreAlfacaseConverter
from alfasim_score.converter.alfacase.score_input_reader import ScoreInputReader


def test_convert_casing_list(
    data_regression: DataRegressionFixture,
    score_input_gas_lift: ScoreInputReader,
) -> None:
    builder = ScoreAlfacaseConverter(score_input_gas_lift)
    casings = builder._convert_casing_list()
    data_regression.check([prepare_for_regression(attr.asdict(casing)) for casing in casings])


def test_convert_tubing_list(
    data_regression: DataRegressionFixture,
    score_input_gas_lift: ScoreInputReader,
) -> None:
    builder = ScoreAlfacaseConverter(score_input_gas_lift)
    tubings = builder._convert_tubing_list()
    data_regression.check([prepare_for_regression(attr.asdict(tubing)) for tubing in tubings])


def test_convert_packer_list(
    data_regression: DataRegressionFixture,
    score_input_gas_lift: ScoreInputReader,
) -> None:
    builder = ScoreAlfacaseConverter(score_input_gas_lift)
    packers = builder._convert_packer_list()
    data_regression.check([prepare_for_regression(attr.asdict(packer)) for packer in packers])


def test_convert_open_hole_list(
    data_regression: DataRegressionFixture,
    score_input_gas_lift: ScoreInputReader,
) -> None:
    builder = ScoreAlfacaseConverter(score_input_gas_lift)
    open_holes = builder._convert_open_hole_list()
    data_regression.check([prepare_for_regression(attr.asdict(hole)) for hole in open_holes])
