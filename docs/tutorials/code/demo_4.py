# demo_4.py
import subprocess

import mosaik
import mosaik.util


SIM_CONFIG = {
    'Controller': {
        'python': 'controller_set_event:Controller',
    },
}

END = 60  # 60 seconds

# Create World
world = mosaik.World(SIM_CONFIG)

# Start simulators
controller = world.start('Controller')

# Instantiate models
external_event_controller = controller.Controller()
world.set_initial_event(external_event_controller.sid)

# Start GUI in a subprocess
proc = subprocess.Popen(['python', 'gui_button.py'])

# Run simulation in real-time
world.run(until=END, rt_factor=1.0)
