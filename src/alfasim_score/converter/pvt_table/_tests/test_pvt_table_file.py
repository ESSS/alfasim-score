import pytest
from pathlib import Path

from alfasim_score.converter.pvt_table.pvt_table_file import PvtTableError
from alfasim_score.converter.pvt_table.pvt_table_file import _parse_table_name
from alfasim_score.converter.pvt_table.pvt_table_file import generate_pvt_table_content
from alfasim_score.converter.pvt_table.pvt_table_file import parse_pvt_table_content
from alfasim_score.converter.pvt_table.pvt_table_file import read_pvt_table_file
from alfasim_score.converter.pvt_table.pvt_table_file import write_pvt_table_file

WELL_FORMED_FILENAMES = (
    "gas_only.tab",
    "liquid_only.tab",
    "partially_absent_gas.tab",
    "two_phase_complete.tab",
    "with_comments.tab",
)


@pytest.mark.parametrize("filename", WELL_FORMED_FILENAMES)
def test_read_and_write_round_trip(shared_datadir: Path, filename: str) -> None:
    pvt_table_filepath = shared_datadir / filename
    pvt_table_data = read_pvt_table_file(pvt_table_filepath)
    content = generate_pvt_table_content(pvt_table_data)
    assert content.getvalue() == pvt_table_filepath.read_text(encoding="utf-8")


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"], ids=["lf", "crlf", "cr"])
def test_write_keeps_the_line_ending_of_the_file(
    shared_datadir: Path, tmp_path: Path, newline: str
) -> None:
    original_bytes = (
        (shared_datadir / "with_comments.tab").read_text(encoding="utf-8").encode("utf-8")
    )
    if newline != "\n":
        original_bytes = original_bytes.replace(b"\n", newline.encode("utf-8"))
    input_filepath = tmp_path / "input.tab"
    input_filepath.write_bytes(original_bytes)

    output_filepath = tmp_path / "output.tab"
    write_pvt_table_file(read_pvt_table_file(input_filepath), output_filepath)
    assert output_filepath.read_bytes() == original_bytes


def test_read_table_grid(shared_datadir: Path) -> None:
    pvt_table_data = read_pvt_table_file(shared_datadir / "partially_absent_gas.tab")
    assert pvt_table_data.name == "BLACK_OIL_PARTIALLY_ABSENT_GAS"
    assert len(pvt_table_data.pressures) == 4
    assert len(pvt_table_data.temperatures) == 4
    assert pvt_table_data.pressures.unit == "Pa"
    assert pvt_table_data.temperatures.unit == "degC"
    assert len(pvt_table_data.table) == 16


def test_read_keeps_the_header_verbatim(shared_datadir: Path) -> None:
    pvt_table_data = read_pvt_table_file(shared_datadir / "with_comments.tab")
    assert pvt_table_data.layout is not None
    header_text = "\n".join(pvt_table_data.layout.header_lines)
    assert header_text.startswith("! A pvt table with comments in the header.")
    assert "BUBBLEPRESSURES = (1.500000e+05, 1.600000e+05),\\" in header_text
    assert "PRESSURE = (1.000000e+05,\\\n 2.000000e+05) Pa,\\" in header_text
    assert list(pvt_table_data.table.columns) == ["PT", "TM", "ROG", "ROHL", "RS"]


@pytest.mark.parametrize(
    ("filename", "expected_message"),
    [
        ("malformed_point_arity.tab", "has 4 values, but the COLUMNS keyword declares 5"),
        ("malformed_not_keyword_format.tab", "is not in the OLGA keyword format"),
        ("three_phase.tab", "PHASE = THREE"),
    ],
    ids=["point_arity", "not_keyword_format", "three_phase"],
)
def test_read_unsupported_file_raises(
    shared_datadir: Path, filename: str, expected_message: str
) -> None:
    with pytest.raises(PvtTableError, match=expected_message):
        read_pvt_table_file(shared_datadir / filename)


@pytest.mark.parametrize(
    ("content", "expected_message"),
    [
        ("\n\n", "has no content"),
        (
            'PVTTABLE LABEL = "A", PHASE = TWO,\nCOLUMNS = (PT, TM, ROG)\n',
            "has no PVTTABLE POINT line",
        ),
        (
            'PVTTABLE LABEL = "A", PHASE = TWO,\nPVTTABLE POINT = (1.0, 2.0)\n',
            "was found before the COLUMNS keyword",
        ),
        (
            'PVTTABLE LABEL = "A", PHASE = TWO,\n'
            "COLUMNS = (PT, TM, ROG)\n"
            'PVTTABLE LABEL = "B", PHASE = TWO,\n',
            "has more than one table",
        ),
        (
            'PVTTABLE LABEL = "A", PHASE = TWO,\n'
            "COLUMNS = (PH, TM, ROG)\n"
            "PVTTABLE POINT = (1.0, 2.0, 3.0)\n",
            "has no PT column",
        ),
        (
            'PVTTABLE LABEL = "A", PHASE = TWO,\n'
            "COLUMNS = (PT, TM, ROG, ROWT)\n"
            "PVTTABLE POINT = (1.0, 2.0, 3.0, 4.0)\n",
            "has the water phase columns ROWT",
        ),
        (
            'PVTTABLE LABEL = "A", PHASE = TWO,\n'
            "COLUMNS = (PT, TM, ROG)\n"
            "PVTTABLE POINT = (1.0, 2.0, abc)\n",
            "Could not read the values",
        ),
        (
            'PVTTABLE LABEL = "A", PHASE = TWO,\n'
            "COLUMNS = (PT, TM, ROG)\n"
            "PVTTABLE POINT = (1.0, 2.0, 3.0)\n"
            "PVTTABLE POINT = (1.0, 2.0, 4.0)\n",
            "more than one point for the same pressure and temperature",
        ),
        (
            'PVTTABLE LABEL = "A", PHASE = TWO,\n'
            "COLUMNS = (PT, TM, ROG)\n"
            "PVTTABLE POINT = (1.0, 2.0, 3.0)\n"
            "PVTTABLE POINT = (2.0, 5.0, 3.0)\n"
            "PVTTABLE POINT = (1.0, 5.0, 3.0)\n",
            "needs 4 points",
        ),
        (
            'PVTTABLE LABEL = "A", PHASE = TWO,\n'
            "COLUMNS = (PT, TM, ROG)\n"
            "PVTTABLE POINT = (1.0, 2.0, 3.0)\n"
            "SOMETHING ELSE = 1\n",
            "after the pvt table points",
        ),
        (
            'PVTTABLE LABEL = "A", PHASE = TWO,\n'
            "PRESSURE = (1.0) FURLONG,\\\n"
            "COLUMNS = (PT, TM, ROG)\n"
            "PVTTABLE POINT = (1.0, 2.0, 3.0)\n",
            "unit 'FURLONG' of the PRESSURE keyword is not supported",
        ),
        (
            'PVTTABLE LABEL = "A", PHASE = TWO,\n',
            "has no COLUMNS keyword",
        ),
        (
            'PVTTABLE LABEL = "A", PHASE = TWO,\n'
            "COLUMNS = (PT, TM, ROG)\n"
            "COLUMNS = (PT, TM, ROG)\n"
            "PVTTABLE POINT = (1.0, 2.0, 3.0)\n",
            "has more than one COLUMNS keyword",
        ),
        (
            'PVTTABLE LABEL = "A", PHASE = TWO,\n' "COLUMNS = (PT, , TM)\n",
            "Found an entry without a name in the COLUMNS keyword",
        ),
        (
            'PVTTABLE LABEL = "A", PHASE = TWO,\n'
            "COLUMNS = (PT, TM, ROG)\n"
            "PVTTABLE POINT = (1.0, 2.0, 3.0)\n"
            "SOMETHING ELSE = 1,\\",
            "after the pvt table points",
        ),
    ],
    ids=[
        "empty",
        "no_points",
        "point_before_columns",
        "more_than_one_table",
        "no_pressure_column",
        "water_columns",
        "value_that_is_not_a_number",
        "duplicated_point",
        "grid_that_is_not_rectangular",
        "content_after_the_points",
        "unsupported_unit",
        "no_columns_keyword",
        "more_than_one_columns_keyword",
        "columns_entry_without_a_name",
        "dangling_continuation_after_the_points",
    ],
)
def test_parse_invalid_content_raises(content: str, expected_message: str) -> None:
    with pytest.raises(PvtTableError, match=expected_message):
        parse_pvt_table_content(content)


def test_trailing_blank_line_after_the_points_is_allowed() -> None:
    content = (
        'PVTTABLE LABEL = "A", PHASE = TWO,\n'
        "COLUMNS = (PT, TM, ROG)\n"
        "PVTTABLE POINT = (1.0, 2.0, 3.0)\n"
        "\n"
    )
    pvt_table_data = parse_pvt_table_content(content)
    assert len(pvt_table_data.table) == 1


def test_parse_table_name_falls_back_to_the_default_name_when_there_is_no_label() -> None:
    """
    Defensive branch: `_parse_table_name` is only ever called with text already known to have a
    LABEL keyword, since `parse_pvt_table_content` checks that before calling it. Tested directly
    since it is unreachable through the public API.
    """
    assert _parse_table_name("no label here", default_name="default") == "default"
