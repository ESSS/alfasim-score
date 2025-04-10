import pytest
from pathlib import Path
from pytest_regressions.dataframe_regression import DataFrameRegressionFixture
from pytest_regressions.file_regression import FileRegressionFixture

from alfasim_score.converter.wellprop.wellprop_pvt_table_converter import WellpropToPvtConverter


@pytest.mark.parametrize("fluid_name", ("N2_LIFT", "DFLT_FCBA_9.90", "DFLT_FPBNA_OLEO_NACL_10.00"))
def test_generate_pvt_table_content(
    shared_datadir: Path,
    file_regression: FileRegressionFixture,
    fluid_name: str,
) -> None:
    converter = WellpropToPvtConverter(shared_datadir / fluid_name)
    pvt_data = converter._convert_pvt_table_data()
    content = converter._generate_pvt_table_content(pvt_data)
    file_regression.check(content.getvalue(), extension=".tab")


@pytest.mark.parametrize("fluid_name", ("N2_LIFT", "DFLT_FCBA_9.90", "DFLT_FPBNA_OLEO_NACL_10.00"))
def test_convert_pvt_table_data(
    shared_datadir: Path,
    dataframe_regression: DataFrameRegressionFixture,
    fluid_name: str,
) -> None:
    converter = WellpropToPvtConverter(shared_datadir / fluid_name)
    dataframe_regression.check(converter._convert_pvt_table_data().table)


def test_convert_pvt_table_file(
    shared_datadir: Path,
) -> None:
    converter = WellpropToPvtConverter(shared_datadir / "N2_LIFT")
    converter.generate_pvt_table_file(shared_datadir)
    output_pvt_filepath = Path(shared_datadir / "N2_LIFT.tab")
    assert output_pvt_filepath.exists(), "PVT table could not be created."
