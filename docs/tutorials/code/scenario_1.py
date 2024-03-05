
import warnings

import scipy
import math
scipy.radians = math.radians

import pandapower.plotting as pplt
# Fix a problem with the numba check in pandapower. This should
# be removed once pandapower > 2.13.1 is released.
import pandapower.auxiliary

pandapower.auxiliary._check_if_numba_is_installed = lambda x: x
warnings.filterwarnings("ignore", category=FutureWarning)

import mosaik
import mosaik.util
import random
from pprint import pprint
# end

SIM_CONFIG: mosaik.SimConfig = {
    "Weather": {"python": "mosaik.basic_simulators:InputSimulator"},
    "PV": {"python": "mosaik_components.pv.pvsimulator:PVSimulator"},
    "Grid": {"python": "mosaik_components.pandapower:Simulator"},
    "Output": {"python": "mosaik.basic_simulators:OutputSimulator"},
}
# end

world = mosaik.World(SIM_CONFIG)

# start simulators
weathersim = world.start("Weather", sim_id="Weather", step_size=900)
pvsim = world.start("PV", sim_id="PV", step_size=900, start_date="2023-06-01 12:00:00")
gridsim = world.start("Grid", sim_id="Grid", step_size=900)
outputsim = world.start("Output")
# end

weather = weathersim.Function(function=lambda time: random.uniform(0.0, 1000.0))
# end
pvs = pvsim.PV.create(
    50, area=10, latitude=53.14, efficiency=0.5, el_tilt=32.0, az_tilt=0.0
)
# end
grid = gridsim.Grid(network_function="create_cigre_network_lv")
# end

# filter buses
lv_buses = [
    entity
    for entity in grid.children
    if entity.type == 'Bus' and entity.extra_info["nominal voltage [kV]"] == 0.4
]
# end
ext_grid = [entity for entity in grid.children if entity.type == 'ExternalGrid'][0]
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

# connect ext_grid
world.connect(ext_grid, output, "P[MW]", "Q[MVar]")
# end

result = outputsim.get_dict(output.eid)
# end

# start run
world.run(until=3600)
# end

# start print
pprint(result)
# end