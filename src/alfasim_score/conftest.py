import pytest
from pathlib import Path

from alfasim_score.converter.alfacase.base_operation import BaseOperationBuilder
from alfasim_score.converter.alfacase.convert_alfacase import ScoreAlfacaseConverter
from alfasim_score.converter.alfacase.injection_operation import InjectionOperationBuilder
from alfasim_score.converter.alfacase.production_operation import ProductionOperationBuilder
from alfasim_score.converter.alfacase.score_input_reader import ScoreInputReader

SCORE_GAS_LIFT_EXAMPLE_FILENAME = "score_input_gas_lift.json"
SCORE_NATURAL_FLOW_EXAMPLE_FILENAME = "score_input_natural_flow.json"
SCORE_INJECTION_EXAMPLE_FILENAME = "score_input_injection_operation.json"


@pytest.fixture
def score_input_gas_lift(shared_datadir: Path) -> ScoreInputReader:
    return ScoreInputReader(shared_datadir / SCORE_GAS_LIFT_EXAMPLE_FILENAME)


@pytest.fixture
def alfacase_gas_lift(score_input_gas_lift: ScoreInputReader) -> ScoreAlfacaseConverter:
    return ScoreAlfacaseConverter(score_input_gas_lift)


@pytest.fixture
def base_operation_gas_lift(score_input_gas_lift: ScoreInputReader) -> BaseOperationBuilder:
    return BaseOperationBuilder(score_input_gas_lift)


@pytest.fixture
def production_operation_gas_lift(
    score_input_gas_lift: ScoreInputReader,
) -> ProductionOperationBuilder:
    return ProductionOperationBuilder(score_input_gas_lift)


@pytest.fixture
def production_operation_natural_flow(shared_datadir: Path) -> ProductionOperationBuilder:
    score_input_reader = ScoreInputReader(shared_datadir / SCORE_NATURAL_FLOW_EXAMPLE_FILENAME)
    return ProductionOperationBuilder(score_input_reader)


@pytest.fixture
def injection_operation(shared_datadir: Path) -> InjectionOperationBuilder:
    score_input_reader = ScoreInputReader(shared_datadir / SCORE_INJECTION_EXAMPLE_FILENAME)
    return InjectionOperationBuilder(score_input_reader)
