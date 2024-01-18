import mosaik
import logging
from copy import deepcopy
import mosaik.util
import pytest
from mosaik.scenario import SimConfig
from mosaik_api_v3.types import (
    Meta,
)


META: Meta =  {
    'api_version': '3.0',
    'type': 'hybrid',
    'models': {
        'ModelName': {
            'public': True,
            'params': ['param_1'],
            'attrs': ['attr_1', 'attr_2'],
        },
    },
}

SIM_CONFIG: SimConfig = {
    "MetaMirror": {
        "python": "tests.simulators.meta_mirror:MetaMirror",
    },
}

# Create World
world = mosaik.World(SIM_CONFIG)

# def test_union_is_created_successfully_event_based():
#     new_meta = deepcopy(META)
#     new_meta['type'] = 'event-based'
#     del new_meta['models']['ModelName']['attrs']
#     new_meta['models']['ModelName']['trigger'] = ['attr_1']
#     # the missing part
#     new_meta['models']['ModelName']['persistent'] = ['attr_1']
#     new_meta['models']['ModelName']['non-persistent'] = ['attr_2']
#     sim = world.start("MetaMirror", meta=new_meta)  
#     print(sim.ModelName.event_inputs)
#     print(sim.ModelName.event_outputs)
#     print(sim.ModelName.measurement_inputs)
#     print(sim.ModelName.attrs)
#     assert False

# def test_union_is_created_successfully_time_based():
#     new_meta = deepcopy(META)
#     new_meta['type'] = 'time-based'
#     del new_meta['models']['ModelName']['attrs']
#     new_meta['models']['ModelName']['trigger'] = ['attr_1']
#     # the missing part
#     new_meta['models']['ModelName']['non-trigger'] = ['attr_2']
#     new_meta['models']['ModelName']['persistent'] = ['attr_1']
#     new_meta['models']['ModelName']['non-persistent'] = ['attr_2']
#     sim = world.start("MetaMirror", meta=new_meta)  
#     print(sim.ModelName.event_inputs)
#     print(sim.ModelName.event_outputs)
#     print(sim.ModelName.measurement_inputs)
#     print(sim.ModelName.attrs)
#     assert False

# def test_union_is_created_successfully_hybrid():
#     new_meta = deepcopy(META)
#     new_meta['type'] = 'hybrid'
#     del new_meta['models']['ModelName']['attrs']
#     new_meta['models']['ModelName']['trigger'] = ['attr_1']
#     # the missing part
#     new_meta['models']['ModelName']['non-trigger'] = ['attr_2']
#     new_meta['models']['ModelName']['persistent'] = ['attr_1']
#     new_meta['models']['ModelName']['non-persistent'] = ['attr_2']
#     sim = world.start("MetaMirror", meta=new_meta)  
#     print(sim.ModelName.event_inputs)
#     print(sim.ModelName.event_outputs)
#     print(sim.ModelName.measurement_inputs)
#     print(sim.ModelName.attrs)
#     assert False

def test_cant_create_union_one_part_missing():
    new_meta = deepcopy(META)
    new_meta['type'] = 'event-based'
    # attrs is deleted to create the need for creating a union
    del new_meta['models']['ModelName']['attrs']
    new_meta['models']['ModelName']['trigger'] = ['attr_1']
    # the missing part
    new_meta['models']['ModelName']['non-trigger'] = []
    with pytest.raises(ValueError):
        world.start("MetaMirror", meta=new_meta)    

def test_no_attrs():
    new_meta = deepcopy(META)
    new_meta['type'] = 'time-based'
    new_meta['models']['ModelName']['trigger'] = ['attr_1']
    with pytest.raises(ValueError):
        world.start("MetaMirror", meta=new_meta)

def test_time_based_with_trigger_attrs():
    new_meta = deepcopy(META)
    new_meta['type'] = 'time-based'
    del new_meta['models']['ModelName']['attrs']
    with pytest.raises(ValueError):
        world.start("MetaMirror", meta=new_meta)

def test_event_based_with_non_trigger_attrs():
    new_meta = deepcopy(META)
    new_meta['type'] = 'event-based'
    new_meta['models']['ModelName']['non-trigger'] = ['attr_1']
    with pytest.raises(ValueError):
        world.start("MetaMirror", meta=new_meta)

def test_time_based_with_non_persistent_attrs():
    new_meta = deepcopy(META)
    new_meta['type'] = 'time-based'
    new_meta['models']['ModelName']['non-persistent'] = ['attr_1']
    with pytest.raises(ValueError):
        world.start("MetaMirror", meta=new_meta)

def test_event_based_with_persistent_attrs():
    new_meta = deepcopy(META)
    new_meta['type'] = 'event-based'
    new_meta['models']['ModelName']['persistent'] = ['attr_1']
    logging.info("This is an informational message.")
    with pytest.raises(ValueError):
        world.start("MetaMirror", meta=new_meta)

def test_persistent_non_persistent():
    new_meta = deepcopy(META)
    new_meta['models']['ModelName']['persistent'] = ['attr_1']
    new_meta['models']['ModelName']['non-persistent'] = ['attr_1']
    with pytest.raises(ValueError):
        world.start("MetaMirror", meta=new_meta)

# tests the incompatibility of the same attr as a trigger and as a non-trigger
def test_trigger_non_trigger():
    new_meta = deepcopy(META)
    new_meta['models']['ModelName']['trigger'] = ['attr_1']
    new_meta['models']['ModelName']['non-trigger'] = ['attr_1']
    with pytest.raises(ValueError):
        world.start("MetaMirror", meta=new_meta)