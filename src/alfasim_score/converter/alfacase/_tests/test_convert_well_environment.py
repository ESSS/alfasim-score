from typing import cast

import attr
import json
import pytest
from alfasim_sdk import PipeThermalModelType
from alfasim_sdk import PipeThermalPositionInput
from pathlib import Path
from pytest_mock import MockerFixture
from pytest_regressions.data_regression import DataRegressionFixture

from alfasim_score.common import ScoreSimulationRegime
from alfasim_score.common import prepare_for_regression
from alfasim_score.constants import REFERENCE_VERTICAL_COORDINATE
from alfasim_score.converter.alfacase.convert_alfacase import ScoreAlfacaseConverter
from alfasim_score.converter.alfacase.score_input_data import ScoreInputData
from alfasim_score.converter.alfacase.score_input_reader import ScoreInputReader


def test_convert_well_environment(
    data_regression: DataRegressionFixture,
    score_data_gas_lift: ScoreInputData,
) -> None:
    builder = ScoreAlfacaseConverter(score_data_gas_lift)
    environment = builder._convert_well_environment()

    assert environment.thermal_model == PipeThermalModelType.Transient
    assert environment.position_input_mode == PipeThermalPositionInput.Tvd
    assert environment.reference_y_coordinate.GetValue() == pytest.approx(0.0)
    data_regression.check(
        [
            prepare_for_regression(attr.asdict(environment))
            for environment in environment.tvd_properties_table
        ]
    )


def test_convert_well_environment_steady_state(
    score_input_gas_lift: ScoreInputReader, tmp_path: Path
) -> None:
    data = json.loads(score_input_gas_lift.score_filepath.read_text())
    data["operation"]["thermal_data"]["pwpa_simulator"] = {
        "config": {"simulation_regime": "STEADY_STATE"}
    }
    patched = tmp_path / "input.json"
    patched.write_text(json.dumps(data))
    from alfasim_score.converter.alfacase.score_input_data import ScoreInputData

    builder = ScoreAlfacaseConverter(ScoreInputData(ScoreInputReader(patched)))
    environment = builder._convert_well_environment()
    assert environment.thermal_model == PipeThermalModelType.SteadyState


def test_get_pipe_thermal_model_raises_on_unknown_value(
    score_data_gas_lift: ScoreInputData, mocker: MockerFixture
) -> None:
    mocker.patch.object(
        ScoreInputReader,
        "read_simulation_regime",
        return_value=cast(ScoreSimulationRegime, "UNKNOWN"),
    )
    builder = ScoreAlfacaseConverter(score_data_gas_lift)
    with pytest.raises(AssertionError):
        builder._get_pipe_thermal_model()
