import pytest
from pathlib import Path

from alfasim_score.converter.alfacase.score_input_reader import ScoreInputReader


@pytest.fixture
def score_input_gas_lift(shared_datadir: Path) -> ScoreInputReader:
    return ScoreInputReader(shared_datadir / "score_input_gas_lift.json")


@pytest.fixture
def score_input_natural_flow(shared_datadir: Path) -> ScoreInputReader:
    return ScoreInputReader(shared_datadir / "score_input_natural_flow.json")
