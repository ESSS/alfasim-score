from pathlib import Path

import pytest

from alfasim_score.converter.alfacase.score_input_reader import ScoreInputReader


@pytest.fixture
def score_input_example(shared_datadir: Path) -> ScoreInputReader:
    return ScoreInputReader(shared_datadir / "score_input_example.json")