import warnings
from io import StringIO

from loguru import logger

import mosaik
import mosaik.basic_simulators
import mosaik.util
from mosaik.scenario import SimConfig


def test_warning_redirect_to_loguru():
    # Step 1: Setup a custom Loguru sink to capture output
    log_output = StringIO()
    logger.add(log_output, format="{message}", level="WARNING")

    # Step 2: Override warnings.showwarning to use the custom Loguru handler
    def custom_showwarning(message, category, filename, lineno, file=None, line=None):
        logger.warning(f"{filename}:{lineno}: {category.__name__}: {message}")

    warnings.showwarning = custom_showwarning

    # Step 3: Trigger a warning
    warnings.warn("This is a test warning!", UserWarning)

    # Step 4: Verify the output
    log_contents = log_output.getvalue().strip()  # Get the captured logs
    assert "This is a test warning!" in log_contents
    assert "UserWarning" in log_contents

    # Cleanup: Remove custom sink to prevent side effects
    logger.remove()


def test_non_existing_entity_warning():
    log_output = StringIO()
    logger.add(log_output, format="{message}", level="WARNING")
    SIM_CONFIG: SimConfig = {
        "TestSimulator": {
            "python": "mosaik.basic_simulators.test_simulator:TestSimulator",
        },
    }

    END = 1

    world = mosaik.World(SIM_CONFIG)
    with world.group():
        test_sim = world.start("TestSimulator")

    test_sim.set_add_unregistered_entity(True)
    test_model = test_sim.Test.create(2)

    world.connect(
        test_model[0], test_model[1], ("value", "to_be_deleted"), time_shifted=True
    )

    world.run(until=END)
    log_contents = log_output.getvalue().strip()
    assert (
        "Simulator TestSimulator-0 returned data for the entity non_existing_eid which was never created. This is likely an error in its get_data method."
        in log_contents
    )
    assert "UserWarning" in log_contents
    logger.remove()


def test_non_existing_attribute_warning():
    log_output = StringIO()
    logger.add(log_output, format="{message}", level="WARNING")
    SIM_CONFIG: SimConfig = {
        "TestSimulator": {
            "python": "mosaik.basic_simulators.test_simulator:TestSimulator",
        },
    }

    END = 1

    world = mosaik.World(SIM_CONFIG)
    with world.group():
        test_sim = world.start("TestSimulator")
    test_sim.set_add_unregistered_attr(True)
    test_model = test_sim.Test.create(2)

    world.connect(
        test_model[0], test_model[1], ("value", "to_be_deleted"), time_shifted=True
    )

    world.run(until=END)
    log_contents = log_output.getvalue().strip()  # Get the captured logs
    assert (
        "The attribute non_existing_attr does not exist in model Test. Data will not be transferred."
        in log_contents
    )
    assert "UserWarning" in log_contents
