from typing import Optional
from typing import Sequence

import argparse
import sys
from pathlib import Path

from alfasim_score.converter.pvt_table.pvt_table_file import PvtTableError
from alfasim_score.converter.pvt_table.pvt_table_fixer import PvtTableFixer

EXIT_CODE_SUCCESS = 0
EXIT_CODE_ISSUES_FOUND = 1
EXIT_CODE_INVALID_FILE = 3

FIXED_FILE_SUFFIX = "_fixed"


def _create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="alfasim-score-fix-pvt-table",
        description=(
            "Check and fix pvt tables in the OLGA keyword format in which the properties of a "
            "phase that does not exist at a pressure/temperature point were written as zero, "
            "which ALFAsim is not able to use."
        ),
    )
    parser.add_argument(
        "pvt_table_filepaths",
        metavar="PVT_TABLE",
        nargs="+",
        type=Path,
        help="the pvt table files to check and fix",
    )
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument(
        "-o",
        "--output",
        type=Path,
        help="where to write the fixed table, only allowed for a single pvt table file",
    )
    output_group.add_argument(
        "--in-place",
        action="store_true",
        help="overwrite the pvt table files with the fixed tables",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="only report the problems found, without writing any file",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="do not print the report of the check",
    )
    return parser


def _get_output_filepath(pvt_table_filepath: Path, output: Optional[Path], in_place: bool) -> Path:
    if in_place:
        return pvt_table_filepath
    if output is not None:
        return output
    return pvt_table_filepath.with_name(
        f"{pvt_table_filepath.stem}{FIXED_FILE_SUFFIX}{pvt_table_filepath.suffix}"
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Check and fix the pvt table files given in the command line."""
    parser = _create_parser()
    args = parser.parse_args(argv)
    if args.output is not None and len(args.pvt_table_filepaths) > 1:
        parser.error("--output can only be used with a single pvt table file.")

    exit_code = EXIT_CODE_SUCCESS
    for pvt_table_filepath in args.pvt_table_filepaths:
        try:
            fixer = PvtTableFixer.from_file(pvt_table_filepath)
            if args.check_only:
                check_result = fixer.check()
                output_filepath = None
            else:
                output_filepath = _get_output_filepath(
                    pvt_table_filepath, args.output, args.in_place
                )
                check_result = fixer.generate_fixed_pvt_table_file(output_filepath)
        except (PvtTableError, OSError) as error:
            print(f"{pvt_table_filepath}: {error}", file=sys.stderr)
            exit_code = max(exit_code, EXIT_CODE_INVALID_FILE)
            continue
        if not args.quiet:
            print(check_result.describe())
            if output_filepath is not None:
                print(f"  Written to {output_filepath}")
        if args.check_only and check_result.has_issues:
            exit_code = max(exit_code, EXIT_CODE_ISSUES_FOUND)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
