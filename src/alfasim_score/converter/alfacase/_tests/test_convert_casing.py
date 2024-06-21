from typing import Any

import json
import pytest
from pathlib import Path
from pytest_regressions.data_regression import DataRegressionFixture

from alfasim_score.common import prepare_for_regression
from alfasim_score.converter.alfacase.convert_alfacase import ScoreAlfacaseConverter
from alfasim_score.converter.alfacase.score_input_reader import ScoreInputReader


def test_convert_casing_list(
    data_regression: DataRegressionFixture,
    score_input_example: ScoreInputReader,
) -> None:
    builder = ScoreAlfacaseConverter(score_input_example)
    casings = builder._convert_casing_list()
    data_regression.check(
        [
            prepare_for_regression(
                {
                    "name": casing.name,
                    "hanger_depth": casing.hanger_depth,
                    "settings_depth": casing.settings_depth,
                    "hole_diameter": casing.hole_diameter,
                    "outer_diameter": casing.outer_diameter,
                    "inner_diameter": casing.inner_diameter,
                    "inner_roughness": casing.inner_roughness,
                    "material": casing.material,
                    "top_of_filler": casing.top_of_filler,
                    "filler_material": casing.filler_material,
                    "material_above_filler": casing.material_above_filler,
                }
            )
            for casing in casings
        ]
    )


def test_convert_tubing_list(
    data_regression: DataRegressionFixture,
    score_input_example: ScoreInputReader,
) -> None:
    builder = ScoreAlfacaseConverter(score_input_example)
    tubings = builder._convert_tubing_list()
    data_regression.check(
        [
            prepare_for_regression(
                {
                    "name": tubing.name,
                    "length": tubing.length,
                    "outer_diameter": tubing.outer_diameter,
                    "inner_diameter": tubing.inner_diameter,
                    "inner_roughness": tubing.inner_roughness,
                    "material": tubing.material,
                }
            )
            for tubing in tubings
        ]
    )


def test_convert_packer_list(
    data_regression: DataRegressionFixture,
    score_input_example: ScoreInputReader,
) -> None:
    builder = ScoreAlfacaseConverter(score_input_example)
    packers = builder._convert_packer_list()
    data_regression.check(
        [
            prepare_for_regression(
                {
                    "name": packer.name,
                    "position": packer.position,
                    "material_above": packer.material_above,
                }
            )
            for packer in packers
        ]
    )


def test_convert_open_hole_list(
    data_regression: DataRegressionFixture,
    score_input_example: ScoreInputReader,
) -> None:
    builder = ScoreAlfacaseConverter(score_input_example)
    open_holes = builder._convert_open_hole_list()
    data_regression.check(
        [
            prepare_for_regression(
                {
                    "name": hole.name,
                    "length": hole.length,
                    "diameter": hole.diameter,
                    "inner_roughness": hole.inner_roughness,
                }
            )
            for hole in open_holes
        ]
    )
