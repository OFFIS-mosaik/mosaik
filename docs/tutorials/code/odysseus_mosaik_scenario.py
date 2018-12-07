import itertools
import random

from mosaik.util import connect_randomly, connect_many_to_one
import mosaik
import os


sim_config = {
    'CSV': {
        'python': 'mosaik_csv:CSV',
    },
    'ZMQ': {
        'cmd': 'mosaik-zmq %(addr)s',
    },
    'HouseholdSim': {
        'python': 'householdsim.mosaik:HouseholdSim',
    },
    'PyPower': {
        'python': 'mosaik_pypower.mosaik:PyPower',
    },
    # 'WebVis': {
    #     'cmd': 'mosaik-web -s 0.0.0.0:8000 %(addr)s',
    # },
    'Odysseus': {
        'connect': '127.0.0.1:5554',
    }
}

START = '2014-01-01 00:00:00'
END = 31 * 24 * 3600  # 1 day
PV_DATA = 'data/pv_10kw.csv'
PROFILE_FILE = 'data/profiles.data.gz'
GRID_NAME = 'demo_lv_grid'
GRID_FILE = 'data/%s.json' % GRID_NAME


def main():
    random.seed(23)
    world = mosaik.World(sim_config)
    create_scenario(world)
    world.run(until=END)  # As fast as possilbe
    # world.run(until=END, rt_factor=1/60)  # Real-time 1min -> 1sec


def create_scenario(world):
    # Start simulators
    pypower = world.start('PyPower', step_size=15*60)
    hhsim = world.start('HouseholdSim')
    pvsim = world.start('CSV', sim_start=START, datafile=PV_DATA)
    odysseusModel = world.start('Odysseus', step_size=60*15)
    zmqModel = world.start('ZMQ', step_size=15*60, duration=END)

    # Instantiate models
    grid = pypower.Grid(gridfile=GRID_FILE).children
    houses = hhsim.ResidentialLoads(sim_start=START,
                                    profile_file=PROFILE_FILE,
                                    grid_name=GRID_NAME).children
    pvs = pvsim.PV.create(20)
    odysseus = odysseusModel.Odysseus.create(1)
    ody = odysseus[0]
    zmq = zmqModel.Socket(host='tcp://*:', port=5558, socket_type='PUB')

    # Connect entities
    connect_buildings_to_grid(world, houses, grid)
    connect_randomly(world, pvs, [e for e in grid if 'node' in e.eid], 'P')

    # Database
    #hdf5 = db.Database(filename='demo.hdf5')

    nodes = [e for e in grid if e.type in 'RefBus, PQBus']

    # Web visualization
    # webvis = world.start('WebVis', start_date=START, step_size=60)
    # webvis.set_config(ignore_types=['Topology', 'ResidentialLoads', 'Grid',
    #                                 'Database'])
    # vis_topo = webvis.Topology()

    connect_many_to_one(world, nodes, ody, 'P', 'Vm')
    connect_many_to_one(world, houses, ody, 'P_out')
    connect_many_to_one(world, pvs, ody, 'P')

    connect_many_to_one(world, nodes, zmq, 'P', 'Vm')
    connect_many_to_one(world, houses, zmq, 'P_out')
    connect_many_to_one(world, pvs, zmq, 'P')


def connect_buildings_to_grid(world, houses, grid):
    buses = filter(lambda e: e.type == 'PQBus', grid)
    buses = {b.eid.split('-')[1]: b for b in buses}
    house_data = world.get_data(houses, 'node_id')
    for house in houses:
        node_id = house_data[house]['node_id']
        world.connect(house, buses[node_id], ('P_out', 'P'))


if __name__ == '__main__':
    main()
