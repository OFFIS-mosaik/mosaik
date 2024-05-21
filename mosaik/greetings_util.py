from textwrap import dedent
import mosaik._version as mosaik_version
from mosaik_api_v3 import __version__ as api_version
import platform

def print_greetings():
    greetings = fr"""
                     ____                              _ _
                    /    \                            (_) |
               ____/      \  _ __ ___   ___  ___  __ _ _| | __
              /    \      / | '_ ` _ \ / _ \/ __|/ _` | | |/ / 
             /      \____/  | | | | | | (_) \__ \ (_| | |   <     
             \      /    \  |_| |_| |_|\___/|___/\__,_|_|_|\_\    
              \____/      \____
              /    \      /    \    mosaik version:     {mosaik_version.__version__}
             /      \____/      \   mosaik API version: {api_version}
             \      /    \      /   Python version:     {get_python_version()}
              \____/      \____/    OS:                 {get_os()}
                   \      /         Documentation:      https://mosaik.readthedocs.io/en/{mosaik_version.__version__}/
                    \____/          Get in touch:       https://github.com/orgs/OFFIS-mosaik/discussions
                    
        """
    print(dedent(greetings))

def get_python_version():
    return platform.python_version()

def get_os():
    return platform.platform()