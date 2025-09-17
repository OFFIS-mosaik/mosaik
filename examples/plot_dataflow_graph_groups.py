#!/usr/bin/env python3
"""Demonstrate grouped dataflow graph visualization using Plotly."""

from __future__ import annotations

import math
from pathlib import Path

import mosaik
from mosaik.util import plot_dataflow_graph_plotly

SIM_CONFIG: mosaik.SimConfig = {
    "InputSim": {
        "python": "mosaik.basic_simulators:InputSimulator",
    },
    "OutputSim": {
        "python": "mosaik.basic_simulators:OutputSimulator",
    },
}


def build_world() -> tuple[mosaik.World, mosaik.ModelFactory, object, object]:
    """Create a small scenario with nested simulator groups."""

    world = mosaik.World(SIM_CONFIG, cache=False)

    with world.group("Sources"):
        with world.group("Wind Farm"):
            wind_sim = world.start("InputSim", step_size=1)
            wind_entity = wind_sim.Function.create(
                1,
                function=lambda t: round(50 + 10 * math.sin(t / 3), 2),
            )[0]

        with world.group("Solar Park"):
            solar_sim = world.start("InputSim", step_size=1)
            solar_entity = solar_sim.Function.create(
                1,
                function=lambda t: round(40 + 6 * math.cos(t / 4), 2),
            )[0]

    with world.group("Analytics"):
        collector = world.start("OutputSim")
        time_series_entity, totals_entity = collector.Dict.create(2)

    world.connect(wind_entity, time_series_entity, ("value", "wind_power"))
    world.connect(solar_entity, time_series_entity, ("value", "solar_power"))

    world.connect(
        wind_entity,
        totals_entity,
        ("value", "wind_power"),
        transform=lambda value: round(value * 1.05, 2),
    )
    world.connect(solar_entity, totals_entity, ("value", "solar_power"))

    return world, collector, time_series_entity, totals_entity


def main() -> None:
    world, collector, time_series_entity, totals_entity = build_world()

    try:
        world.run(until=24, shutdown=False)

        time_series_data = collector.get_dict(time_series_entity.eid)
        totals_data = collector.get_dict(totals_entity.eid)
        last_step = max(time_series_data) if time_series_data else None

        if last_step is not None:
            print("Last time step:", last_step)
            print("Measurements:", time_series_data[last_step])
            print("Totals:", totals_data[last_step])

        fig = plot_dataflow_graph_plotly(world)
        output_path = Path(__file__).with_name("dataflow_graph_plotly.html")
        fig.write_html(output_path)
        print(f"Wrote interactive graph to {output_path}")
        print("Open the file in a browser to inspect group boxes and connections.")
    finally:
        world.shutdown()


if __name__ == "__main__":
    main()
