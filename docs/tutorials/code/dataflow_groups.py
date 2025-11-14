"""Simple scenario that highlights group overlays in the Plotly
dataflow graph."""

import mosaik
import mosaik.util

SIM_CONFIG = {
    "ExampleSim": {
        "python": "simulator_mosaik:ExampleSim",
    },
    "ExampleSim2": {
        "python": "simulator_mosaik:ExampleSim",
    },
    "Collector": {
        "cmd": "%(python)s collector.py %(addr)s",
    },
}

END = 5


def main():
    with mosaik.World(SIM_CONFIG, debug=False) as world:
        with world.group("North Campus"):
            north_gen_sim = world.start("ExampleSim", sim_id="NorthGen")
            north_grid_sim = world.start("ExampleSim2", sim_id="NorthGrid")
            with world.group("Solar Farm"):
                north_solar_sim = world.start("ExampleSim", sim_id="NorthSolar")

            north_gen = north_gen_sim.ExampleModel(init_val=3)
            north_grid = north_grid_sim.ExampleModel(init_val=1)
            north_solar = north_solar_sim.ExampleModel(init_val=2)

        with world.group("South Campus"):
            south_gen_sim = world.start("ExampleSim", sim_id="SouthGen")
            south_gen = south_gen_sim.ExampleModel(init_val=5)

        collector = world.start("Collector")
        monitor = collector.Monitor()

        world.connect(north_solar, north_gen, ("val", "delta"))
        world.connect(
            north_gen,
            north_grid,
            ("val", "delta"),
            weak=True,
            initial_data={"val": 0},
        )
        world.connect(north_grid, monitor, ("val", "delta"))
        world.connect(south_gen, monitor, ("val", "delta"))

        world.run(until=END)

        fig = mosaik.util.plot_dataflow_graph_plotly(world, show_plot=False)
        fig.write_html("dataflow_groups.html", include_plotlyjs="cdn")


if __name__ == "__main__":
    main()
