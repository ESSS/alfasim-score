from pytest_regressions.data_regression import DataRegressionFixture

from alfasim_score.converter.alfacase.convert_alfacase import ScoreAlfacaseConverter
from alfasim_score.converter.alfacase.score_input_reader import ScoreInputReader
from alfasim_score.converter.fixtures import score_input_example


def test_convert_materials(
    data_regression: DataRegressionFixture,
    score_input_example: ScoreInputReader,
) -> None:
    builder = ScoreAlfacaseConverter(score_input_example)
    materials = builder.convert_materials()

    data_regression.check(
        [
            {
                "name": material.name,
                "type": material.material_type.value,
                "density": material.density.GetValue(),
                "thermal_conductivity": material.thermal_conductivity.GetValue(),
                "heat_capacity": material.heat_capacity.GetValue(),
                "thermal_expansion": material.expansion.GetValue(),
            }
            for material in materials
        ]
    )
