import pytest
import shutil
from pathlib import Path

from alfasim_score.cli import EXIT_CODE_INVALID_FILE
from alfasim_score.cli import EXIT_CODE_ISSUES_FOUND
from alfasim_score.cli import EXIT_CODE_SUCCESS
from alfasim_score.cli import main


@pytest.fixture
def pvt_table_filepath(shared_datadir: Path, tmp_path: Path) -> Path:
    """A pvt table that has to be fixed, copied to a folder that can be written to."""
    return Path(shutil.copy(shared_datadir / "liquid_only.tab", tmp_path))


def test_check_only_reports_the_issues(
    pvt_table_filepath: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["--check-only", str(pvt_table_filepath)]) == EXIT_CODE_ISSUES_FOUND
    assert "GAS phase does not exist in 20 of 20 points" in capsys.readouterr().out
    assert not list(pvt_table_filepath.parent.glob("*_fixed.tab")), "no file should be written"


def test_check_only_of_a_table_without_issues(
    shared_datadir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pvt_table_filepath = shared_datadir / "two_phase_complete.tab"
    assert main(["--check-only", str(pvt_table_filepath)]) == EXIT_CODE_SUCCESS
    assert "there is nothing to fix" in capsys.readouterr().out


def test_write_the_fixed_table_with_the_default_name(pvt_table_filepath: Path) -> None:
    assert main([str(pvt_table_filepath)]) == EXIT_CODE_SUCCESS
    output_filepath = pvt_table_filepath.with_name("liquid_only_fixed.tab")
    assert output_filepath.exists(), "the fixed pvt table could not be created."
    assert output_filepath.read_text() != pvt_table_filepath.read_text()


def test_write_the_fixed_table_to_the_given_output(
    pvt_table_filepath: Path, tmp_path: Path
) -> None:
    output_filepath = tmp_path / "somewhere_else.tab"
    assert main([str(pvt_table_filepath), "--output", str(output_filepath)]) == EXIT_CODE_SUCCESS
    assert output_filepath.exists(), "the fixed pvt table could not be created."


def test_write_the_fixed_table_in_place(pvt_table_filepath: Path) -> None:
    original_content = pvt_table_filepath.read_text()
    assert main([str(pvt_table_filepath), "--in-place"]) == EXIT_CODE_SUCCESS
    assert pvt_table_filepath.read_text() != original_content
    assert not list(pvt_table_filepath.parent.glob("*_fixed.tab"))


def test_fix_more_than_one_table(shared_datadir: Path, tmp_path: Path) -> None:
    filepaths = [
        Path(shutil.copy(shared_datadir / filename, tmp_path))
        for filename in ("gas_only.tab", "liquid_only.tab")
    ]
    assert main([str(filepath) for filepath in filepaths]) == EXIT_CODE_SUCCESS
    assert (tmp_path / "gas_only_fixed.tab").exists()
    assert (tmp_path / "liquid_only_fixed.tab").exists()


def test_output_is_not_allowed_for_more_than_one_table(shared_datadir: Path) -> None:
    argv = [
        str(shared_datadir / "gas_only.tab"),
        str(shared_datadir / "liquid_only.tab"),
        "--output",
        "fixed.tab",
    ]
    with pytest.raises(SystemExit):
        main(argv)


@pytest.mark.parametrize("filename", ["three_phase.tab", "malformed_point_arity.tab"])
def test_unsupported_table_is_reported_as_an_error(
    shared_datadir: Path, capsys: pytest.CaptureFixture[str], filename: str
) -> None:
    assert main(["--check-only", str(shared_datadir / filename)]) == EXIT_CODE_INVALID_FILE
    assert filename in capsys.readouterr().err


def test_table_that_does_not_exist_is_reported_as_an_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["--check-only", str(tmp_path / "missing.tab")]) == EXIT_CODE_INVALID_FILE
    assert "missing.tab" in capsys.readouterr().err


def test_quiet_does_not_print_the_report(
    pvt_table_filepath: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["--check-only", "--quiet", str(pvt_table_filepath)]) == EXIT_CODE_ISSUES_FOUND
    assert capsys.readouterr().out == ""
