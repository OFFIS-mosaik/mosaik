"""Scenario that highlights group overlays
in the Plotly dataflow graph."""

import mosaik
import mosaik.util

SIM_CONFIG = {
    "Input": {"python": "mosaik.basic_simulators.input_simulator:InputSimulator"},
    "Output": {"python": "mosaik.basic_simulators.output_simulator:OutputSimulator"},
}

END = 5


def main() -> None:
    with mosaik.World(SIM_CONFIG, debug=False) as world:
        with world.group("North Campus"):
            with world.group("Solar Farm"):
                north_solar = world.start("Input", sim_id="NorthSolar").Constant(
                    constant=2
                )
            north_gen = world.start("Input", sim_id="NorthGen").Constant(constant=3)
            north_grid = world.start("Output", sim_id="NorthGrid").Dict()

        with world.group("South Campus"):
            south_gen = world.start("Input", sim_id="SouthGen").Constant(constant=5)

        monitor = world.start("Output", sim_id="Monitor").Dict()

        world.connect(north_solar, north_grid, ("value", "value"))
        world.connect(
            north_gen,
            north_grid,
            ("value", "value"),
            weak=True,
        )
        world.connect(north_gen, monitor, ("value", "value"))
        world.connect(south_gen, monitor, ("value", "value"))

        world.run(until=END)

        fig = mosaik.util.plot_dataflow_graph_plotly(world, show_plot=False)
        fig.write_html("dataflow_groups.html", include_plotlyjs="cdn")


if __name__ == "__main__":
    main()
