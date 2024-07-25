import pytest
from pathlib import Path

from alfasim_score.converter.alfacase.base_operation import BaseOperationBuilder
from alfasim_score.converter.alfacase.convert_alfacase import ScoreAlfacaseConverter
from alfasim_score.converter.alfacase.production_operation import ProductionOperationBuilder
from alfasim_score.converter.alfacase.score_input_reader import ScoreInputReader


@pytest.fixture
def score_input_gas_lift(shared_datadir: Path) -> ScoreInputReader:
    return ScoreInputReader(shared_datadir / "score_input_gas_lift.json")


@pytest.fixture
def score_input_natural_flow(shared_datadir: Path) -> ScoreInputReader:
    return ScoreInputReader(shared_datadir / "score_input_natural_flow.json")


@pytest.fixture
def alfacase_gas_lift(score_input_gas_lift: ScoreInputReader) -> ScoreAlfacaseConverter:
    return ScoreAlfacaseConverter(score_input_gas_lift)


@pytest.fixture
def alfacase_natural_flow(score_input_natural_flow: ScoreInputReader) -> ScoreAlfacaseConverter:
    return ScoreAlfacaseConverter(score_input_natural_flow)


@pytest.fixture
def base_operation_gas_lift(shared_datadir: Path) -> BaseOperationBuilder:
    return BaseOperationBuilder(shared_datadir / "score_input_gas_lift.json")


@pytest.fixture
def base_operation_natural_flow(shared_datadir: Path) -> BaseOperationBuilder:
    return BaseOperationBuilder(shared_datadir / "score_input_natural_flow.json")


@pytest.fixture
def production_operation_gas_lift(shared_datadir: Path) -> ProductionOperationBuilder:
    return ProductionOperationBuilder(shared_datadir / "score_input_gas_lift.json")


@pytest.fixture
def production_operation_natural_flow(shared_datadir: Path) -> ProductionOperationBuilder:
    return ProductionOperationBuilder(shared_datadir / "score_input_natural_flow.json")
