"""
Scenario 1::
   A(1)
"""


from mosaik import World


def create_scenario(world: World):
    example_simulator = world.start("Local", sim_id="A")
    example_simulator.A(init_val=0)


UNTIL = 3


def test_scenario(world: World):
    create_scenario(world)
    world.run(until=UNTIL)

    world.assert_graph(
        """
        A~0 A~1
        A~1 A~2
        """
    )

    world.assert_inputs({})
