# This file exists because pyproject.toml files offer no built-in way of
# combining several files to form the project description on PyPI,
# but we would like to have the README.rst, CHANGES.rst and AUTHORS.rst
# there. Luckily, we can fill the readme field in the project table
# dynamically using a Hatch plugin.

from hatchling.metadata.plugin.interface import MetadataHookInterface


class DescriptionDataHook(MetadataHookInterface):
    def update(self, metadata):
        metadata["readme"] = {
            "content-type": "text/x-rst",
            "text": "\n\n".join(
                open(f, encoding="utf-8").read()
                for f in ["README.rst", "CHANGES.rst", "AUTHORS.rst"]
            ),
        }
