import attr
from alfasim_sdk import NodeCellType
from pytest_regressions.data_regression import DataRegressionFixture

from alfasim_score.common import prepare_for_regression
from alfasim_score.converter.alfacase.convert_alfacase import ScoreAlfacaseConverter
from alfasim_score.converter.alfacase.score_input_reader import ScoreInputReader


def test_convert_nodes(
    data_regression: DataRegressionFixture,
    score_input_example: ScoreInputReader,
) -> None:
    builder = ScoreAlfacaseConverter(score_input_example)
    nodes = builder.build_nodes()
    data_regression.check(
        [
            {"name": node.name, "type": node.node_type.value, "pvt_model": node.pvt_model}
            for node in nodes
        ]
    )
