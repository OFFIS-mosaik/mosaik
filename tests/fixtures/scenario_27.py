"""
Scenario 27:
   A ⇄ B → C

This scenario tests for the right max_advance value if a simulator is
interrupted due to an earlier step.
"""


def create_scenario(world):
    model_a = world.start('A', step_type='event-based',
                          self_steps={0: 1, 1: 2}).A()
    model_b = world.start('LoopSim', loop_length=1).A()
    model_c = world.start('C', step_type='event-based').A()
    world.connect(model_a, model_b, ('val_out', 'loop_in'))
    world.connect(model_b, model_a, ('loop_out', 'val_in'), weak=True)
    world.connect(model_a, model_c, ('val_out', 'val_in'))
    world.connect(model_b, model_c, ('loop_out', 'val_in'))

    world.set_initial_event(model_a.sid, 0)


CONFIG = 'generic'

EXECUTION_GRAPH = """
A-0-0 A-0-1
A-0-0 LoopSim-0-0
LoopSim-0-0 A-0-0~1
A-0-0~1 A-0-1
A-0-0~1 LoopSim-0-0~1
A-0-0~1 C-0-0
LoopSim-0-0~1 LoopSim-0-1
LoopSim-0-0~1 C-0-0
A-0-1 LoopSim-0-1
LoopSim-0-1 A-0-1~1
A-0-1~1 C-0-1
A-0-1~1 LoopSim-0-1~1
LoopSim-0-1~1 C-0-1
"""

INPUTS = {
    'LoopSim-0-0': {'Loop': {'loop_in': {'A-0.0': 0}}},
    'A-0-0~1': {'0': {'val_in': {'LoopSim-0.Loop': 1}}},
    'LoopSim-0-0~1': {'Loop': {'loop_in': {'A-0.0': 0}}},
    'C-0-0': {'0': {'val_in': {'A-0.0': 0, 'LoopSim-0.Loop': 1}}},
    'LoopSim-0-1': {'Loop': {'loop_in': {'A-0.0': 1}}},
    'A-0-1~1': {'0': {'val_in': {'LoopSim-0.Loop': 1}}},
    'LoopSim-0-1~1': {'Loop': {'loop_in': {'A-0.0': 1}}},
    'C-0-1': {'0': {'val_in': {'A-0.0': 1, 'LoopSim-0.Loop': 1}}},
}

UNTIL = 2
