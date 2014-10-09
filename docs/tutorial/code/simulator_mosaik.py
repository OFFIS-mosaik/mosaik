# simulator_mosaik.py
"""
Mosaik interface for the example simulator.

"""
import mosaik_api

import simulator


META = {
    'models': {
        'Model': {
            'public': True,
            'params': ['init_val'],
            'attrs': ['delta', 'val'],
        },
    },
}
