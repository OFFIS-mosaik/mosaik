"""
The simulation manager is responsible for starting simulation processes and
shutting them down.

It is able to start pure Python simulators in-process (by importing and
instantiating them), to start external simulation processes and to connect to
already running simulators and manage access to them.

"""
import importlib


def start(sim_name, sim_config):
    """
    Start the simulator *sim_name* based on the configuration im *sim_config*.

    The sim config is a dictionary with one entry for every simulator. The
    entry itself tells mosaik how to start the simulator::

        {
            'ExampleSimA': {
                'python': 'example_sim.mosaik:ExampleSim',
            },
            'ExampleSimB': {
                'cmd': 'example_sim %(addr)s,
                'cwd': '.',
            },
            'ExampleSimC': {
                'connect': 'host:port',
                'slots': 1,
            },
        }

    *ExampleSimA* is a pure Python simulator. Mosaik will import the module
    ``example_sim.mosaik`` and instantiate the class ``ExampleSim`` to start
    the simulator.

    *ExampleSimB* would be started by executing the command *example_sim* and
    passing the network address of mosaik das command line argument. You can
    optionally specify a *current working directory*. It defaults to ``.``.

    *ExampleSimC* can not be started by mosaik, so mosaik tries to connect to
    it. Only *slots* connections are allowed at the same time.

    The function returns a :class:`mosaik_api.Simulator` instance.

    It raises a :exc:`~mosaik.exceptions.SimulationError` if the simulator
    could not be started.

    """
    # TODO: This is only for in-proc python simulations. For remote
    #simulations, return a SimProxy instance instead.
    try:
        mod_name, cls_name = sim_config[sim_name]['python'].split(':')
        mod = importlib.import_module(mod_name)
        cls = getattr(mod, cls_name)
        sim = cls()
    except AttributeError, ImportError, KeyError, ValueError as err:
        raise exceptions.SimulationError(
            'Simulator "%s" could not be started: %s' % (sim_name, err.args[0])
        ) from None

    return sim
