from alfasim_sdk import CaseDescription
from alfasim_sdk import convert_description_to_alfacase
from barril.units import Scalar
from pathlib import Path

from alfasim_score.common import AnnulusLabel
from alfasim_score.common import OperationType
from alfasim_score.converter.alfacase.base_operation import BaseOperationBuilder
from alfasim_score.converter.alfacase.injection_operation import InjectionOperationBuilder
from alfasim_score.converter.alfacase.production_operation import ProductionOperationBuilder
from alfasim_score.converter.alfacase.score_input_reader import ScoreInputReader
from alfasim_score.converter.alfacase.score_output_generator import ScoreOutputGenerator


def convert_score_to_alfacase_description(score_filepath: Path) -> CaseDescription:
    """Convert SCORE input file to an alfacase description."""
    score_input = ScoreInputReader(score_filepath)
    operation_type = score_input.read_operation_type()
    builder: BaseOperationBuilder
    if operation_type == OperationType.PRODUCTION:
        builder = ProductionOperationBuilder(score_filepath)
    else:  # OperationType.INJECTION
        builder = InjectionOperationBuilder(score_filepath)
    return builder.generate_operation_alfacase_description()


def convert_score_to_alfacase(score_filepath: Path, alfacase_filepath: Path) -> None:
    """Convert SCORE input file to an alfacase file."""
    alfacase_description = convert_score_to_alfacase_description(score_filepath)
    alfacase_content = convert_description_to_alfacase(alfacase_description)
    alfacase_filepath.write_text(data=alfacase_content, encoding="utf-8")


def convert_output_file_results(
    alfasim_results_filepath: Path,
    output_score_filepath: Path,
    active_annuli: list[AnnulusLabel],
    well_start_position: Scalar,
) -> None:
    output_generator = ScoreOutputGenerator(
        alfasim_results_filepath, well_start_position, active_annuli
    )
    output_generator.generate_output_file(output_score_filepath)
