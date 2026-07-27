import numpy as np
import pandas as pd
import pytest
from pathlib import Path
from pytest_regressions.data_regression import DataRegressionFixture
from pytest_regressions.dataframe_regression import DataFrameRegressionFixture
from pytest_regressions.file_regression import FileRegressionFixture

from alfasim_score.converter.pvt_table.pvt_table_file import PvtTableError
from alfasim_score.converter.pvt_table.pvt_table_file import generate_pvt_table_content
from alfasim_score.converter.pvt_table.pvt_table_file import parse_pvt_table_content
from alfasim_score.converter.pvt_table.pvt_table_file import read_pvt_table_file
from alfasim_score.converter.pvt_table.pvt_table_fixer import GAS_LIQUID_PROPERTY_PAIRS
from alfasim_score.converter.pvt_table.pvt_table_fixer import PvtTableFixer
from alfasim_score.converter.pvt_table.pvt_table_fixer import PvtTablePhase

TABLE_FILENAMES = (
    "gas_only.tab",
    "liquid_only.tab",
    "partially_absent_gas.tab",
    "two_phase_complete.tab",
)

TABLE_WITH_POINTS_ORDERED_BY_TEMPERATURE = (
    'PVTTABLE LABEL = "ORDERED_BY_TEMPERATURE", PHASE = TWO,\n'
    "COLUMNS = (PT, TM, ROG, ROHL, RS, VISG, VISHL)\n"
    "PVTTABLE POINT = (1.0e5, 1.0e1, 1.2e0, 9.00e2, 5.0e-1, 1.00e-5, 1.00e-3)\n"
    "PVTTABLE POINT = (2.0e5, 1.0e1, 0.0e0, 9.01e2, 0.0e0, 0.00e-5, 1.10e-3)\n"
    "PVTTABLE POINT = (1.0e5, 2.0e1, 1.1e0, 8.95e2, 5.1e-1, 1.10e-5, 0.90e-3)\n"
    "PVTTABLE POINT = (2.0e5, 2.0e1, 0.0e0, 8.96e2, 0.0e0, 0.00e-5, 0.95e-3)\n"
)

TABLE_WITHOUT_ANY_PHASE = (
    'PVTTABLE LABEL = "WITHOUT_ANY_PHASE", PHASE = TWO,\n'
    "COLUMNS = (PT, TM, ROG, ROHL, RS)\n"
    "PVTTABLE POINT = (1.0e5, 1.0e1, 0.0e0, 0.0e0, 0.0e0)\n"
    "PVTTABLE POINT = (1.0e5, 2.0e1, 0.0e0, 0.0e0, 0.0e0)\n"
    "PVTTABLE POINT = (2.0e5, 1.0e1, 0.0e0, 0.0e0, 0.0e0)\n"
    "PVTTABLE POINT = (2.0e5, 2.0e1, 0.0e0, 0.0e0, 0.0e0)\n"
)


@pytest.mark.parametrize("filename", TABLE_FILENAMES)
def test_check_pvt_table(
    shared_datadir: Path, data_regression: DataRegressionFixture, filename: str
) -> None:
    check_result = PvtTableFixer.from_file(shared_datadir / filename).check()
    data_regression.check(check_result.to_dict())


@pytest.mark.parametrize("filename", TABLE_FILENAMES)
def test_check_describe(
    shared_datadir: Path, file_regression: FileRegressionFixture, filename: str
) -> None:
    check_result = PvtTableFixer.from_file(shared_datadir / filename).check()
    file_regression.check(check_result.describe(), extension=".txt")


@pytest.mark.parametrize("filename", TABLE_FILENAMES)
def test_generate_fixed_pvt_table_content(
    shared_datadir: Path, file_regression: FileRegressionFixture, filename: str
) -> None:
    fixed_pvt_table_data, _ = PvtTableFixer.from_file(shared_datadir / filename).fix()
    content = generate_pvt_table_content(fixed_pvt_table_data)
    file_regression.check(content.getvalue(), extension=".tab")


@pytest.mark.parametrize("filename", TABLE_FILENAMES)
def test_fixed_pvt_table_data(
    shared_datadir: Path, dataframe_regression: DataFrameRegressionFixture, filename: str
) -> None:
    fixed_pvt_table_data, _ = PvtTableFixer.from_file(shared_datadir / filename).fix()
    dataframe_regression.check(fixed_pvt_table_data.table)


def test_fix_liquid_that_does_not_exist_anywhere(shared_datadir: Path) -> None:
    fixer = PvtTableFixer.from_file(shared_datadir / "gas_only.tab")
    original_table = fixer.pvt_table_data.table
    fixed_pvt_table_data, check_result = fixer.fix()
    fixed_table = fixed_pvt_table_data.table

    assert len(check_result.phase_issues) == 1
    assert check_result.phase_issues[0].phase is PvtTablePhase.LIQUID
    assert check_result.phase_issues[0].is_fully_absent
    for gas_column, liquid_column in GAS_LIQUID_PROPERTY_PAIRS:
        assert np.array_equal(
            fixed_table[liquid_column].to_numpy(), fixed_table[gas_column].to_numpy()
        ), f"{liquid_column} was not copied from {gas_column}"
    assert np.array_equal(fixed_table["RS"].to_numpy(), original_table["RS"].to_numpy())
    assert np.all(fixed_table["RS"].to_numpy() == 1.0)
    assert np.all(fixed_table["SIGGHL"].to_numpy() == 0.0)


def test_fix_gas_that_does_not_exist_anywhere(shared_datadir: Path) -> None:
    fixer = PvtTableFixer.from_file(shared_datadir / "liquid_only.tab")
    original_table = fixer.pvt_table_data.table
    fixed_pvt_table_data, check_result = fixer.fix()
    fixed_table = fixed_pvt_table_data.table

    assert len(check_result.phase_issues) == 1
    assert check_result.phase_issues[0].phase is PvtTablePhase.GAS
    assert check_result.phase_issues[0].is_fully_absent
    for gas_column, liquid_column in GAS_LIQUID_PROPERTY_PAIRS:
        assert np.array_equal(
            fixed_table[gas_column].to_numpy(), fixed_table[liquid_column].to_numpy()
        ), f"{gas_column} was not copied from {liquid_column}"
    assert np.array_equal(fixed_table["RS"].to_numpy(), original_table["RS"].to_numpy())
    assert np.all(fixed_table["RS"].to_numpy() == 0.0)


def test_fix_gas_that_does_not_exist_in_some_points(shared_datadir: Path) -> None:
    fixer = PvtTableFixer.from_file(shared_datadir / "partially_absent_gas.tab")
    original_table = fixer.pvt_table_data.table
    fixed_pvt_table_data, check_result = fixer.fix()
    fixed_table = fixed_pvt_table_data.table

    assert len(check_result.phase_issues) == 1
    assert not check_result.phase_issues[0].is_fully_absent
    assert check_result.phase_issues[0].absent_points == 10
    assert not fixed_table.isna().to_numpy().any()
    assert check_result.phase_issues[0].fixed_columns == ["ROG", "VISG", "CPG", "TCG"]
    for column in ("ROG", "VISG", "CPG", "TCG"):
        assert (fixed_table[column].to_numpy() > 0.0).all(), f"{column} still has a zero"
    unchanged_columns = (
        "RS",
        "DROGDP",
        "DROGDT",
        "HG",
        "ROHL",
        "DROHLDP",
        "DROHLDT",
        "VISHL",
        "CPHL",
        "HHL",
        "TCHL",
        "SIGGHL",
    )
    for column in unchanged_columns:
        assert np.array_equal(
            fixed_table[column].to_numpy(), original_table[column].to_numpy()
        ), f"{column} should not have been changed"


def test_fix_table_with_all_the_phases_is_a_no_operation(shared_datadir: Path) -> None:
    fixer = PvtTableFixer.from_file(shared_datadir / "two_phase_complete.tab")
    fixed_pvt_table_data, check_result = fixer.fix()
    assert not check_result.has_issues
    pd.testing.assert_frame_equal(fixed_pvt_table_data.table, fixer.pvt_table_data.table)


def test_zeroed_column_of_an_existing_phase_is_only_reported(shared_datadir: Path) -> None:
    fixer = PvtTableFixer.from_file(shared_datadir / "liquid_only.tab")
    fixed_pvt_table_data, check_result = fixer.fix()
    assert check_result.zeroed_columns == ["HHL", "SIGGHL"]
    assert np.all(fixed_pvt_table_data.table["HHL"].to_numpy() == 0.0)


def test_out_of_bound_column_of_an_existing_phase_is_only_reported(shared_datadir: Path) -> None:
    fixer = PvtTableFixer.from_file(shared_datadir / "partially_absent_gas.tab")
    fixed_pvt_table_data, check_result = fixer.fix()
    assert check_result.out_of_bound_columns == {"DROHLDP": 12, "DROHLDT": 10}
    assert (fixed_pvt_table_data.table["DROHLDP"].to_numpy() < 0.0).any()


def test_fix_keeps_the_order_of_the_points() -> None:
    pvt_table_data = parse_pvt_table_content(TABLE_WITH_POINTS_ORDERED_BY_TEMPERATURE)
    fixed_pvt_table_data, _ = PvtTableFixer(pvt_table_data).fix()
    fixed_table = fixed_pvt_table_data.table

    assert np.array_equal(
        fixed_table["PT"].to_numpy(), pvt_table_data.table["PT"].to_numpy()
    ), "the points were reordered"
    assert np.array_equal(fixed_table["ROG"].to_numpy(), [1.2, 1.2, 1.1, 1.1])
    assert np.array_equal(fixed_table["VISG"].to_numpy(), [1.00e-5, 1.00e-5, 1.10e-5, 1.10e-5])


def test_fix_table_without_any_phase_raises() -> None:
    fixer = PvtTableFixer(parse_pvt_table_content(TABLE_WITHOUT_ANY_PHASE))
    with pytest.raises(PvtTableError, match="Neither the gas nor the liquid phase exists"):
        fixer.fix()


def test_generate_fixed_pvt_table_file(shared_datadir: Path, tmp_path: Path) -> None:
    fixer = PvtTableFixer.from_file(shared_datadir / "liquid_only.tab")
    output_filepath = tmp_path / "fixed.tab"
    check_result = fixer.generate_fixed_pvt_table_file(output_filepath)

    assert check_result.has_issues
    assert output_filepath.exists(), "the fixed pvt table could not be created."
    written_pvt_table_data = read_pvt_table_file(output_filepath)
    fixed_pvt_table_data, _ = fixer.fix()
    pd.testing.assert_frame_equal(written_pvt_table_data.table, fixed_pvt_table_data.table)
