"""
Scenario 27:
   A ⇄ B → C

This scenario tests for the right max_advance value if a simulator is
interrupted due to an earlier step.
"""


from mosaik.scenario import World


def create_scenario(world: World):
    with world.group():
        model_a = world.start('A', sim_id="A", step_type='event-based',
                            self_steps={0: 1, 1: 2}).A()
        model_b = world.start('LoopSim', sim_id="Loop", loop_length=1).A()
        model_c = world.start('C', sim_id="C", step_type='event-based').A()
    world.connect(model_a, model_b, ('val_out', 'loop_in'))
    world.connect(model_b, model_a, ('loop_out', 'val_in'), weak=True)
    world.connect(model_a, model_c, ('val_out', 'val_in'))
    world.connect(model_b, model_c, ('loop_out', 'val_in'))

    world.set_initial_event(model_a.sid, 0)


CONFIG = 'generic'
WEAK = True

EXECUTION_GRAPH = """
A~0:0    A~1:0
A~0:0    Loop~0:0
A~0:0    C~0:0
Loop~0:0 A~0:1
Loop~0:0 C~0:0
A~0:1    A~1:0
A~0:1    Loop~0:1
A~0:1    C~0:1
Loop~0:1 Loop~1:0
A~1:0    Loop~1:0
A~1:0    C~1:0
Loop~1:0 A~1:1
Loop~1:0 C~1:0
A~1:1    C~1:1
A~1:1    Loop~1:1
Loop~1:1
"""

INPUTS = {
    'Loop~0:0': {'Loop': {'loop_in': {'A.0': 0}}},
    'A~0:1': {'0': {'val_in': {'Loop.Loop': 1}}},
    'Loop~0:1': {'Loop': {'loop_in': {'A.0': 0}}},
    'C~0:0': {'0': {'val_in': {'A.0': 0, 'Loop.Loop': 1}}},
    'Loop~1:0': {'Loop': {'loop_in': {'A.0': 1}}},
    'A~1:1': {'0': {'val_in': {'Loop.Loop': 1}}},
    'Loop~1:1': {'Loop': {'loop_in': {'A.0': 1}}},
    'C~1:0': {'0': {'val_in': {'A.0': 1, 'Loop.Loop': 1}}},
    'C~0:1': {'0': {'val_in': {'A.0': 0}}},
    'C~1:1': {'0': {'val_in': {'A.0': 1}}},
}

UNTIL = 2
