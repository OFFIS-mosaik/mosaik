"""Small scenario demonstrating simulator call tracing.

Run this file from the repository root with::

    python docs/how-tos/code/simulator_tracing.py
"""

from __future__ import annotations

import sys

from loguru import logger

import mosaik
from mosaik.scenario import SimConfig

SIM_CONFIG: SimConfig = {
    "Input": {"python": "mosaik.basic_simulators:InputSimulator"},
    "Output": {"python": "mosaik.basic_simulators:OutputSimulator"},
}


def main() -> None:
    # Remove loguru's default sink so this example only prints the
    # selected simulator traces. Applications with their own logging
    # setup can keep their existing sinks.
    logger.remove()
    logger.enable("mosaik")

    # Shorter prefixes select broader groups, for example "sim" for all
    # simulators or "sim.local" for all in-process simulators.
    simulator_filter = "sim.local.Input"
    trace_handler = logger.add(
        sys.stderr,
        level="TRACE",
        filter=lambda record: (
            record["extra"].get("simulator", "").startswith(simulator_filter)
        ),
        format="{level: <8} | {extra[simulator]} | {message}",
    )

    try:
        with mosaik.World(
            SIM_CONFIG, configure_logging=False, skip_greetings=True
        ) as world:
            input_sim = world.start("Input", sim_id="Input", step_size=1)
            output_sim = world.start("Output", sim_id="Output")

            source = input_sim.Constant(constant=42)
            collector = output_sim.Dict()
            world.connect(source, collector, "value")

            world.run(until=2, print_progress=False)
            print("Collected data:", output_sim.get_dict(collector.eid))
    finally:
        logger.remove(trace_handler)


if __name__ == "__main__":
    main()
