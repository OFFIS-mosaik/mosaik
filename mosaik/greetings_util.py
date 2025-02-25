import platform
import sys
from textwrap import dedent

from mosaik_api_v3 import __version__ as api_version

from mosaik._version import version as mosaik_version


def print_greetings():
    greetings = f"""
                \033[32m____\033[0m                              _ _
               \033[32m/    \\\033[0m                            (_) |
          \033[34m____\033[32m/      \\\033[0m  _ __ ___   ___  ___  __ _ _| | __
         \033[34m/    \033[32m\\      /\033[0m | '_ ` _ \\ / _ \\/ __|/ _` | | |/ /
        \033[34m/      \033[32m\\____/\033[0m  | | | | | | (_) \\__ \\ (_| | |   <
        \033[34m\\      /\033[0m    \\  |_| |_| |_|\\___/|___/\\__,_|_|_|\\_\\
         \033[34m\\____/\033[0m      \\\033[31m____\033[0m
         \033[35m/    \\\033[0m      \033[31m/    \\\033[0m     mosaik: {mosaik_version}
        \033[35m/      \\\033[33m____\033[31m/      \\\033[0m       API: {api_version}
        \033[35m\\      /\033[33m    \\\033[31m      /\033[0m    Python: {get_python_version()}
         \033[35m\\____/\033[33m      \\\033[31m____/\033[0m         OS: {get_os()}
              \033[33m\\      /\033[0m            Docs: https://mosaik.readthedocs.io/en/{mosaik_version}/
               \033[33m\\____/\033[0m     Get in touch: https://github.com/orgs/OFFIS-mosaik/discussions
        """  # noqa: E501
    print(dedent(greetings), file=sys.stderr)  # noqa: T201


def get_python_version():
    return platform.python_version()


def get_os():
    return platform.platform()
