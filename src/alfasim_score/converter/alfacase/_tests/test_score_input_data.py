from typing import Dict
from typing import Optional

import json
import numpy as np
import pytest
from _pytest.monkeypatch import MonkeyPatch
from barril.units import Array
from barril.units import Scalar
from pathlib import Path
from pytest_regressions.data_regression import DataRegressionFixture

from alfasim_score.common import AnnulusLabel
from alfasim_score.common import ScoreSimulationRegime
from alfasim_score.constants import MAXIMUM_DISTANCE_BETWEEN_TRAJECTORY_POINTS
from alfasim_score.converter.alfacase.score_input_data import ScoreInputData
from alfasim_score.converter.alfacase.score_input_reader import ScoreInputReader
from alfasim_score.units import LENGTH_UNIT


def test_get_annuli_list(
    data_regression: DataRegressionFixture,
    score_data_gas_lift: ScoreInputData,
) -> None:
    assert score_data_gas_lift.get_annuli_list() == [AnnulusLabel.A, AnnulusLabel.B]


def test_get_seabed_hydrostatic_pressure(
    score_data_gas_lift: ScoreInputData,
) -> None:
    assert score_data_gas_lift.get_seabed_hydrostatic_pressure() == Scalar(20562115.0, "Pa")


@pytest.mark.parametrize(
    "trajectory_data",
    [
        {"x": Array([0, 0, 0, 0], LENGTH_UNIT), "y": Array([2072, 2092, 2102, 2112], LENGTH_UNIT)},
        {"x": Array([0, 0, 0, 0], LENGTH_UNIT), "y": Array([2072, 2132, 2202, 2272], LENGTH_UNIT)},
        {
            "x": Array([0, 50, 150, 300], LENGTH_UNIT),
            "y": Array([2072, 2122, 2222, 2372], LENGTH_UNIT),
        },
    ],
)
def test_get_refined_trajectory(
    trajectory_data: Dict[str, Array], score_data_gas_lift: ScoreInputData, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(ScoreInputReader, "read_well_trajectory", lambda _: trajectory_data)
    refined = score_data_gas_lift.get_refined_trajectory()
    x_out = refined["x"].GetValues(LENGTH_UNIT)
    y_out = refined["y"].GetValues(LENGTH_UNIT)

    # check if all positions are really < 50m
    points = np.stack((x_out, y_out), axis=1)
    deltas = np.linalg.norm(points[1:] - points[:-1], axis=1)
    max_distance = MAXIMUM_DISTANCE_BETWEEN_TRAJECTORY_POINTS.GetValue(LENGTH_UNIT)
    assert np.all(deltas <= max_distance + 1e-6)


@pytest.mark.parametrize(
    "input_file, expected",
    [
        (None, ScoreSimulationRegime.TRANSIENT),
        ("STEADY_STATE", ScoreSimulationRegime.STEADY_STATE),
        ("PSEUDO_TRANSIENT", ScoreSimulationRegime.PSEUDO_TRANSIENT),
    ],
)
def test_read_simulation_regime(
    score_input_gas_lift: ScoreInputReader,
    tmp_path: Path,
    input_file: Optional[str],
    expected: ScoreSimulationRegime,
) -> None:
    def _make_reader_with_regime(
        base_reader: ScoreInputReader, tmp_path: Path, regime: Optional[str]
    ) -> ScoreInputReader:
        """Write a patched copy of the base fixture JSON with the given simulation_regime value."""
        data = json.loads(base_reader.score_filepath.read_text())
        thermal_data = data["operation"]["thermal_data"]
        if regime is None:
            thermal_data.pop("pwpa_simulator", None)
        else:
            thermal_data["pwpa_simulator"] = {"config": {"simulation_regime": regime}}
        patched = tmp_path / "input.json"
        patched.write_text(json.dumps(data))
        return ScoreInputReader(patched)

    reader = _make_reader_with_regime(score_input_gas_lift, tmp_path, input_file)
    assert reader.read_simulation_regime() == expected


def test_read_simulation_regime_default(score_input_gas_lift: ScoreInputReader) -> None:
    assert score_input_gas_lift.read_simulation_regime() is ScoreSimulationRegime.TRANSIENT


def test_read_simulation_regime_when_pwpa_simulator_is_null(
    score_input_gas_lift: ScoreInputReader, tmp_path: Path
) -> None:
    data = json.loads(score_input_gas_lift.score_filepath.read_text())
    data["operation"]["thermal_data"]["pwpa_simulator"] = None
    patched = tmp_path / "input.json"
    patched.write_text(json.dumps(data))
    reader = ScoreInputReader(patched)
    assert reader.read_simulation_regime() is ScoreSimulationRegime.TRANSIENT
