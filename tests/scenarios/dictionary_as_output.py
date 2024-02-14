"""
Test whether output data that consists of dictionaries is correctly
overwritten.
"""
#XFAIL = [False]

def create_scenario(world):
	model_a = world.start('FixedOut').Entity(
		outputs={
			0: {'answer': 42},
			1: {'question': 'still computing'},
		})
	model_b = world.start('B').A()
	world.connect(model_a, model_b, ('out', 'val_in'))

CONFIG = 'generic'

EXECUTION_GRAPH = """
FixedOut-0~0 B-0~0
FixedOut-0~0 FixedOut-0~1
B-0~0 B-0~1
FixedOut-0~1 B-0~1
"""

INPUTS = {
	'B-0~0': {'0': {'val_in': {'FixedOut-0.E0': {'answer': 42}}}},
	'B-0~1': {'0': {'val_in': {'FixedOut-0.E0': {'question': 'still computing'}}}},
}

UNTIL = 2
