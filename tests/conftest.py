import gc
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


# This is occasionally useful when trying to debug ResourceWarnings and
# the like, because it will cause them to right after the test (instead
# of whenever garbage collection happens to run.)
# Usually, `autouse` should be set to `False`. Set it temporarily to
# `True` for these purposes.
@pytest.fixture(autouse=True)
def ensure_gc():
    yield  # Run the test first
    print("Collecting garbage")
    gc.collect()


# This turns off benchmark tests by default. (They can be run by giving
# the --benchmarks option.) This is adapted from the pytest
# documentation:
# https://docs.pytest.org/en/latest/example/simple.html#control-skipping-of-tests-according-to-command-line-option


def pytest_addoption(parser):
    parser.addoption(
        "--benchmarks",
        action="store_true",
        default=False,
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
