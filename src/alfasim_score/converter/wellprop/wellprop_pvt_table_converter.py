import itertools
import numpy as np
import os
import pandas as pd
from barril.units import Array
from barril.units import Scalar
from dataclasses import dataclass
from enum import Enum
from io import StringIO
from pathlib import Path

from alfasim_score.common import PvtTableNumberOfPhases

# class WellPropPhase(Enum):
#     gas = "GAS"
#     liquid = "equivLIQUID"
#     water = "WATER"

# @dataclass
# class WellPropFile:
#     name: str
#     phase: WellPropPhase

#     def get_property_filename(self, property: str) -> str:
#         return "temperature_{self.phase}_{self.name}.csv"
# phases = ["GAS", "equivLIQUID", "WATER"]
# properties = ["conductivity", "cp", "density", "enthalpy", "interfacial_tension", "mass_fraction", "viscosity"]
# temperature_files = [f"temperature_{phase}_{property}.csv" for phase in phases for property in properties]

LABEL_NUMBER_OF_PHASES = "TWO"

WELLPROP_FILES = [
    "temperature_GAS_conductivity.csv",
    "temperature_GAS_cp.csv",
    "temperature_GAS_density.csv",
    "temperature_GAS_enthalpy.csv",
    "temperature_GAS_interfacial_tension.csv",
    "temperature_GAS_mass_fraction.csv",
    "temperature_GAS_viscosity.csv",
    "temperature_equivLIQUID_conductivity.csv",
    "temperature_equivLIQUID_cp.csv",
    "temperature_equivLIQUID_density.csv",
    "temperature_equivLIQUID_enthalpy.csv",
    "temperature_equivLIQUID_interfacial_tension.csv",
    "temperature_equivLIQUID_mass_fraction.csv",
    "temperature_equivLIQUID_viscosity.csv",
    "temperature_WATER_conductivity.csv",
    "temperature_WATER_cp.csv",
    "temperature_WATER_density.csv",
    "temperature_WATER_enthalpy.csv",
    "temperature_WATER_interfacial_tension.csv",
    "temperature_WATER_mass_fraction.csv",
    "temperature_WATER_viscosity.csv",
]


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


@dataclass
class PvtTableData:
    name: str
    pressures: Array
    temperatures: Array
    table: pd.DataFrame


class WellpropToPvtConverter:
    wellprop_folder: str
    pvt_filename: str
    dataframe: pd.DataFrame

    def __init__(self, wellprop_folder: str = "", pvt_filename: str = "") -> None:
        self.wellprop_folder = wellprop_folder
        self.pvt_filename = pvt_filename

    def read_wellprop_files(self) -> None:
        """
        Read wellprop files.
        """
        self.dataframes = {}
        for file in WELLPROP_FILES:

            filename = os.path.join(self.wellprop_folder, file)
            dataframe_name = os.path.splitext(file)[0].replace("temperature_", "")
            if os.path.isfile(filename):
                self.dataframes[dataframe_name] = pd.read_csv(filename, index_col=0)
            else:
                self.dataframes[dataframe_name] = pd.DataFrame(index=[], columns=[], data=[])

    def calculate_derivatives(
        self, densities: np.ndarray, pressures: np.ndarray, temperatures: np.ndarray
    ) -> tuple:
        """
        Calculate the pressure and temperature derivatives for the densities.
        """
        # Initialize derivative arrays
        densities_dp = np.zeros_like(densities)
        densities_dt = np.zeros_like(densities)

        # Central differences for pressure
        for i in range(1, len(pressures) - 1):
            dp = pressures[i + 1] - pressures[i - 1]
            densities_dp[i, :] = (densities[i + 1, :] - densities[i - 1, :]) / dp

        # Forward difference for the first pressure point
        dp_first = pressures[1] - pressures[0]
        densities_dp[0, :] = (densities[1, :] - densities[0, :]) / dp_first

        # Backward difference for the last pressure point
        dp_last = pressures[-1] - pressures[-2]
        densities_dp[-1, :] = (densities[-1, :] - densities[-2, :]) / dp_last

        # Central differences for temperature
        for j in range(1, len(temperatures) - 1):
            dt = temperatures[j + 1] - temperatures[j - 1]
            densities_dt[:, j] = (densities[:, j + 1] - densities[:, j - 1]) / dt

        # Forward difference for the first temperature point
        dt_first = temperatures[1] - temperatures[0]
        densities_dt[:, 0] = (densities[:, 1] - densities[:, 0]) / dt_first

        # Backward difference for the last temperature point
        dt_last = temperatures[-1] - temperatures[-2]
        densities_dt[:, -1] = (densities[:, -1] - densities[:, -2]) / dt_last

        return densities_dp, densities_dt

    def convert_pvt_table_data(self) -> pd.DataFrame:
        """
        Convert the data from wellprop tables into PVT tab file format.
        """
        temperatures = self.dataframes["GAS_cp"].columns.astype(float) - 273.15
        pressures = self.dataframes["GAS_cp"].index.astype(float)
        number_of_points = len(temperatures) * len(pressures)
        properties = {}
        liquid_densities = self.dataframes["equivLIQUID_density"].values
        gas_densities = self.dataframes["GAS_density"].values

        # Initialize derivative arrays
        liquid_densities_dp = np.zeros_like(liquid_densities)
        liquid_densities_dt = np.zeros_like(liquid_densities)
        gas_densities_dp = np.zeros_like(gas_densities)
        gas_densities_dt = np.zeros_like(gas_densities)

        liquid_densities_dp, liquid_densities_dt = self.calculate_derivatives(
            liquid_densities, pressures, temperatures
        )
        gas_densities_dp, gas_densities_dt = self.calculate_derivatives(
            gas_densities, pressures, temperatures
        )

        liquid_densities_dp = liquid_densities_dp.flatten()
        liquid_densities_dt = liquid_densities_dt.flatten()
        gas_densities_dp = gas_densities_dp.flatten()
        gas_densities_dt = gas_densities_dt.flatten()

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

        properties[PvtTableProperties.LiquidDensity.value] = np.array(liquid_densities)
        properties[PvtTableProperties.LiquidDensityDP.value] = np.array(liquid_densities_dp)
        properties[PvtTableProperties.LiquidDensityDT.value] = np.array(liquid_densities_dt)
        properties[PvtTableProperties.GasDensity.value] = np.array(gas_densities)
        properties[PvtTableProperties.GasDensityDP.value] = np.array(gas_densities_dp)
        properties[PvtTableProperties.GasDensityDT.value] = np.array(gas_densities_dt)
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
        properties[PvtTableProperties.GasSpecificEnthalpy.value] = np.array(
            gas_constants["specific_enthalpy"]
        )
        properties[PvtTableProperties.LiquidSpecificEnthalpy.value] = np.array(
            liquid_constants["specific_enthalpy"]
        )
        properties[PvtTableProperties.GasThermalConductivity.value] = np.array(
            gas_constants["conductivity"]
        )
        properties[PvtTableProperties.LiquidThermalConductivity.value] = np.array(
            liquid_constants["conductivity"]
        )
        properties[PvtTableProperties.GasLiquidSurfaceTension.value] = np.array(
            [Scalar(0.0, "N/m").GetValue("N/m")] * number_of_points
        )
        for key, value in properties.items():
            if not value.size:
                properties[key] = np.zeros(number_of_points)

        return PvtTableData(
            name=self.pvt_filename,
            pressures=Array(list(pressures), "Pa"),
            temperatures=Array(list(temperatures), "degC"),
            table=pd.concat(
                [
                    pd.DataFrame(
                        list(itertools.product(pressures, temperatures)), columns=["PT", "TM"]
                    ),
                    pd.DataFrame(
                        properties, columns=[property.value for property in PvtTableProperties]
                    ),
                ],
                axis=1,
            ),
        )

    def generate_pvt_table_content(self, pvt_table_data: PvtTableData) -> StringIO:
        format_numbers = lambda number: "{:.6e}".format(number)
        file_buffer = StringIO(f"{pvt_table_data.name}.tab")
        file_buffer.write(
            f'PVTTABLE LABEL = "{pvt_table_data.name}", PHASE = {LABEL_NUMBER_OF_PHASES},\n'
        )
        file_buffer.write(f"STDPRESSURE = 1.000000e+00 ATM,\\\n")
        file_buffer.write(f"STDTEMPERATURE = 2.887100e+02 K,\\\n")
        file_buffer.write(
            "PRESSURE = ({}) Pa,\\\n".format(
                ", ".join(map(format_numbers, pvt_table_data.pressures.GetValues("Pa")))
            )
        )
        file_buffer.write(
            "TEMPERATURE = ({}) C,\\\n".format(
                ", ".join(map(format_numbers, pvt_table_data.temperatures.GetValues("degC")))
            )
        )
        file_buffer.write("COLUMNS = ({})\n".format(", ".join(pvt_table_data.table.columns)))
        for _, row in pvt_table_data.table.iterrows():
            file_buffer.write(
                f"PVTTABLE POINT = ({', '.join(map(format_numbers, row.tolist()))})\n"
            )
        return file_buffer
