"""
This scenario has two event-based simulators in a time-shifted loop. The second
simulator's output should be delayed due to the time shift, so that the simulators
do not enter a same-time loop.

  A ⇄ B

where the connection from B to A is time_shifted.
"""

from mosaik import World


def create_scenario(world: World):
    model_a = world.start("Generic", sim_id="A", step_type="event-based").A()
    model_b = world.start(
        "Generic", sim_id="B", step_type="event-based", output_timing={0: [0, 0, 1]}
    ).A()
    world.set_initial_event(model_a.sid)
    world.connect(model_a, model_b, ("val_out", "val_in"))
    world.connect(
        model_b,
        model_a,
        ("val_out", "val_in"),
        initial_data={"val_out": -1},
        time_shifted=True,
    )


def test_scenario(world: World):
    create_scenario(world)
    world.run(until=2)

    world.assert_graph(
        """
        A~0 B~0
        B~0 A~1
        A~1 B~1
        """
    )

    world.assert_inputs(
        {
            "A~0": {"0": {"val_in": {"B.0": -1}}},
            "B~0": {"0": {"val_in": {"A.0": 0}}},
            "A~1": {"0": {"val_in": {"B.0": 0}}},
            "B~1": {"0": {"val_in": {"A.0": 1}}},
        }
    )
