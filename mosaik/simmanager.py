import importlib


def start(sim_name, sim_config):
    # TODO: This is only for in-proc python simulations. For remote
    #simulations, return a SimProxy instance instead.
    mod_name, cls_name = sim_config[sim_name]['python'].split(':')
    mod = importlib.import_module(mod_name)
    cls = getattr(mod, cls_name)
    return cls()
