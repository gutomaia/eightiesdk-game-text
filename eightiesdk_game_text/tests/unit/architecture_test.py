"""This package's binding of the import-boundary contract."""

import ast
from pathlib import Path
from unittest import TestCase

import eightiesdk_game_text
from eightiesdk_game_text.tests.architecture_spec import ImportBoundarySpec

PACKAGE_ROOT = Path(eightiesdk_game_text.__file__).parent

#: what a production module of this extension may never import
FORBIDDEN = (
    'eightiesdk_platform',
    'eightiesdk_runtime',
    'eightiesdk_game_hud',
    'eightiesdk_game_scene',
    'eightiesdk_game_animation',
    'eightiesdk_game_stream_animation',
    'awgy',
    'quiz',
)


def crossing_imports(sources, forbidden):
    """(module, imported name) for every import into `forbidden`.

    `sources` maps a module name to its text. A name crosses when its
    TOP-LEVEL package is a forbidden one or a member of its family:
    `eightiesdk_platform` bans `eightiesdk_platform_nes` too. The
    first reader matched `banned + '.'` only, and the positive
    control caught it letting a platform crust straight through.
    """

    def crosses(name):
        top = name.split('.')[0]
        return any(
            top == banned or top.startswith(banned + '_')
            for banned in forbidden
        )

    for module, source in sources.items():
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or '']
            else:
                continue
            for name in names:
                if crosses(name):
                    yield module, name


def production_sources(root):
    return {
        str(path.relative_to(root)): path.read_text(encoding='utf-8')
        for path in sorted(root.rglob('*.py'))
        if 'tests' not in path.relative_to(root).parts
    }


class ImportBoundaryTest(ImportBoundarySpec, TestCase):
    def given_the_package_production_modules(self):
        self.sources = production_sources(PACKAGE_ROOT)
        self.assertGreaterEqual(len(self.sources), 7)

    def given_a_module_source(self, name, source):
        self.sources = {name: source}

    def when_the_import_boundary_is_checked(self):
        self.crossings = tuple(crossing_imports(self.sources, FORBIDDEN))

    def assert_no_import_crosses_the_boundary(self):
        self.assertEqual((), self.crossings)

    def assert_the_crossing_import_is_named(self, module, imported):
        self.assertIn((module, imported), self.crossings)


__all__ = ['ImportBoundaryTest', 'crossing_imports']
