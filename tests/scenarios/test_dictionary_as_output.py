"""
Test whether output data that consists of dictionaries is correctly
overwritten.
"""

from mosaik import World


def create_scenario(world: World):
    model_a = world.start("FixedOut", sim_id="FixedOut").Entity(
        outputs={
            0: {"answer": 42},
            1: {"question": "still computing"},
        }
    )
    model_b = world.start("Generic", sim_id="B").A()
    world.connect(model_a, model_b, ("out", "val_in"))


def test_scenario(world: World):
    create_scenario(world)
    world.run(until=2)

    world.assert_graph(
        """
        FixedOut~0 B~0
        FixedOut~0 FixedOut~1
        B~0 B~1
        FixedOut~1 B~1
        """
    )

    world.assert_inputs(
        {
            "B~0": {"0": {"val_in": {"FixedOut.E0": {"answer": 42}}}},
            "B~1": {"0": {"val_in": {"FixedOut.E0": {"question": "still computing"}}}},
        }
    )
