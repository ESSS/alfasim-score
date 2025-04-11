import pytest
from pathlib import Path
from pytest_regressions.dataframe_regression import DataFrameRegressionFixture
from pytest_regressions.file_regression import FileRegressionFixture

from alfasim_score.converter.wellprop.wellprop_pvt_table_converter import WellpropToPvtConverter


@pytest.mark.parametrize("fluid_name", ("N2_LIFT", "DFLT_FCBA_9.90", "DFLT_FPBNA_OLEO_NACL_10.00"))
def test_wellprop_to_pvt_converter(
    shared_datadir: Path,
    file_regression: FileRegressionFixture,
    fluid_name: str,
) -> None:
    converter = WellpropToPvtConverter(str(shared_datadir / fluid_name), fluid_name)
    converter.read_wellprop_files()
    pvt_table = converter.convert_pvt_table_data()
    # print(pvt_table)
    # with open(datadir / f"{fluid_name}.tab", "w") as f:
    #     f.write(pvt_table.getvalue())

    # output_file_name = f"{fluid_name}.tab"

    # file_regression.check(GetFileContents(datadir / output_file_name), extension=".tab")


@pytest.mark.parametrize("fluid_name", ("N2_LIFT", "DFLT_FCBA_9.90", "DFLT_FPBNA_OLEO_NACL_10.00"))
def test_convert_pvt_table_data(
    shared_datadir: Path,
    dataframe_regression: DataFrameRegressionFixture,
    fluid_name: str,
) -> None:
    converter = WellpropToPvtConverter(str(shared_datadir / fluid_name), fluid_name)
    converter.read_wellprop_files()
    dataframe_regression.check(converter.convert_pvt_table_data())
