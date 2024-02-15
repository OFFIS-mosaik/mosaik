"""
Scenario 22:

"""


from mosaik.scenario import World


def create_scenario(world: World):
    with world.group():
        a = world.start('LoopSim', sim_id="Loop", loop_length=2).A()
        b = world.start('EchoSim', sim_id="Echo").A()

    world.set_initial_event(a.sid)

    world.connect(a, b, ('loop_out', 'loop_in'))
    world.connect(b, a, ('loop_out', 'loop_in'), weak=True)


CONFIG = 'loop'
WEAK = True

EXECUTION_GRAPH = """
Loop~0:0 Echo~0:0
Echo~0:0 Loop~0:1
Loop~0:1 Echo~0:1
Echo~0:1 Loop~0:2
Loop~0:2 Loop~1:0
Loop~1:0 Echo~1:0
Echo~1:0 Loop~1:1
Loop~1:1 Echo~1:1
Echo~1:1 Loop~1:2
"""

INPUTS = {
    'Echo~0:0': {'Echo': {'loop_in': {'Loop.Loop': 1}}},
    'Loop~0:1': {'Loop': {'loop_in': {'Echo.Echo': 1}}},
    'Echo~0:1': {'Echo': {'loop_in': {'Loop.Loop': 2}}},
    'Loop~0:2': {'Loop': {'loop_in': {'Echo.Echo': 2}}},
    'Echo~1:0': {'Echo': {'loop_in': {'Loop.Loop': 1}}},
    'Loop~1:1': {'Loop': {'loop_in': {'Echo.Echo': 1}}},
    'Echo~1:1': {'Echo': {'loop_in': {'Loop.Loop': 2}}},
    'Loop~1:2': {'Loop': {'loop_in': {'Echo.Echo': 2}}},
}

UNTIL = 2
