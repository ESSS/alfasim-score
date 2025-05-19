from typing import Dict

import numpy as np
import pytest
from _pytest.monkeypatch import MonkeyPatch
from barril.units import Array
from barril.units import Scalar
from pytest_regressions.data_regression import DataRegressionFixture

from alfasim_score.common import AnnulusLabel
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
