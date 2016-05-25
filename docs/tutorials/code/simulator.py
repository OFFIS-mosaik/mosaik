# simulator.py
"""
This module contains a simple example simulator.

"""


class Model:
    """Simple model that increases its value *val* with some *delta* every
    step.

    You can optionally set the initial value *init_val*. It defaults to ``0``.

    """
    def __init__(self, init_val=0):
        self.val = init_val
        self.delta = 1

    def step(self):
        """Perform a simulation step by adding *delta* to *val*."""
        self.val += self.delta


class Simulator(object):
    """Simulates a number of ``Model`` models and collects some data."""
    def __init__(self):
        self.models = []
        self.data = []

    def add_model(self, init_val):
        """Create an instances of ``Model`` with *init_val*."""
        model = Model(init_val)
        self.models.append(model)
        self.data.append([])  # Add list for simulation data

    def step(self, deltas=None):
        """Set new model inputs from *deltas* to the models and perform a
        simulatino step.

        *deltas* is a dictionary that maps model indices to new delta values
        for the model.

        """
        if deltas:
            # Set new deltas to model instances
            for idx, delta in deltas.items():
                self.models[idx].delta = delta

        # Step models and collect data
        for i, model in enumerate(self.models):
            model.step()
            self.data[i].append(model.val)


if __name__ == '__main__':
    # This is how the simulator could be used:
    sim = Simulator()
    for i in range(2):
        sim.add_model(init_val=0)
    sim.step()
    sim.step({0: 23, 1: 42})
    print('Simulation finished with data:')
    for i, inst in enumerate(sim.data):
        print('%d: %s' % (i, inst))
