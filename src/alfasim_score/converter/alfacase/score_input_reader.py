import json
from barril.units import Array
from pathlib import Path
from typing import Tuple

from alfasim_score.units import LENGTH_UNIT


class ScoreInputReader:
    def __init__(self, score_filepath: Path):
        self.score_filepath = score_filepath
        with open(score_filepath) as f:
            self.input_content = json.load(f)

    def read_well_trajectory(self) -> Tuple[Array, Array]:
        """Create the arrays with the x and y positions."""
        x = [entry["displacement"] for entry in self.input_content["trajectory"]["data"]]
        y = [-entry["vertical_depth"] for entry in self.input_content["trajectory"]["data"]]
        return Array(x, LENGTH_UNIT), Array(y, LENGTH_UNIT)
