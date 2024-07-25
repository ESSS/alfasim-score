import attr
from pytest_regressions.data_regression import DataRegressionFixture

from alfasim_score.common import prepare_for_regression
from alfasim_score.converter.alfacase.convert_alfacase import ScoreAlfacaseConverter
from alfasim_score.converter.alfacase.score_input_reader import ScoreInputReader


def test_convert_materials(
    data_regression: DataRegressionFixture,
    score_input_gas_lift: ScoreInputReader,
) -> None:
    builder = ScoreAlfacaseConverter(score_input_gas_lift)
    materials = builder._convert_materials()

    data_regression.check([prepare_for_regression(attr.asdict(material)) for material in materials])
