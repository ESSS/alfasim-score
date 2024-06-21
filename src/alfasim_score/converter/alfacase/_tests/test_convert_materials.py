from pytest_regressions.data_regression import DataRegressionFixture

from alfasim_score.common import prepare_for_regression
from alfasim_score.converter.alfacase.convert_alfacase import ScoreAlfacaseConverter
from alfasim_score.converter.alfacase.score_input_reader import ScoreInputReader


def test_convert_materials(
    data_regression: DataRegressionFixture,
    score_input_example: ScoreInputReader,
) -> None:
    builder = ScoreAlfacaseConverter(score_input_example)
    materials = builder.convert_materials()

    data_regression.check(
        [
            prepare_for_regression(
                {
                    "name": material.name,
                    "type": material.material_type.value,
                    "density": material.density,
                    "thermal_conductivity": material.thermal_conductivity,
                    "heat_capacity": material.heat_capacity,
                    "thermal_expansion": material.expansion,
                }
            )
            for material in materials
        ]
    )
