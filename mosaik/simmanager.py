"""
The simulation manager is responsible for starting simulation processes and
shutting them down.

It is able to start pure Python simulators in-process (by importing and
instantiating them), to start external simulation processes and to connect to
already running simulators and manage access to them.

"""
import collections
import importlib
import subprocess

from mosaik.exceptions import ScenarioError


def start(sim_name, sim_config, sim_id, sim_params):
    """
    Start the simulator *sim_name* based on the configuration im *sim_config*,
    give it the ID *sim_id* and pass the parameters of the dict *sim_params* to
    it.

    The sim config is a dictionary with one entry for every simulator. The
    entry itself tells mosaik how to start the simulator::

        {
            'ExampleSimA': {
                'python': 'example_sim.mosaik:ExampleSim',
            },
            'ExampleSimB': {
                'cmd': 'example_sim %(addr)s',
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

    Return a :class:`SimProxy` instance.

    """
    try:
        conf = sim_config[sim_name]
    except KeyError:
        raise ScenarioError('Simulator "%s" could not be started: Not found '
                            'in sim_config' % sim_name)

    # Try available starters in that order and raise an error if none of them
    # matches:
    starters = collections.OrderedDict(python=start_python,
                                       cmd=start_proc,
                                       connect=start_connect)
    for sim_type, start in starters.items():
        if sim_type in conf:
            return start(sim_name, conf, sim_id, sim_params)
    else:
        raise ScenarioError('Simulator "%s" could not be started: Invalid '
                            'configuration' % sim_name)


def start_python(sim_name, conf, sim_id, sim_params):
    """Import and instantiate the Python simulator *sim_name* based on its
    config entry *conf*.

    Raise a :exc:`~mosaik.exceptions.ScenarioError` if the simulator cannot be
    instantiated.

    """
    try:
        mod_name, cls_name = conf['python'].split(':')
        mod = importlib.import_module(mod_name)
        cls = getattr(mod, cls_name)
    except (AttributeError, ImportError, KeyError, ValueError) as err:
        detail_msgs = {
            ValueError: 'Malformed Python class name: Expected "module:Class"',
            ImportError: 'Could not import module',
            AttributeError: 'Class not found in module',
        }
        details = detail_msgs[type(err)]
        raise ScenarioError('Simulator "%s" could not be started: %s' %
                            (sim_name, details)) from None

    return SimProxy(sim_id, cls(**sim_params))


def start_proc(sim_name, conf, sim_id, sim_params):
    pass


def start_connect(sim_name, conf, sim_id, sim_params):
    pass


class SimProxy:
    """Simple proxy/facade for in-process simulators."""
    def __init__(self, sid, inst):
        self.sid = sid
        self.inst = inst
        self.meta = inst.meta
        self.last_step = float('-inf')
        self.next_step = 0
        self.step_required = None

    def create(self, num, model_name, model_params):
        return self.inst.create(num, model_name, model_params)

    def step(self, time, inputs):
        return self.inst.step(time, inputs)

    def get_data(self, outputs):
        return self.inst.get_data(outputs)

    def stop(self):
        pass  # Nothing to  do here.
