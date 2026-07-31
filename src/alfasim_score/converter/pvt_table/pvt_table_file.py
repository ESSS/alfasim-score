from typing import Optional

import numpy as np
import pandas as pd
import re
from barril.units import Array
from barril.units import Scalar
from dataclasses import dataclass
from enum import Enum
from io import StringIO
from pathlib import Path

LABEL_NUMBER_OF_PHASES = "TWO"
STDPRESSURE = Scalar(1.0, "atm")
STDTEMPERATURE = Scalar(2.887100e02, "K")
PVT_TABLE_VALUE_FORMAT = "{:.6e}"

PRESSURE_COLUMN = "PT"
TEMPERATURE_COLUMN = "TM"

# Comments written at the top of the tables this package generates, so that the origin of a file can
# be told apart from a table delivered by WELLBOREPROPS.
WELLPROP_CONVERSION_COMMENT = "! tab file converted from WELLBOREPROPS csv files by alfasim-score"
FIXED_TABLE_COMMENT = (
    "! tab file fixed by alfasim-score, the properties of the points where a phase does not exist "
    "were filled"
)

# Columns of the water phase, only written by three phase tables.
WATER_COLUMNS = frozenset(
    {"ROWT", "RSW", "DROWTDP", "DROWTDT", "VISWT", "CPWT", "HWT", "TCWT", "SIGGWT", "SIGHLWT"}
)

# Units accepted in the PRESSURE and TEMPERATURE keywords, mapped to the barril unit names.
PRESSURE_UNIT_BY_LABEL = {
    "PA": "Pa",
    "KPA": "kPa",
    "MPA": "MPa",
    "BAR": "bar",
    "PSI": "psi",
    "ATM": "atm",
}
TEMPERATURE_UNIT_BY_LABEL = {
    "C": "degC",
    "K": "K",
    "F": "degF",
    "R": "degR",
}
DEFAULT_PRESSURE_UNIT = "Pa"
DEFAULT_TEMPERATURE_UNIT = "degC"

_LABEL_PATTERN = re.compile(r"\bPVTTABLE\s+LABEL\s*=\s*([^,\n]+)", re.IGNORECASE)
_POINT_PATTERN = re.compile(r"^\s*PVTTABLE\s+POINT\s*=\s*\((.*)\)", re.IGNORECASE)
_COLUMNS_PATTERN = re.compile(r"\bCOLUMNS\s*=\s*\(([^)]*)\)", re.IGNORECASE)
_PRESSURE_PATTERN = re.compile(r"\bPRESSURE\s*=\s*\([^)]*\)\s*([A-Z]+)", re.IGNORECASE)
_TEMPERATURE_PATTERN = re.compile(r"\bTEMPERATURE\s*=\s*\([^)]*\)\s*([A-Z]+)", re.IGNORECASE)
_PHASE_PATTERN = re.compile(r"\bPHASE\s*=\s*([A-Z]+)", re.IGNORECASE)
_COMMENT_PREFIX = "!"


class PvtTableProperties(Enum):
    GasDensity = "ROG"
    LiquidDensity = "ROHL"
    GasDensityDP = "DROGDP"
    LiquidDensityDP = "DROHLDP"
    GasDensityDT = "DROGDT"
    LiquidDensityDT = "DROHLDT"
    GasMassFraction = "RS"
    GasViscosity = "VISG"
    LiquidViscosity = "VISHL"
    GasSpecificHeat = "CPG"
    LiquidSpecificHeat = "CPHL"
    GasSpecificEnthalpy = "HG"
    LiquidSpecificEnthalpy = "HHL"
    GasThermalConductivity = "TCG"
    LiquidThermalConductivity = "TCHL"
    GasLiquidSurfaceTension = "SIGGHL"


class PvtTableError(Exception):
    """Raised when a pvt table file cannot be read or is not supported."""


@dataclass
class PvtTableFileLayout:
    """
    Header and line ending of a pvt table file kept verbatim, so a file written back from a parsed
    table differs from the original one only in the values of the table points.
    """

    header_lines: list[str]
    newline: str = "\n"


@dataclass
class PvtTableData:
    name: str
    pressures: Array
    temperatures: Array
    table: pd.DataFrame
    layout: Optional[PvtTableFileLayout] = None


def _format_number(number: float) -> str:
    return PVT_TABLE_VALUE_FORMAT.format(number)


def _has_header_line(pvt_table_data: PvtTableData, line: str) -> bool:
    """Whether the header of the file the table was read from already has the given line."""
    if pvt_table_data.layout is None:
        return False
    return any(header_line.strip() == line for header_line in pvt_table_data.layout.header_lines)


def generate_pvt_table_content(
    pvt_table_data: PvtTableData, header_comments: tuple[str, ...] = ()
) -> StringIO:
    """
    Generate the content of a pvt table file in the OLGA keyword format.

    When the table carries the layout of the file it was read from, the original header is written
    back verbatim and only the table points are generated again.

    :param pvt_table_data: the pvt table to be written
    :param header_comments: comment lines written at the top of the file, skipped when the header
        read from the original file already has them, so that fixing a file twice does not repeat
        the same comment
    :return: the content of the pvt table file
    """
    file_buffer = StringIO()
    for comment in header_comments:
        if not _has_header_line(pvt_table_data, comment):
            file_buffer.write(f"{comment}\n")
    if pvt_table_data.layout is not None:
        for header_line in pvt_table_data.layout.header_lines:
            file_buffer.write(f"{header_line}\n")
    else:
        file_buffer.write(
            f'PVTTABLE LABEL = "{pvt_table_data.name}", PHASE = {LABEL_NUMBER_OF_PHASES},\n'
        )
        file_buffer.write(
            "STDPRESSURE = {} ATM,\\\n".format(_format_number(STDPRESSURE.GetValue("atm")))
        )
        file_buffer.write(
            "STDTEMPERATURE = {} K,\\\n".format(_format_number(STDTEMPERATURE.GetValue("K")))
        )
        file_buffer.write(
            "PRESSURE = ({}) Pa,\\\n".format(
                ", ".join(map(_format_number, pvt_table_data.pressures.GetValues("Pa")))
            )
        )
        file_buffer.write(
            "TEMPERATURE = ({}) C,\\\n".format(
                ", ".join(map(_format_number, pvt_table_data.temperatures.GetValues("degC")))
            )
        )
        file_buffer.write("COLUMNS = ({})\n".format(", ".join(pvt_table_data.table.columns)))
    for _, row in pvt_table_data.table.iterrows():
        file_buffer.write(f"PVTTABLE POINT = ({', '.join(map(_format_number, row.tolist()))})\n")
    return file_buffer


def write_pvt_table_file(
    pvt_table_data: PvtTableData,
    output_filepath: Path,
    header_comments: tuple[str, ...] = (),
) -> None:
    """
    Write the pvt table to a file in the OLGA keyword format.

    A table read from a file is written back with the line ending it originally had, so that fixing
    a table does not rewrite every line of the file.

    :param pvt_table_data: the pvt table to be written
    :param output_filepath: where the pvt table file is written
    :param header_comments: comment lines written at the top of the file
    """
    content = generate_pvt_table_content(pvt_table_data, header_comments)
    newline = pvt_table_data.layout.newline if pvt_table_data.layout is not None else None
    resolved_filepath = output_filepath.resolve()
    if not resolved_filepath.parent.is_dir():
        raise PvtTableError(f"The directory {resolved_filepath.parent} does not exist.")
    with open(resolved_filepath, "w", newline=newline) as file:
        file.write(content.getvalue())


def _get_newline(content: str) -> str:
    """Get the line ending used by the content of a file."""
    if "\r\n" in content:
        return "\r\n"
    if "\r" in content:
        return "\r"
    return "\n"


def read_pvt_table_file(pvt_table_filepath: Path) -> PvtTableData:
    """Read a pvt table file in the OLGA keyword format."""
    resolved_filepath = pvt_table_filepath.resolve(strict=True)
    if not resolved_filepath.is_file():
        raise PvtTableError(f"{resolved_filepath} is not a file.")
    with open(resolved_filepath, encoding="utf-8", newline="") as file:
        content = file.read()
    return parse_pvt_table_content(content, default_name=pvt_table_filepath.stem)


def _join_continuation_lines(content: str) -> list[tuple[str, str, int]]:
    """
    Group the physical lines of the file into logical lines, joining the ones continued with a
    trailing backslash.

    Each logical line is returned as the original text (verbatim, so it can be written back), the
    text with the continuations joined (to be parsed) and the number of the first physical line.
    """
    logical_lines = []
    original_lines: list[str] = []
    joined_parts: list[str] = []
    first_line_number = 1
    for line_number, physical_line in enumerate(content.splitlines(), start=1):
        if not original_lines:
            first_line_number = line_number
        original_lines.append(physical_line)
        stripped_line = physical_line.rstrip()
        if stripped_line.endswith("\\"):
            joined_parts.append(stripped_line[:-1])
            continue
        joined_parts.append(stripped_line)
        logical_lines.append(("\n".join(original_lines), "".join(joined_parts), first_line_number))
        original_lines = []
        joined_parts = []
    if original_lines:
        logical_lines.append(("\n".join(original_lines), "".join(joined_parts), first_line_number))
    return logical_lines


def _is_meaningful(joined_text: str) -> bool:
    stripped_text = joined_text.strip()
    return bool(stripped_text) and not stripped_text.startswith(_COMMENT_PREFIX)


def _parse_column_names(columns_text: str) -> list[str]:
    """
    Read the column names from the content of the COLUMNS keyword.

    Only the first token of each entry is used, so entries carrying a unit are also accepted.
    """
    column_names = []
    for entry in columns_text.split(","):
        tokens = entry.split()
        if not tokens:
            raise PvtTableError("Found an entry without a name in the COLUMNS keyword.")
        column_names.append(tokens[0].upper())
    return column_names


def _parse_table_name(joined_text: str, default_name: str) -> str:
    match = _LABEL_PATTERN.search(joined_text)
    if match is None:
        return default_name
    return match.group(1).strip().strip('"').strip("'") or default_name


def _parse_unit(
    header_text: str,
    pattern: "re.Pattern[str]",
    unit_by_label: dict[str, str],
    default_unit: str,
    keyword: str,
) -> str:
    match = pattern.search(header_text)
    if match is None:
        return default_unit
    unit_label = match.group(1).upper()
    if unit_label not in unit_by_label:
        raise PvtTableError(
            f"The unit '{match.group(1)}' of the {keyword} keyword is not supported."
        )
    return unit_by_label[unit_label]


def _parse_point_values(values_text: str, column_names: list[str], line_number: int) -> list[float]:
    """Read the values of a PVTTABLE POINT keyword."""
    try:
        values = [float(value) for value in values_text.split(",")]
    except ValueError:
        raise PvtTableError(
            f"Could not read the values of the pvt table point at line {line_number}."
        )
    if len(values) != len(column_names):
        raise PvtTableError(
            f"The pvt table point at line {line_number} has {len(values)} values, but the COLUMNS "
            f"keyword declares {len(column_names)} columns."
        )
    return values


def _parse_point_line(
    joined_text: str, column_names: Optional[list[str]], line_number: int
) -> Optional[list[float]]:
    """Parse a PVTTABLE POINT line, or return None when the line is not one."""
    point_match = _POINT_PATTERN.match(joined_text)
    if point_match is None:
        return None
    if column_names is None:
        raise PvtTableError(
            f"The pvt table point at line {line_number} was found before the COLUMNS keyword."
        )
    return _parse_point_values(point_match.group(1), column_names, line_number)


def _parse_header_line(
    joined_text: str, column_names: Optional[list[str]]
) -> tuple[int, Optional[list[str]]]:
    """Parse a header line, returning the number of LABEL keywords found and the column names."""
    columns_match = _COLUMNS_PATTERN.search(joined_text)
    if columns_match is not None:
        if column_names is not None:
            raise PvtTableError("The pvt table file has more than one COLUMNS keyword.")
        column_names = _parse_column_names(columns_match.group(1))
    return len(_LABEL_PATTERN.findall(joined_text)), column_names


def _read_header_and_points(
    logical_lines: list[tuple[str, str, int]]
) -> tuple[list[str], list[str], list[list[float]]]:
    """Split the lines of the file into the header, the column names and the table points."""
    header_lines: list[str] = []
    column_names: Optional[list[str]] = None
    points: list[list[float]] = []
    number_of_labels = 0
    for original_text, joined_text, line_number in logical_lines:
        point_values = _parse_point_line(joined_text, column_names, line_number)
        if point_values is not None:
            points.append(point_values)
            continue
        if points:
            if _is_meaningful(joined_text):
                raise PvtTableError(
                    f"Found the unsupported content '{joined_text.strip()}' at line {line_number}, "
                    "after the pvt table points."
                )
            continue
        label_count, column_names = _parse_header_line(joined_text, column_names)
        number_of_labels += label_count
        header_lines.append(original_text)

    if number_of_labels > 1:
        raise PvtTableError(
            "The pvt table file has more than one table, which is not supported. Split the tables "
            "into one file each."
        )
    if column_names is None:
        raise PvtTableError("The pvt table file has no COLUMNS keyword.")
    if not points:
        raise PvtTableError("The pvt table file has no PVTTABLE POINT line.")
    return header_lines, column_names, points


def _check_table_is_supported(header_text: str, column_names: list[str]) -> None:
    """Check that the pvt table is a two phase table in the pressure/temperature formulation."""
    phase_match = _PHASE_PATTERN.search(header_text)
    if phase_match is not None and phase_match.group(1).upper() != LABEL_NUMBER_OF_PHASES:
        raise PvtTableError(
            f"The pvt table has PHASE = {phase_match.group(1)}, but only tables with "
            f"PHASE = {LABEL_NUMBER_OF_PHASES} are supported."
        )
    water_columns = sorted(WATER_COLUMNS.intersection(column_names))
    if water_columns:
        raise PvtTableError(
            f"The pvt table has the water phase columns {', '.join(water_columns)}, but only two "
            "phase tables are supported."
        )
    for column in (PRESSURE_COLUMN, TEMPERATURE_COLUMN):
        if column not in column_names:
            raise PvtTableError(
                f"The pvt table has no {column} column, only tables in the pressure/temperature "
                "formulation are supported."
            )


def _check_grid_is_rectangular(table: pd.DataFrame) -> None:
    """Check that the points of the pvt table fill a rectangular pressure/temperature grid."""
    if table.duplicated(subset=[PRESSURE_COLUMN, TEMPERATURE_COLUMN]).any():
        raise PvtTableError(
            "The pvt table has more than one point for the same pressure and temperature."
        )
    number_of_pressures = len(np.unique(table[PRESSURE_COLUMN].to_numpy()))
    number_of_temperatures = len(np.unique(table[TEMPERATURE_COLUMN].to_numpy()))
    if len(table) != number_of_pressures * number_of_temperatures:
        raise PvtTableError(
            f"The pvt table has {len(table)} points, but a rectangular grid of "
            f"{number_of_pressures} pressures and {number_of_temperatures} temperatures needs "
            f"{number_of_pressures * number_of_temperatures} points."
        )


def parse_pvt_table_content(content: str, default_name: str = "") -> PvtTableData:
    """
    Parse the content of a pvt table file in the OLGA keyword format.

    The header is kept verbatim and only the PVTTABLE POINT lines and the COLUMNS keyword are
    interpreted, so keywords not used by this package are preserved when the file is written back.
    """
    logical_lines = _join_continuation_lines(content)
    meaningful_lines = [joined for _, joined, _ in logical_lines if _is_meaningful(joined)]
    if not meaningful_lines:
        raise PvtTableError("The pvt table file has no content.")
    if _LABEL_PATTERN.search(meaningful_lines[0]) is None:
        raise PvtTableError(
            "The pvt table file is not in the OLGA keyword format, the first line was expected to "
            "have the PVTTABLE LABEL keyword."
        )

    header_lines, column_names, points = _read_header_and_points(logical_lines)
    header_text = "\n".join(header_lines)
    _check_table_is_supported(header_text, column_names)
    table = pd.DataFrame(points, columns=column_names)
    _check_grid_is_rectangular(table)
    pressure_values = np.unique(table[PRESSURE_COLUMN].to_numpy())
    temperature_values = np.unique(table[TEMPERATURE_COLUMN].to_numpy())

    pressure_unit = _parse_unit(
        header_text, _PRESSURE_PATTERN, PRESSURE_UNIT_BY_LABEL, DEFAULT_PRESSURE_UNIT, "PRESSURE"
    )
    temperature_unit = _parse_unit(
        header_text,
        _TEMPERATURE_PATTERN,
        TEMPERATURE_UNIT_BY_LABEL,
        DEFAULT_TEMPERATURE_UNIT,
        "TEMPERATURE",
    )
    return PvtTableData(
        name=_parse_table_name(meaningful_lines[0], default_name),
        pressures=Array(list(pressure_values), pressure_unit),
        temperatures=Array(list(temperature_values), temperature_unit),
        table=table,
        layout=PvtTableFileLayout(header_lines=header_lines, newline=_get_newline(content)),
    )
