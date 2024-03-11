"""
This scenario consists of two event-based simulators in a weakly-resolved loop
with a connected time-based simulator. This used to produce deadlocks in the
scheduler when events where scheduled close to world.until.

  A ⇄ B → C

where the connection from B to A is weak.
"""


from mosaik.scenario import World


def create_scenario(world: World):
    with world.group():
        model_a = world.start("A", sim_id="A", step_type="event-based").A()
        model_b = world.start(
            "B", sim_id="B", step_type="event-based", output_timing={0: [1]}
        ).A()
    model_c = world.start("C", sim_id="C", step_type="time-based", step_size=1).A()
    world.set_initial_event(model_a.sid)
    world.connect(model_a, model_b, ("val_out", "val_in"))
    world.connect(model_b, model_a, ("val_out", "val_in"), weak=True)
    world.connect(model_b, model_c, ("val_out", "val_in"))


CONFIG = "generic"
WEAK = True

EXECUTION_GRAPH = """
A~0:0 B~0:0
"""

INPUTS = {
    "B~0:0": {"0": {"val_in": {"A.0": 0}}},
    "C~0": {},
}

UNTIL = 1
