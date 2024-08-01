from copy import copy
from pytest_regressions.data_regression import DataRegressionFixture

from alfasim_score.converter.alfacase.base_operation import BaseOperationBuilder
from alfasim_score.converter.alfacase.convert_alfacase import ScoreAlfacaseConverter


def test_convert_nodes(
    data_regression: DataRegressionFixture,
    base_operation_gas_lift: BaseOperationBuilder,
) -> None:
    base_alfacase = copy(base_operation_gas_lift.base_alfacase)
    base_operation_gas_lift.configure_nodes(base_alfacase)
    data_regression.check(
        [
            {"name": node.name, "type": node.node_type.value, "pvt_model": node.pvt_model}
            for node in base_alfacase.nodes
        ]
    )
