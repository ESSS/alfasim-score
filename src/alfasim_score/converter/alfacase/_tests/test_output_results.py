import json
import pandas as pd
import pytest
from pathlib import Path
from pytest_regressions.file_regression import FileRegressionFixture

from alfasim_score.converter.alfacase.score_output_generator import generate_output_results


def test_generate_output_results(
    shared_datadir: Path, file_regression: FileRegressionFixture
) -> None:
    example_exported_filepath = shared_datadir / "case.data"
    element_name = "7-SRR-2-RJS (2022-07-28_15-01-27)"
    active_annuli = ["a", "b", "c"]
    output = generate_output_results(example_exported_filepath, element_name, active_annuli)
    file_regression.check(json.dumps(output, indent=2), extension=".json", encoding="utf-8")
