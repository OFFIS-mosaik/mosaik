"""
Scenario 22:

"""


from mosaik.scenario import World


def create_scenario(world: World):
    with world.group():
        a = world.start('LoopSim', loop_length=2).A()
        b = world.start('EchoSim').A()

    world.set_initial_event(a.sid)

    world.connect(a, b, ('loop_out', 'loop_in'))
    world.connect(b, a, ('loop_out', 'loop_in'), weak=True)


CONFIG = 'loop'
WEAK = True

EXECUTION_GRAPH = """
LoopSim-0~0   EchoSim-0~0
EchoSim-0~0   LoopSim-0~0:1
LoopSim-0~0:1 EchoSim-0~0:1
EchoSim-0~0:1 LoopSim-0~0:2
LoopSim-0~0:2 LoopSim-0~1
LoopSim-0~1   EchoSim-0~1
EchoSim-0~1   LoopSim-0~1:1
LoopSim-0~1:1 EchoSim-0~1:1
EchoSim-0~1:1 LoopSim-0~1:2
"""

INPUTS = {
    'EchoSim-0~0': {'Echo': {'loop_in': {'LoopSim-0.Loop': 1}}},
    'LoopSim-0~0:1': {'Loop': {'loop_in': {'EchoSim-0.Echo': 1}}},
    'EchoSim-0~0:1': {'Echo': {'loop_in': {'LoopSim-0.Loop': 2}}},
    'LoopSim-0~0:2': {'Loop': {'loop_in': {'EchoSim-0.Echo': 2}}},
    'EchoSim-0~1': {'Echo': {'loop_in': {'LoopSim-0.Loop': 1}}},
    'LoopSim-0~1:1': {'Loop': {'loop_in': {'EchoSim-0.Echo': 1}}},
    'EchoSim-0~1:1': {'Echo': {'loop_in': {'LoopSim-0.Loop': 2}}},
    'LoopSim-0~1:2': {'Loop': {'loop_in': {'EchoSim-0.Echo': 2}}},
}

UNTIL = 2
