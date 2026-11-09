import pytest
from pathlib import Path

from alfasim_score.converter.wellprop.cli import EXIT_CODE_INVALID_FOLDER
from alfasim_score.converter.wellprop.cli import EXIT_CODE_SUCCESS
from alfasim_score.converter.wellprop.cli import main
from alfasim_score.converter.wellprop.wellprop_pvt_table_converter import WellpropToPvtConverter


def test_convert_inside_the_wellprop_folder(shared_datadir: Path) -> None:
    wellprop_folder = shared_datadir / "N2_LIFT"

    assert main([str(wellprop_folder)]) == EXIT_CODE_SUCCESS

    converter = WellpropToPvtConverter(wellprop_folder)
    expected_content = converter._generate_pvt_table_content(
        converter._convert_and_fix_pvt_table_data()
    )
    assert (wellprop_folder / "N2_LIFT.tab").read_text() == expected_content.getvalue()


@pytest.mark.filterwarnings("ignore:No wellprop file found")
def test_convert_more_than_one_folder_to_the_output_folder(
    shared_datadir: Path, tmp_path: Path
) -> None:
    output_folder = tmp_path / "pvt_tables"
    wellprop_folders = [shared_datadir / "N2_LIFT", shared_datadir / "DFLT_FCBA_9.90"]

    assert (
        main([*(str(folder) for folder in wellprop_folders), "-o", str(output_folder)])
        == EXIT_CODE_SUCCESS
    )

    assert sorted(path.name for path in output_folder.iterdir()) == [
        "DFLT_FCBA_9.90.tab",
        "N2_LIFT.tab",
    ]


def test_folder_that_does_not_exist_is_reported_as_an_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([str(tmp_path / "missing")]) == EXIT_CODE_INVALID_FOLDER
    assert "is not a folder" in capsys.readouterr().err
