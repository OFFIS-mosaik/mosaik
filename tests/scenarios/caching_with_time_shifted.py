def create_scenario(world):
	model_a = world.start('A').A()
	model_b = world.start('B').A()
	model_c = world.start('C').A()

	world.connect(model_a, model_b, ('val_out', 'val_in'), time_shifted=True, initial_data={'val_out': -1})
	world.connect(model_b, model_a, ('val_out', 'val_in'), time_shifted=True, initial_data={'val_out': -1})
	world.connect(model_a, model_c, ('val_out', 'val_in'))
	world.connect(model_c, model_b, ('val_out', 'val_in'))

CONFIG = 'generic'

EXECUTION_GRAPH = """
A-0~0 A-0~1
A-0~0 B-0~1
A-0~0 C-0~0
B-0~0 B-0~1
B-0~0 A-0~1
C-0~0 C-0~1
C-0~0 B-0~0
A-0~1 C-0~1
C-0~1 B-0~1	
"""

INPUTS = {
	'A-0~0': {'0': {'val_in': {'B-0.0': -1}}},
	'A-0~1': {'0': {'val_in': {'B-0.0': 0}}},
	'C-0~0': {'0': {'val_in': {'A-0.0': 0}}},
	'B-0~0': {'0': {'val_in': {'C-0.0': 0, 'A-0.0': -1}}},
	'B-0~1': {'0': {'val_in': {'A-0.0': 0, 'C-0.0': 1}}},
	'C-0~1': {'0': {'val_in': {'A-0.0': 1}}},
}

UNTIL = 2
