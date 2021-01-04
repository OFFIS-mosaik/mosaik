"""
Scenario 22:

"""


def create_scenario(world):
    a = world.start('LoopSim', loop_length=3).A()
    b = world.start('EchoSim').A()

    world.set_event(a.sid)

    world.connect(a, b, ('loop_out', 'loop_in'))
    world.connect(b, a, ('loop_out', 'loop_in'), weak=True)


CONFIG = 'loop'

EXECUTION_GRAPH = """
LoopSim-0-0 EchoSim-0-0
EchoSim-0-0 LoopSim-0-0
LoopSim-0-0 LoopSim-0-1
LoopSim-0-1 EchoSim-0-1
EchoSim-0-1 LoopSim-0-1
"""

INPUTS = {
    'LoopSim-0-0': {'Loop': {'loop_in': {'EchoSim-0.Echo': 3}}},
    'EchoSim-0-0': {'Echo': {'loop_in': {'LoopSim-0.Loop': 3}}},
    'LoopSim-0-1': {'Loop': {'loop_in': {'EchoSim-0.Echo': 3}}},
    'EchoSim-0-1': {'Echo': {'loop_in': {'LoopSim-0.Loop': 3}}},
}

UNTIL = 2
