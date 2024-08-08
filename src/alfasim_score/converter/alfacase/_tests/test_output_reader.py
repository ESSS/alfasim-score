import pandas as pd
import pytest
from pathlib import Path
from pytest_regressions.num_regression import NumericRegressionFixture

from alfasim_score.converter.alfacase.score_input_reader import ScoreInputReader


def test_output_reader(
    datadir: Path,
    num_regression: NumericRegressionFixture,
    score_input_gas_lift: ScoreInputReader,
) -> None:
    example_exported_filepath = datadir / "pressure_example.csv"
    score_input_gas_lift.export_profile_curve(example_exported_filepath, "pressure")

    results = pd.read_csv(example_exported_filepath)
    num_regression.check(
        {
            "measured_depth": results["measured_depth"],
            "pressure": results["pressure"],
        }
    )


def test_score_without_result(
    score_input_gas_lift: ScoreInputReader,
) -> None:
    score_input_gas_lift.input_content["operation"]["thermal_simulation"].pop("result")
    assert len(score_input_gas_lift.read_output_curves()) == 0


def test_read_wrong_operation_type(score_input_gas_lift: ScoreInputReader) -> None:
    score_input_gas_lift.input_content["operation"]["type"] = "UNKNOWN_OPERATION_TYPE"
    with pytest.raises(ValueError):
        score_input_gas_lift.read_operation_type()
