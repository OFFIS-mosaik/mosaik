from textwrap import dedent
from mosaik._version import version as mosaik_version
from mosaik_api_v3 import __version__ as api_version
import platform
import sys


def print_greetings():
    greetings = rf"""
                     ____                              _ _
                    /    \                            (_) |
               ____/      \  _ __ ___   ___  ___  __ _ _| | __
              /    \      / | '_ ` _ \ / _ \/ __|/ _` | | |/ / 
             /      \____/  | | | | | | (_) \__ \ (_| | |   <     
             \      /    \  |_| |_| |_|\___/|___/\__,_|_|_|\_\    
              \____/      \____
              /    \      /    \    mosaik version:     {mosaik_version}
             /      \____/      \   mosaik API version: {api_version}
             \      /    \      /   Python version:     {get_python_version()}
              \____/      \____/    OS:                 {get_os()}
                   \      /         Documentation:      https://mosaik.readthedocs.io/en/{mosaik_version}/
                    \____/          Get in touch:       https://github.com/orgs/OFFIS-mosaik/discussions
                    
        """
    print(dedent(greetings), file=sys.stderr)


def get_python_version():
    return platform.python_version()


def get_os():
    return platform.platform()
