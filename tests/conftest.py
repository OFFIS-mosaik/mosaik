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