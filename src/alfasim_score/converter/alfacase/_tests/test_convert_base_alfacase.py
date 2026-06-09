from typing import cast

import pytest
from alfasim_sdk import convert_description_to_alfacase
from pytest_mock import MockerFixture
from pytest_regressions.file_regression import FileRegressionFixture

from alfasim_score.common import ScoreSimulationRegime
from alfasim_score.converter.alfacase.base_operation import BaseOperationBuilder
from alfasim_score.converter.alfacase.convert_alfacase import ScoreAlfacaseConverter
from alfasim_score.converter.alfacase.score_input_reader import ScoreInputReader

_UNKNOWN_REGIME = cast(ScoreSimulationRegime, "UNKNOWN")


def test_get_simulation_regime_raises_on_unknown_value(
    base_operation_gas_lift: BaseOperationBuilder,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(ScoreInputReader, "read_simulation_regime", return_value=_UNKNOWN_REGIME)
    with pytest.raises(AssertionError):
        base_operation_gas_lift._get_simulation_regime()


def test_get_initial_condition_strategy_raises_on_unknown_value(
    base_operation_gas_lift: BaseOperationBuilder,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(ScoreInputReader, "read_simulation_regime", return_value=_UNKNOWN_REGIME)
    with pytest.raises(AssertionError):
        base_operation_gas_lift._get_initial_condition_strategy()


def test_create_alfacase_base(
    file_regression: FileRegressionFixture,
    alfacase_gas_lift: ScoreAlfacaseConverter,
) -> None:
    case_description = alfacase_gas_lift.build_base_alfacase_description()
    file_regression.check(
        convert_description_to_alfacase(case_description), encoding="utf-8", extension=".alfacase"
    )


def test_create_alfacase_base_operation_configuration(
    file_regression: FileRegressionFixture,
    base_operation_gas_lift: BaseOperationBuilder,
) -> None:
    configured_alfacase = base_operation_gas_lift.generate_operation_alfacase_description()
    file_regression.check(
        convert_description_to_alfacase(configured_alfacase),
        encoding="utf-8",
        extension=".alfacase",
    )
