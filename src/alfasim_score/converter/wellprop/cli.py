from typing import Optional
from typing import Sequence

import argparse
import sys
from pathlib import Path

from alfasim_score.converter.wellprop.wellprop_pvt_table_converter import WellpropToPvtConverter

EXIT_CODE_SUCCESS = 0
EXIT_CODE_INVALID_FOLDER = 3


def _create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="alfasim-score-convert-wellprop",
        description=(
            "Convert folders of WELLBOREPROPS csv files into pvt tables in the OLGA keyword "
            "format, named after the folder and already fixed for the phases that do not exist."
        ),
    )
    parser.add_argument(
        "wellprop_folders",
        metavar="WELLPROP_FOLDER",
        nargs="+",
        type=Path,
        help="the folders with the WELLBOREPROPS csv files",
    )
    parser.add_argument(
        "-o",
        "--output-folder",
        type=Path,
        help="where to write the pvt tables (default: inside each WELLBOREPROPS folder)",
    )
    return parser


def _convert_one_folder(wellprop_folder: Path, output_folder: Optional[Path]) -> int:
    """Convert one WELLBOREPROPS folder into a pvt table file."""
    if not wellprop_folder.is_dir():
        print(f"{wellprop_folder}: is not a folder", file=sys.stderr)
        return EXIT_CODE_INVALID_FOLDER
    destiny_folder = output_folder if output_folder is not None else wellprop_folder
    destiny_folder.mkdir(parents=True, exist_ok=True)
    WellpropToPvtConverter(wellprop_folder).generate_pvt_table_file(destiny_folder)
    print(f"{wellprop_folder}: written to {destiny_folder / wellprop_folder.name}.tab")
    return EXIT_CODE_SUCCESS


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Convert the WELLBOREPROPS folders given in the command line into pvt table files."""
    args = _create_parser().parse_args(argv)
    exit_code = EXIT_CODE_SUCCESS
    for wellprop_folder in args.wellprop_folders:
        exit_code = max(exit_code, _convert_one_folder(wellprop_folder, args.output_folder))
    return exit_code


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
