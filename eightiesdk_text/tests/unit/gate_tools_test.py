"""This package binds the shared gate-tools contract.

INHERITED, NOT RESTATED. The rule, the derivation of the tool list
from the makefiles, and the positive control live in
`eightiesdk_fitness.gate_tools_spec`.
"""

from pathlib import Path
from unittest import TestCase

import eightiesdk_text
from eightiesdk_fitness.gate_tools_spec import GateToolsSpec


class TextGateToolsTest(GateToolsSpec, TestCase):
    def package_root(self):
        return Path(eightiesdk_text.__file__).parent


__all__ = ['TextGateToolsTest']
