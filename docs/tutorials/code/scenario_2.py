import random
from pprint import pprint

import mosaik
import mosaik.util

# end

SIM_CONFIG: mosaik.SimConfig = {
    "Weather": {"python": "mosaik.basic_simulators:InputSimulator"},
    "PV": {"python": "mosaik_components.pv.pvsimulator:PVSimulator"},
    "Grid": {"python": "mosaik_components.pandapower:Simulator"},
    "Output": {"python": "mosaik.basic_simulators:OutputSimulator"},
    "Profits": {"python": "profits_simulator:Simulator"},
}
# end

with mosaik.World(SIM_CONFIG) as world:
    # start simulators
    weathersim = world.start("Weather", sim_id="Weather", step_size=900)
    pvsim = world.start(
        "PV", sim_id="PV", step_size=900, start_date="2023-06-01 12:00:00"
    )
    gridsim = world.start("Grid", sim_id="Grid", step_size=900)
    profitssim = world.start("Profits", price=100)
    outputsim = world.start("Output")
    # end

    weather = weathersim.Function(function=lambda time: random.uniform(0.0, 1000.0))
    # end
    pvs = pvsim.PV.create(
        50, area=10, latitude=53.14, efficiency=0.5, el_tilt=32.0, az_tilt=0.0
    )
    pv_profit_eids = [f"Profit-for-{pv.eid}" for pv in pvs]
    pv_profits = profitssim.PVProfits.create(len(pv_profit_eids), eid=pv_profit_eids)
    # end
    grid = gridsim.Grid(network_function="create_cigre_network_lv")
    # end

    # filter buses
    lv_buses = [
        entity
        for entity in grid.children
        if entity.type == "Bus" and entity.extra_info["nominal voltage [kV]"] == 0.4
    ]
    # end
    ext_grid = grid.children_dict["ExternalGrid-0"]
    # end

    output = outputsim.Dict()
    # end

    # connect weather to pv
    for pv in pvs:
        world.connect(weather, pv, ("value", "DNI[W/m2]"))
    # end

    # connect pv to buses
    mosaik.util.connect_randomly(
        world,
        pvs,
        lv_buses,
        ("P[MW]", "P_gen[MW]"),
    )
    # end

    # connect profits
    mosaik.util.connect_zip(world, pvs, pv_profits, "P[MW]")
    mosaik.util.connect_many_to_one(world, pv_profits, output, "profit[EUR]")
    # end

    # connect ext_grid
    world.connect(ext_grid, output, "P[MW]", "Q[MVar]")
    # end

    # start run
    world.run(until=3600)
    # end

    # start print
    result = outputsim.get_dict(output.eid)
    pprint(result)
    # end
