from typing import Any
from typing import Optional

import numpy as np
import pandas as pd
from dataclasses import dataclass
from dataclasses import field
from dataclasses import replace
from enum import Enum
from pathlib import Path

from alfasim_score.converter.pvt_table.pvt_table_file import FIXED_TABLE_COMMENT
from alfasim_score.converter.pvt_table.pvt_table_file import PRESSURE_COLUMN
from alfasim_score.converter.pvt_table.pvt_table_file import TEMPERATURE_COLUMN
from alfasim_score.converter.pvt_table.pvt_table_file import PvtTableData
from alfasim_score.converter.pvt_table.pvt_table_file import PvtTableError
from alfasim_score.converter.pvt_table.pvt_table_file import PvtTableProperties
from alfasim_score.converter.pvt_table.pvt_table_file import read_pvt_table_file
from alfasim_score.converter.pvt_table.pvt_table_file import write_pvt_table_file


class PvtTablePhase(str, Enum):
    GAS = "GAS"
    LIQUID = "LIQUID"


# Properties of the gas phase and their counterpart in the liquid phase, copied when a phase does
# not exist anywhere in the table. The whole density field is copied from the other phase, so its
# derivatives are copied along with it.
GAS_LIQUID_PROPERTY_PAIRS = (
    (PvtTableProperties.GasDensity.value, PvtTableProperties.LiquidDensity.value),
    (PvtTableProperties.GasDensityDP.value, PvtTableProperties.LiquidDensityDP.value),
    (PvtTableProperties.GasDensityDT.value, PvtTableProperties.LiquidDensityDT.value),
    (PvtTableProperties.GasViscosity.value, PvtTableProperties.LiquidViscosity.value),
    (PvtTableProperties.GasSpecificHeat.value, PvtTableProperties.LiquidSpecificHeat.value),
    (PvtTableProperties.GasSpecificEnthalpy.value, PvtTableProperties.LiquidSpecificEnthalpy.value),
    (
        PvtTableProperties.GasThermalConductivity.value,
        PvtTableProperties.LiquidThermalConductivity.value,
    ),
)

# Properties filled in the points where the phase does not exist. The density derivatives are
# deliberately left as they are, because the filled density is constant over the filled points, so a
# derivative of zero is exactly what it should be.
FILLED_PROPERTY_PAIRS = (
    (PvtTableProperties.GasDensity.value, PvtTableProperties.LiquidDensity.value),
    (PvtTableProperties.GasViscosity.value, PvtTableProperties.LiquidViscosity.value),
    (PvtTableProperties.GasSpecificHeat.value, PvtTableProperties.LiquidSpecificHeat.value),
    (PvtTableProperties.GasSpecificEnthalpy.value, PvtTableProperties.LiquidSpecificEnthalpy.value),
    (
        PvtTableProperties.GasThermalConductivity.value,
        PvtTableProperties.LiquidThermalConductivity.value,
    ),
)

DENSITY_COLUMN_BY_PHASE = {
    PvtTablePhase.GAS: PvtTableProperties.GasDensity.value,
    PvtTablePhase.LIQUID: PvtTableProperties.LiquidDensity.value,
}
GAS_MASS_FRACTION_COLUMN = PvtTableProperties.GasMassFraction.value
SURFACE_TENSION_COLUMN = PvtTableProperties.GasLiquidSurfaceTension.value

# The pressure and the temperature identify the point, the gas mass fraction tells which phases
# exist (and must be kept as it is, so that a filled phase is never actually used by ALFAsim) and
# the gas-liquid surface tension has no counterpart in a single phase table.
NOT_FIXABLE_COLUMNS = (
    PRESSURE_COLUMN,
    TEMPERATURE_COLUMN,
    GAS_MASS_FRACTION_COLUMN,
    SURFACE_TENSION_COLUMN,
)

# Properties that are not allowed to be negative. The values out of these bounds are discarded
# before filling the missing points, so that the artifacts calculated on the phase boundary are not
# propagated over the table.
#
# The specific enthalpy has an arbitrary reference and the density derivatives have no bound: the
# derivative with respect to the pressure is checked because a fluid cannot expand when compressed,
# but the derivative with respect to the temperature is not, since water between 0 and 4 degC gets
# denser as the temperature grows.
NON_NEGATIVE_COLUMNS = frozenset(
    {
        PvtTableProperties.GasDensity.value,
        PvtTableProperties.LiquidDensity.value,
        PvtTableProperties.GasDensityDP.value,
        PvtTableProperties.LiquidDensityDP.value,
        PvtTableProperties.GasViscosity.value,
        PvtTableProperties.LiquidViscosity.value,
        PvtTableProperties.GasSpecificHeat.value,
        PvtTableProperties.LiquidSpecificHeat.value,
        PvtTableProperties.GasThermalConductivity.value,
        PvtTableProperties.LiquidThermalConductivity.value,
    }
)


@dataclass(frozen=True)
class PvtTablePhaseIssue:
    """A phase that does not exist in some (or all) points of the table and how it was filled."""

    phase: PvtTablePhase
    absent_points: int
    total_points: int
    is_fully_absent: bool
    fixed_columns: list[str] = field(default_factory=list)
    discarded_out_of_bound_columns: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert the issue to a dict in order to be used in regression tests."""
        return {
            "phase": self.phase.value,
            "absent_points": self.absent_points,
            "total_points": self.total_points,
            "is_fully_absent": self.is_fully_absent,
            "fixed_columns": list(self.fixed_columns),
            "discarded_out_of_bound_columns": dict(self.discarded_out_of_bound_columns),
        }


@dataclass(frozen=True)
class PvtTableCheckResult:
    """Result of checking a pvt table, listing what has to be fixed and what is only reported."""

    table_name: str
    number_of_points: int
    phase_issues: list[PvtTablePhaseIssue] = field(default_factory=list)
    zeroed_columns: list[str] = field(default_factory=list)
    out_of_bound_columns: dict[str, int] = field(default_factory=dict)
    inconsistent_mass_fraction_points: int = 0

    @property
    def has_issues(self) -> bool:
        """Whether the table has a phase that does not exist and therefore has to be fixed."""
        return bool(self.phase_issues)

    def to_dict(self) -> dict[str, Any]:
        """Convert the result to a dict in order to be used in regression tests."""
        return {
            "table_name": self.table_name,
            "number_of_points": self.number_of_points,
            "phase_issues": [issue.to_dict() for issue in self.phase_issues],
            "zeroed_columns": list(self.zeroed_columns),
            "out_of_bound_columns": dict(self.out_of_bound_columns),
            "inconsistent_mass_fraction_points": self.inconsistent_mass_fraction_points,
        }

    def describe(self) -> str:
        """Describe the result of the check in a report to be shown to the user."""
        lines = [f"PVT table '{self.table_name}' ({self.number_of_points} points)"]
        if not self.phase_issues:
            lines.append("  All the phases exist in every point, there is nothing to fix.")
        for issue in self.phase_issues:
            percentage = 100.0 * issue.absent_points / issue.total_points
            lines.append(
                f"  {issue.phase.value} phase does not exist in {issue.absent_points} of "
                f"{_format_number_of_points(issue.total_points)} ({percentage:.1f}%)"
            )
            if issue.is_fully_absent:
                lines.append(
                    "    the phase does not exist anywhere, its properties were copied from the "
                    "other phase"
                )
            lines.append(f"    filled columns: {', '.join(issue.fixed_columns)}")
            for column, points in issue.discarded_out_of_bound_columns.items():
                lines.append(
                    f"    {column} was out of the physical bounds in "
                    f"{_format_number_of_points(points)} and was filled again"
                )
        if self.zeroed_columns:
            lines.append(
                "  Columns of an existing phase that are zero in every point (reported only, they "
                f"are not fixed): {', '.join(self.zeroed_columns)}"
            )
        for column, points in self.out_of_bound_columns.items():
            lines.append(
                f"  {column} is out of the physical bounds in {_format_number_of_points(points)} "
                "of an existing phase (reported only, it is not fixed)"
            )
        if self.inconsistent_mass_fraction_points:
            lines.append(
                f"  {GAS_MASS_FRACTION_COLUMN} does not agree with the densities in "
                f"{_format_number_of_points(self.inconsistent_mass_fraction_points)}"
            )
        return "\n".join(lines)


def _format_number_of_points(number_of_points: int) -> str:
    """Format a number of points of the table to be shown to the user."""
    return f"{number_of_points} point" if number_of_points == 1 else f"{number_of_points} points"


def _get_out_of_bound_points(column: str, values: np.ndarray) -> np.ndarray:
    """Get the points in which the values of a column are out of its physical bounds."""
    if column in NON_NEGATIVE_COLUMNS:
        return np.asarray(values < 0.0)
    return np.zeros(len(values), dtype=bool)


def _fill_at_fixed_condition(
    frame: pd.DataFrame, fixed_column: str, columns_to_fill: list[str]
) -> None:
    """
    Fill the missing values of the columns using the previous (or the next) value of the sequence
    of points in which the fixed column has the same value.

    The lines in which the column has no value at all are skipped, so that they can still be filled
    in the other direction.
    """
    fixed_values = frame[fixed_column].to_numpy()
    for value in np.unique(fixed_values):
        is_at_value = np.isclose(fixed_values, value)
        for column in columns_to_fill:
            values_at_condition = frame.loc[is_at_value, column]
            is_missing = values_at_condition.isna().to_numpy()
            if is_missing.any() and not is_missing.all():
                frame.loc[is_at_value, column] = values_at_condition.ffill().bfill()


class PvtTableFixer:
    """
    Check and fix pvt tables in which the properties of a phase that does not exist in a point were
    written as zero, which ALFAsim is not able to use.

    The density, the viscosity, the specific heat and the thermal conductivity of the points in
    which the phase does not exist are filled with the value of the closest point in which the
    phase does exist, at the same pressure first and then at the same temperature. When the phase
    does not exist anywhere in the table, its properties are copied from the other phase instead.

    The gas mass fraction is never changed, so a filled phase keeps the fraction zero and is never
    actually used by ALFAsim.
    """

    def __init__(self, pvt_table_data: PvtTableData) -> None:
        self.pvt_table_data = pvt_table_data

    @classmethod
    def from_file(cls, pvt_table_filepath: Path) -> "PvtTableFixer":
        """Create a fixer for the pvt table of a file in the OLGA keyword format."""
        return cls(read_pvt_table_file(pvt_table_filepath))

    def check(self) -> PvtTableCheckResult:
        """Check the pvt table without changing it."""
        _, check_result = self._fix_table()
        return check_result

    def fix(self) -> tuple[PvtTableData, PvtTableCheckResult]:
        """Fix the pvt table, returning the fixed table and the result of the check."""
        table, check_result = self._fix_table()
        return replace(self.pvt_table_data, table=table), check_result

    def generate_fixed_pvt_table_file(self, output_filepath: Path) -> PvtTableCheckResult:
        """
        Fix the pvt table and write it to a file in the OLGA keyword format.

        A comment telling the file was fixed is written in the header of the file, but only when
        there was something to fix, so that a table that is already correct is written back
        unchanged.
        """
        fixed_pvt_table_data, check_result = self.fix()
        header_comments = (FIXED_TABLE_COMMENT,) if check_result.has_issues else ()
        write_pvt_table_file(fixed_pvt_table_data, output_filepath, header_comments)
        return check_result

    def _get_absent_points(self, table: pd.DataFrame, phase: PvtTablePhase) -> np.ndarray:
        """Get the points in which the phase does not exist, identified by a density of zero."""
        density_column = DENSITY_COLUMN_BY_PHASE[phase]
        if density_column not in table.columns:
            raise PvtTableError(f"The pvt table has no {density_column} column.")
        return np.asarray(table[density_column].to_numpy() <= 0.0)

    def _get_phase_columns(
        self,
        table: pd.DataFrame,
        phase: PvtTablePhase,
        property_pairs: tuple[tuple[str, str], ...] = GAS_LIQUID_PROPERTY_PAIRS,
    ) -> list[str]:
        """Get the columns of the table that hold properties of the phase and can be fixed."""
        index = 0 if phase is PvtTablePhase.GAS else 1
        return [
            columns[index]
            for columns in property_pairs
            if columns[index] in table.columns and columns[index] not in NOT_FIXABLE_COLUMNS
        ]

    def _copy_properties_from_other_phase(
        self, table: pd.DataFrame, phase: PvtTablePhase
    ) -> list[str]:
        """Copy the properties of the other phase into a phase that does not exist anywhere."""
        copied_columns = []
        for gas_column, liquid_column in GAS_LIQUID_PROPERTY_PAIRS:
            if phase is PvtTablePhase.GAS:
                target_column, source_column = gas_column, liquid_column
            else:
                target_column, source_column = liquid_column, gas_column
            if target_column in table.columns and source_column in table.columns:
                table[target_column] = table[source_column].to_numpy()
                copied_columns.append(target_column)
        return copied_columns

    def _fix_phase(self, table: pd.DataFrame, phase: PvtTablePhase) -> Optional[PvtTablePhaseIssue]:
        """Fix the properties of the points in which the phase does not exist."""
        absent_points = self._get_absent_points(table, phase)
        if not absent_points.any():
            return None
        columns_to_fix = self._get_phase_columns(table, phase, FILLED_PROPERTY_PAIRS)
        is_fully_absent = bool(absent_points.all())
        if is_fully_absent:
            other_phase = PvtTablePhase.LIQUID if phase is PvtTablePhase.GAS else PvtTablePhase.GAS
            if self._get_absent_points(table, other_phase).all():
                raise PvtTableError(
                    "Neither the gas nor the liquid phase exists in the pvt table, there is no "
                    "phase to copy the properties from."
                )
            return PvtTablePhaseIssue(
                phase=phase,
                absent_points=int(absent_points.sum()),
                total_points=len(table),
                is_fully_absent=True,
                fixed_columns=self._copy_properties_from_other_phase(table, phase),
            )
        return self._fill_absent_points(table, phase, absent_points, columns_to_fix)

    def _fill_absent_points(
        self,
        table: pd.DataFrame,
        phase: PvtTablePhase,
        absent_points: np.ndarray,
        columns_to_fix: list[str],
    ) -> PvtTablePhaseIssue:
        """Fill the points in which the phase does not exist with the values of the closest ones."""
        frame = table.sort_values([PRESSURE_COLUMN, TEMPERATURE_COLUMN], kind="stable")
        is_absent = np.asarray(pd.Series(absent_points, index=table.index).loc[frame.index])
        discarded_out_of_bound_columns = {}
        for column in columns_to_fix:
            values = frame[column].to_numpy(dtype=float).copy()
            is_out_of_bound = _get_out_of_bound_points(column, values) & ~is_absent
            if is_out_of_bound.any():
                discarded_out_of_bound_columns[column] = int(is_out_of_bound.sum())
            values[is_absent | is_out_of_bound] = np.nan
            frame[column] = values
        # The pressure is fixed first because the properties change much more with the pressure
        # than with the temperature, so filling along the temperature keeps the value of the point
        # at the same pressure, on the other side of the phase boundary.
        _fill_at_fixed_condition(frame, PRESSURE_COLUMN, columns_to_fix)
        _fill_at_fixed_condition(frame, TEMPERATURE_COLUMN, columns_to_fix)
        for column in columns_to_fix:
            if frame[column].isna().any():
                frame[column] = frame[column].ffill().bfill()
            if frame[column].isna().all():
                raise PvtTableError(
                    f"The column {column} has no value at all to fill the points in which the "
                    f"{phase.value} phase does not exist."
                )
        table.loc[:, columns_to_fix] = frame[columns_to_fix]
        return PvtTablePhaseIssue(
            phase=phase,
            absent_points=int(absent_points.sum()),
            total_points=len(table),
            is_fully_absent=False,
            fixed_columns=columns_to_fix,
            discarded_out_of_bound_columns=discarded_out_of_bound_columns,
        )

    def _get_columns_only_reported(
        self, table: pd.DataFrame, absent_points_by_phase: dict[PvtTablePhase, np.ndarray]
    ) -> tuple[list[str], dict[str, int]]:
        """
        Get the columns that look wrong but are not fixed: the ones of an existing phase that are
        zero in every point and the ones of an existing phase out of the physical bounds.

        A zero value is valid for some properties (the specific enthalpy has an arbitrary reference,
        for instance) and the properties of an existing phase are the data of the table itself, so
        both cases are reported to the user instead of being changed.
        """
        zeroed_columns = []
        out_of_bound_columns = {}
        for phase, absent_points in absent_points_by_phase.items():
            if absent_points.any():
                continue
            for column in self._get_phase_columns(table, phase):
                values = table[column].to_numpy(dtype=float)
                if not values.any():
                    zeroed_columns.append(column)
                number_of_out_of_bound = int(_get_out_of_bound_points(column, values).sum())
                if number_of_out_of_bound:
                    out_of_bound_columns[column] = number_of_out_of_bound
        if SURFACE_TENSION_COLUMN in table.columns:
            if not table[SURFACE_TENSION_COLUMN].to_numpy().any():
                zeroed_columns.append(SURFACE_TENSION_COLUMN)
        return zeroed_columns, out_of_bound_columns

    def _count_inconsistent_mass_fraction_points(self, table: pd.DataFrame) -> int:
        """
        Count the points in which the gas mass fraction does not agree with the densities.

        The gas mass fraction is expected to be zero where the gas does not exist and one where the
        liquid does not exist.
        """
        if GAS_MASS_FRACTION_COLUMN not in table.columns:
            return 0
        mass_fraction = table[GAS_MASS_FRACTION_COLUMN].to_numpy()
        is_gas_absent = self._get_absent_points(table, PvtTablePhase.GAS)
        is_liquid_absent = self._get_absent_points(table, PvtTablePhase.LIQUID)
        is_inconsistent = ((mass_fraction <= 0.0) != is_gas_absent) | (
            (mass_fraction >= 1.0) != is_liquid_absent
        )
        return int(is_inconsistent.sum())

    def _fix_table(self) -> tuple[pd.DataFrame, PvtTableCheckResult]:
        """Fix a copy of the table and report what was fixed and what was only reported."""
        original_table = self.pvt_table_data.table
        absent_points_by_phase = {
            phase: self._get_absent_points(original_table, phase) for phase in PvtTablePhase
        }
        zeroed_columns, out_of_bound_columns = self._get_columns_only_reported(
            original_table, absent_points_by_phase
        )
        inconsistent_mass_fraction_points = self._count_inconsistent_mass_fraction_points(
            original_table
        )
        table = original_table.copy()
        phase_issues = []
        for phase in PvtTablePhase:
            phase_issue = self._fix_phase(table, phase)
            if phase_issue is not None:
                phase_issues.append(phase_issue)
        check_result = PvtTableCheckResult(
            table_name=self.pvt_table_data.name,
            number_of_points=len(table),
            phase_issues=phase_issues,
            zeroed_columns=zeroed_columns,
            out_of_bound_columns=out_of_bound_columns,
            inconsistent_mass_fraction_points=inconsistent_mass_fraction_points,
        )
        return table, check_result
