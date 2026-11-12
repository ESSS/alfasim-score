import numpy as np
import pandas as pd
import pytest
from pathlib import Path
from pytest_regressions.dataframe_regression import DataFrameRegressionFixture
from pytest_regressions.file_regression import FileRegressionFixture

from alfasim_score.converter.wellprop.wellprop_pvt_table_converter import WellpropToPvtConverter


@pytest.mark.filterwarnings("ignore:No wellprop file found")
@pytest.mark.parametrize("fluid_name", ("N2_LIFT", "DFLT_FCBA_9.90", "DFLT_FPBNA_OLEO_NACL_10.00"))
def test_generate_pvt_table_content(
    shared_datadir: Path,
    file_regression: FileRegressionFixture,
    fluid_name: str,
) -> None:
    converter = WellpropToPvtConverter(shared_datadir / fluid_name)
    pvt_data = converter._convert_and_fix_pvt_table_data()
    content = converter._generate_pvt_table_content(pvt_data)
    file_regression.check(content.getvalue(), extension=".tab")


@pytest.mark.filterwarnings("ignore:No wellprop file found")
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
    tmp_path: Path,
) -> None:
    converter = WellpropToPvtConverter(shared_datadir / "N2_LIFT")
    converter.generate_pvt_table_file(tmp_path)
    output_pvt_filepath = tmp_path / "N2_LIFT.tab"
    assert output_pvt_filepath.exists(), "PVT table could not be created."
    expected_content = converter._generate_pvt_table_content(
        converter._convert_and_fix_pvt_table_data()
    )
    assert output_pvt_filepath.read_text() == expected_content.getvalue()


def test_convert_surface_tension_from_the_liquid_file(shared_datadir: Path) -> None:
    surface_tension_filepath = (
        shared_datadir / "N2_LIFT" / "temperature_equivLIQUID_interfacial_tension.csv"
    )
    surface_tension = pd.read_csv(surface_tension_filepath, index_col=0)
    surface_tension[:] = 0.025
    surface_tension.to_csv(surface_tension_filepath)
    converter = WellpropToPvtConverter(shared_datadir / "N2_LIFT")

    table = converter._convert_and_fix_pvt_table_data().table

    assert np.unique(table["SIGGHL"]).tolist() == pytest.approx([0.025])


def test_convert_surface_tension_falls_back_to_the_gas_file(shared_datadir: Path) -> None:
    wellprop_folder = shared_datadir / "N2_LIFT"
    (wellprop_folder / "temperature_equivLIQUID_interfacial_tension.csv").unlink()
    surface_tension_filepath = wellprop_folder / "temperature_GAS_interfacial_tension.csv"
    surface_tension = pd.read_csv(surface_tension_filepath, index_col=0)
    surface_tension[:] = 0.03
    surface_tension.to_csv(surface_tension_filepath)
    converter = WellpropToPvtConverter(wellprop_folder)

    table = converter._convert_and_fix_pvt_table_data().table

    assert np.unique(table["SIGGHL"]).tolist() == pytest.approx([0.03])


def test_convert_warns_about_missing_files(shared_datadir: Path) -> None:
    converter = WellpropToPvtConverter(shared_datadir / "DFLT_FCBA_9.90")

    with pytest.warns(UserWarning, match="properties HG, HHL, SIGGHL: they are written as zero"):
        converter._convert_pvt_table_data()
