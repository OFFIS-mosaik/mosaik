import pytest
import logging
from loguru import logger
from _pytest.logging import LogCaptureFixture

# From the loguru documentation, see https://loguru.readthedocs.io/en/latest/resources/migration.html#replacing-caplog-fixture-from-pytest-library
@pytest.fixture
def caplog(caplog: LogCaptureFixture):
    class PropogateHandler(logging.Handler):
        def emit(self, record):
            logging.getLogger(record.name).handle(record)

    handler_id = logger.add(PropogateHandler(), format="{message}")
    yield caplog
    logger.remove(handler_id)


# This turns off benchmark tests by default. (They can be run by giving
# the --benchmarks option.) This is adapted from the pytest
# documentation:
# https://docs.pytest.org/en/latest/example/simple.html#control-skipping-of-tests-according-to-command-line-option

def pytest_addoption(parser):
    parser.addoption(
        "--benchmarks", action="store_true", default=False,
        help="include benchmark tests (might be slow)",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--benchmarks"):
        # if --benchmarks is given, do not skip them
        return
    skip_benchmarks = pytest.mark.skip(reason="need --benchmarks option to run")
    for item in items:
        if "benchmark" in item.keywords:
            item.add_marker(skip_benchmarks)
