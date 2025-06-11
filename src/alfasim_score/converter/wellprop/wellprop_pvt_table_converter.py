from typing import Dict
from typing import Tuple

import itertools
import numpy as np
import pandas as pd
from barril.units import Array
from barril.units import Scalar
from dataclasses import dataclass
from enum import Enum
from io import StringIO
from pathlib import Path

from alfasim_score.converter.wellprop.utils import numeric_difference_1d

LABEL_NUMBER_OF_PHASES = "TWO"
STDPRESSURE = Scalar(1.0, "atm")
STDTEMPERATURE = Scalar(2.887100e02, "K")

WELLPROP_FILES = [
    "GAS_conductivity.csv",
    "GAS_cp.csv",
    "GAS_density.csv",
    "GAS_enthalpy.csv",
    "GAS_interfacial_tension.csv",
    "GAS_mass_fraction.csv",
    "GAS_viscosity.csv",
    "equivLIQUID_conductivity.csv",
    "equivLIQUID_cp.csv",
    "equivLIQUID_density.csv",
    "equivLIQUID_enthalpy.csv",
    "equivLIQUID_interfacial_tension.csv",
    "equivLIQUID_mass_fraction.csv",
    "equivLIQUID_viscosity.csv",
    "WATER_conductivity.csv",
    "WATER_cp.csv",
    "WATER_density.csv",
    "WATER_enthalpy.csv",
    "WATER_interfacial_tension.csv",
    "WATER_mass_fraction.csv",
    "WATER_viscosity.csv",
    "MIXTURE_temperature.csv",
]


class PvtTableType(Enum):
    """
    Whether the PVT table is based on specified
    pressure and temperature (PT) or
    pressure and enthalpy (PH).
    """

    PT = 1
    PH = 2


class PvtTableProperties(Enum):
    GasDensity = "ROG"
    LiquidDensity = "ROHL"
    GasDensityDP = "DROGDP"
    LiquidDensityDP = "DROHLDP"
    GasDensityDT = "DROGDT"
    LiquidDensityDT = "DROHLDT"
    GasDensityDT_constP = "DROGDTP"
    LiquidDensityDT_constP = "DROHLDTP"
    GasDensityDP_constT = "DROGDPT"
    LiquidDensityDP_constT = "DROHLDPT"
    GasDensityDP_constH = "DROGDPH"
    LiquidDensityDP_constH = "DROHLDPH"
    GasDensityDH_constP = "DROGDHP"
    LiquidDensityDH_constP = "DROHLDHP"
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
    TemperaturesM = "TM"  # FIXME: find the real meaning


@dataclass
class PvtTableData:
    name: str
    pressures: Array
    temperatures: Array
    enthalpies: Array
    table: pd.DataFrame


class WellpropToPvtConverter:
    def __init__(self, wellprop_folder: Path) -> None:
        # FIXME: get from user
        self.pvt_type = PvtTableType.PH
        self.wellprop_folder = wellprop_folder
        self.pvt_filename = wellprop_folder.name
        self.dataframes = self._read_wellprop_files()

    def _read_wellprop_files(self) -> Dict[str, pd.DataFrame]:
        """
        Read wellprop csv files.
        """
        dataframes = {}
        for filename in WELLPROP_FILES:
            pvt_type_identifier = (
                "temperature_" if self.pvt_type == PvtTableType.PT else "enthalpy_"
            )
            filepath = Path(self.wellprop_folder) / (pvt_type_identifier + filename)
            dataframe_name = Path(filename).stem
            if Path(filepath).exists():
                dataframes[dataframe_name] = pd.read_csv(filepath, index_col=0)
            else:
                dataframes[dataframe_name] = pd.DataFrame(index=[], columns=[], data=[])
        return dataframes

    def _calculate_derivatives_PT(
        self,
        pressures: np.ndarray[tuple[int], np.dtype[float]],
        temperatures: np.ndarray[tuple[int], np.dtype[float]],
        densities: np.ndarray[tuple[int, int], np.dtype[float]],
    ) -> dict["str", np.ndarray[tuple[int], np.dtype[float]]]:
        """
        Calculate the pressure and temperature derivatives for the densities.
        """
        # Initialize derivative arrays
        dro_dP_T = np.full_like(
            densities, np.nan, dtype=float
        )  # density derivative wrt pressure, constant temperature
        dro_dT_P = np.full_like(
            densities, np.nan, dtype=float
        )  # density derivative wrt temperature, constant pressure

        for i in range(len(pressures)):
            dro_dP_T[:, i] = numeric_difference_1d(densities[:, i], pressures)
        for j in range(len(temperatures)):
            dro_dT_P[j, :] = numeric_difference_1d(densities[j, :], temperatures)

        derivatives = {
            "dro_dP_T": dro_dP_T.flatten(),
            "dro_dT_P": dro_dT_P.flatten(),
        }
        return derivatives

    def _calculate_derivatives_PH(
        self,
        pressures: np.ndarray[tuple[int], np.dtype[float]],
        enthalpies: np.ndarray[tuple[int], np.dtype[float]],
        densities: np.ndarray[tuple[int, int], np.dtype[float]],
        temperatures: np.ndarray[tuple[int, int], np.dtype[float]],
        zero_tolerance: float = 1e-12,
    ) -> dict[str, np.ndarray[tuple[int], np.dtype[float]]]:
        """
        Calculates density derivatives with respect to pressure (at constant temperature and enthalpy)
        temperature (at constant pressure) and enthalpy (at constant pressure)from a table where
        density and temperature are functions of pressure and enthalpy.

        :param pressures: 1D array of pressure values.
        :param enthalpies: 1D array of enthalpy values.
        :param densities: 2D array of density values (rows=pressure, cols=enthalpy).
        :param temperatures: 2D array of temperature values (rows=pressure, cols=enthalpy).
        :param zero_tolerance: A small value to consider a denominator as zero for division handling.

        :return:
            A dictionary containing four numpy arrays in a flatten view:
                - dro_dT_P: Density derivative wrt Temperature (at constant Pressure)
                - dro_dP_T: Density derivative wrt Pressure (at constant Temperature)
                - dro_dP_T: Density derivative wrt Pressure (at constant Temperature)
                - dro_dP_T: Density derivative wrt Pressure (at constant Temperature)
                Returns NaN where derivatives cannot be computed due to insufficient data
                or division by near-zero denominators.

        :raises:
            ValueError: If input array dimensions do not match.
        """
        # Validate input dimensions
        num_P = len(pressures)
        num_h = len(enthalpies)

        if np.shape(densities) != (num_P, num_h) or np.shape(temperatures) != (num_P, num_h):
            raise ValueError(
                f"Dimension mismatch: pressure({num_P}), enthalpy({num_h}). "
                f"density.shape={densities.shape}, temperature.shape={temperatures.shape}. "
                "Expected density and temperature shapes to be (len(pressure), len(enthalpy))."
            )

        # Initialize matrices for the base partial derivatives
        # These will have the same shape as density/temperature
        # The last two are intermediate values that will not be exported
        dro_dT_P = np.full_like(
            densities, np.nan, dtype=float
        )  # density derivative wrt temperature, constant pressure
        dro_dP_T = np.full_like(
            densities, np.nan, dtype=float
        )  # density derivative wrt pressure, constant temperature
        dro_dP_h = np.full_like(
            densities, np.nan, dtype=float
        )  # density derivative wrt pressure, constant enthalpy
        dro_dh_P = np.full_like(
            densities, np.nan, dtype=float
        )  # density derivative wrt enthalpy, constant pressure
        dT_dP_h = np.full_like(
            temperatures, np.nan, dtype=float
        )  # temperature derivative wrt pressure, constant enthalpy
        dT_dh_P = np.full_like(
            temperatures, np.nan, dtype=float
        )  # temperature derivate wrt enthalpy, constant pressure

        for j in range(num_h):  # Iterate over enthalpy columns (h is constant)
            dro_dP_h[:, j] = numeric_difference_1d(
                densities[:, j], pressures, tolerance=zero_tolerance
            )
            dT_dP_h[:, j] = numeric_difference_1d(
                temperatures[:, j], pressures, tolerance=zero_tolerance
            )

        for i in range(num_P):  # Iterate over pressure rows (P is constant)
            dro_dh_P[i, :] = numeric_difference_1d(
                densities[i, :], enthalpies, tolerance=zero_tolerance
            )
            dT_dh_P[i, :] = numeric_difference_1d(
                temperatures[i, :], enthalpies, tolerance=zero_tolerance
            )

        # --- Now apply the chain rule formulas ---

        # Handle division by zero for dT_dh_P, which is in the denominator of both formulas
        valid_divisor_mask = np.abs(dT_dh_P) > zero_tolerance

        # Formula 1: (∂D/∂T)_P = (∂D/∂h)_P / (∂T/∂h)_P
        dro_dT_P[valid_divisor_mask] = dro_dh_P[valid_divisor_mask] / dT_dh_P[valid_divisor_mask]

        # Formula 2: (∂D/∂P)_T = (∂D/∂P)_h - [(∂D/∂h)_P * (∂T/∂P)_h] / (∂T/∂h)_P
        numerator_for_subtraction = dro_dh_P * dT_dP_h
        term_to_subtract = np.full_like(densities, np.nan, dtype=float)
        term_to_subtract[valid_divisor_mask] = (
            numerator_for_subtraction[valid_divisor_mask] / dT_dh_P[valid_divisor_mask]
        )

        dro_dP_T = dro_dP_h - term_to_subtract

        derivatives = {
            "dro_dT_P": dro_dT_P.flatten(),
            "dro_dP_T": dro_dP_T.flatten(),
            "dro_dP_h": dro_dP_h.flatten(),
            "dro_dh_P": dro_dh_P.flatten(),
        }
        return derivatives

    def _convert_pvt_table_data(self) -> pd.DataFrame:
        """
        Convert the data from wellprop tables into PVT tab file format.
        """
        pressures = self.dataframes["GAS_cp"].index.astype(float)
        temperatures = self.dataframes["GAS_cp"].columns.astype(float) - 273.15
        liquid_densities = self.dataframes["equivLIQUID_density"].values
        gas_densities = self.dataframes["GAS_density"].values
        if self.pvt_type == PvtTableType.PH:
            enthalpies = self.dataframes["GAS_cp"].columns.astype(float)
            temperatures = (
                self.dataframes["MIXTURE_temperature"].values - 273.15
            )  # FIXME: check if this is correct
        number_of_points = len(pressures) * (
            len(temperatures) if self.pvt_type == PvtTableType.PT else len(enthalpies)
        )

        if self.pvt_type == PvtTableType.PT:
            liquid_density_derivatives = self._calculate_derivatives_PT(
                pressures, temperatures, liquid_densities
            )
            gas_density_derivatives = self._calculate_derivatives_PT(
                pressures,
                temperatures,
                gas_densities,
            )

            liquid_densities_dP = liquid_density_derivatives["dro_dP_T"]
            liquid_densities_dT = liquid_density_derivatives["dro_dT_P"]
            gas_densities_dP = gas_density_derivatives["dro_dP_T"]
            gas_densities_dT = gas_density_derivatives["dro_dT_P"]
        else:
            liquid_density_derivatives = self._calculate_derivatives_PH(
                pressures, enthalpies, gas_densities, temperatures
            )
            gas_density_derivatives = self._calculate_derivatives_PH(
                pressures, enthalpies, liquid_densities, temperatures
            )

            liquid_densities_dP_T = liquid_density_derivatives["dro_dP_T"]
            liquid_densities_dT_P = liquid_density_derivatives["dro_dT_P"]
            liquid_densities_dP_h = liquid_density_derivatives["dro_dP_h"]
            liquid_densities_dh_P = liquid_density_derivatives["dro_dh_P"]
            gas_densities_dP_T = gas_density_derivatives["dro_dP_T"]
            gas_densities_dT_P = gas_density_derivatives["dro_dT_P"]
            gas_densities_dP_h = gas_density_derivatives["dro_dP_h"]
            gas_densities_dh_P = gas_density_derivatives["dro_dh_P"]

        liquid_densities = liquid_densities.flatten()
        gas_densities = gas_densities.flatten()
        gas_constants = {
            "mass_fraction": self.dataframes["GAS_mass_fraction"].values.astype(float).flatten(),
            "viscosity": self.dataframes["GAS_viscosity"].values.astype(float).flatten(),
            "specific_heat": self.dataframes["GAS_cp"].values.astype(float).flatten(),
            "specific_enthalpy": self.dataframes["GAS_enthalpy"].values.astype(float).flatten(),
            "conductivity": self.dataframes["GAS_conductivity"].values.astype(float).flatten(),
        }

        liquid_constants = {
            "viscosity": self.dataframes["equivLIQUID_viscosity"].values.astype(float).flatten(),
            "specific_heat": self.dataframes["equivLIQUID_cp"].values.astype(float).flatten(),
            "specific_enthalpy": self.dataframes["equivLIQUID_enthalpy"]
            .values.astype(float)
            .flatten(),
            "conductivity": self.dataframes["equivLIQUID_conductivity"]
            .values.astype(float)
            .flatten(),
        }

        mixture_constants = {
            "temperature": self.dataframes["MIXTURE_temperature"].values.astype(float).flatten(),
        }

        # Fill properties dict
        properties = {}
        properties[PvtTableProperties.LiquidDensity.value] = np.array(liquid_densities)
        properties[PvtTableProperties.GasDensity.value] = np.array(gas_densities)
        if self.pvt_type == PvtTableType.PT:
            properties[PvtTableProperties.LiquidDensityDP.value] = np.array(liquid_densities_dP)
            properties[PvtTableProperties.LiquidDensityDT.value] = np.array(liquid_densities_dT)
            properties[PvtTableProperties.GasDensityDP.value] = np.array(gas_densities_dP)
            properties[PvtTableProperties.GasDensityDT.value] = np.array(gas_densities_dT)
        else:
            properties[PvtTableProperties.GasDensityDP_constT.value] = np.array(gas_densities_dP_T)
            properties[PvtTableProperties.GasDensityDT_constP.value] = np.array(gas_densities_dT_P)
            properties[PvtTableProperties.GasDensityDP_constH.value] = np.array(gas_densities_dP_h)
            properties[PvtTableProperties.GasDensityDH_constP.value] = np.array(gas_densities_dh_P)
            properties[PvtTableProperties.LiquidDensityDP_constT.value] = np.array(
                liquid_densities_dP_T
            )
            properties[PvtTableProperties.LiquidDensityDT_constP.value] = np.array(
                liquid_densities_dT_P
            )
            properties[PvtTableProperties.LiquidDensityDP_constH.value] = np.array(
                liquid_densities_dP_h
            )
            properties[PvtTableProperties.LiquidDensityDH_constP.value] = np.array(
                liquid_densities_dh_P
            )

        properties[PvtTableProperties.GasMassFraction.value] = np.array(
            gas_constants["mass_fraction"]
        )
        properties[PvtTableProperties.GasViscosity.value] = np.array(gas_constants["viscosity"])
        properties[PvtTableProperties.LiquidViscosity.value] = np.array(
            liquid_constants["viscosity"]
        )
        properties[PvtTableProperties.GasSpecificHeat.value] = np.array(
            gas_constants["specific_heat"]
        )
        properties[PvtTableProperties.LiquidSpecificHeat.value] = np.array(
            liquid_constants["specific_heat"]
        )
        if self.pvt_type == PvtTableType.PT:
            properties[PvtTableProperties.GasSpecificEnthalpy.value] = np.array(
                gas_constants["specific_enthalpy"]
            )
            properties[PvtTableProperties.LiquidSpecificEnthalpy.value] = np.array(
                liquid_constants["specific_enthalpy"]
            )
        else:
            properties[PvtTableProperties.GasSpecificEnthalpy.value] = np.full_like(
                gas_densities, 1e-06, float
            )
            properties[PvtTableProperties.LiquidSpecificEnthalpy.value] = np.full_like(
                liquid_densities, 1e-06, float
            )

        # assert 0
        properties[PvtTableProperties.GasThermalConductivity.value] = np.array(
            gas_constants["conductivity"]
        )
        properties[PvtTableProperties.LiquidThermalConductivity.value] = np.array(
            liquid_constants["conductivity"]
        )
        properties[PvtTableProperties.GasLiquidSurfaceTension.value] = np.array(
            [Scalar(0.0, "N/m").GetValue("N/m")] * number_of_points
        )
        if self.pvt_type == PvtTableType.PH:
            properties[PvtTableProperties.TemperaturesM.value] = np.array(
                mixture_constants["temperature"]
            )
        for key, value in properties.items():
            if not value.size:
                properties[key] = np.zeros(number_of_points)

        thetas = temperatures if self.pvt_type == PvtTableType.PT else enthalpies
        theta_table_name = "TM" if self.pvt_type == PvtTableType.PT else "HTOT"
        # print("Properties:", properties)
        return PvtTableData(
            name=self.pvt_filename,
            pressures=Array(list(pressures), "Pa"),
            temperatures=Array(list(temperatures), "degC"),
            enthalpies=(
                Array(list(enthalpies), "J/kg")
                if self.pvt_type == PvtTableType.PH
                else Array([], "J/kg")
            ),
            table=pd.concat(
                [
                    pd.DataFrame(
                        list(itertools.product(pressures, thetas)), columns=["PT", theta_table_name]
                    ),
                    pd.DataFrame(
                        properties, columns=[property.value for property in PvtTableProperties]
                    ),
                ],
                axis=1,
            ),
        )

    def _generate_pvt_table_content(self, pvt_table_data: PvtTableData) -> StringIO:
        format_numbers = lambda number: "{:.6e}".format(number)
        file_buffer = StringIO(f"{pvt_table_data.name}.tab")
        file_buffer.write(
            f'PVTTABLE LABEL = "{pvt_table_data.name}", PHASE = {LABEL_NUMBER_OF_PHASES},\n'
        )
        if self.pvt_type == PvtTableType.PH:
            file_buffer.write(f"PVTFORMULATION = PH,\\\n")
        file_buffer.write(
            "STDPRESSURE = {} ATM,\\\n".format(format_numbers(STDPRESSURE.GetValue("atm")))
        )
        file_buffer.write(
            "STDTEMPERATURE = {} K,\\\n".format(format_numbers(STDTEMPERATURE.GetValue("K")))
        )
        file_buffer.write(
            "PRESSURE = ({}) Pa,\\\n".format(
                ", ".join(map(format_numbers, pvt_table_data.pressures.GetValues("Pa")))
            )
        )
        if self.pvt_type == PvtTableType.PT:
            file_buffer.write(
                "TEMPERATURE = ({}) C,\\\n".format(
                    ", ".join(map(format_numbers, pvt_table_data.temperatures.GetValues("degC")))
                )
            )
        else:
            file_buffer.write(
                "NOENTHALPY = (50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50),\\\n"
            )
        file_buffer.write("COLUMNS = ({})\n".format(", ".join(pvt_table_data.table.columns)))
        for _, row in pvt_table_data.table.iterrows():
            file_buffer.write(
                f"PVTTABLE POINT = ({', '.join(map(format_numbers, row.tolist()))})\n"
            )
        return file_buffer

    def generate_pvt_table_file(self, destiny_folder: Path) -> None:
        """Create a pvt table file with data from welprop csv files."""
        pvt_data = self._convert_pvt_table_data()
        content = self._generate_pvt_table_content(pvt_data)
        with open(destiny_folder / f"{pvt_data.name}.tab", "w") as file:
            file.write(content.getvalue())
