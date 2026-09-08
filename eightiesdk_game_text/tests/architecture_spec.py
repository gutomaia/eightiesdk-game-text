"""Contract for the package's import boundary.

The runtime discovers this extension by entry point. An import back
into a platform, the runtime, a sibling extension or a product would
invert that, so no production module may import one.

PARSED, NOT GREPPED. A check that reads source as a string fires on
the comment that explains an absence and stays silent on a quiet
removal; the first version of this rule refused the package for a
docstring that mentioned a product by name. The rule is about
imports, so it reads imports.
"""


class ImportBoundarySpec:
    """Bindings read production modules and name any crossing import."""

    def given_the_package_production_modules(self):
        raise NotImplementedError()

    def given_a_module_source(self, name, source):
        raise NotImplementedError()

    def when_the_import_boundary_is_checked(self):
        raise NotImplementedError()

    def assert_no_import_crosses_the_boundary(self):
        raise NotImplementedError()

    def assert_the_crossing_import_is_named(self, module, imported):
        raise NotImplementedError()

    def test_the_package_imports_nothing_across_the_boundary(self):
        self.given_the_package_production_modules()

        self.when_the_import_boundary_is_checked()

        self.assert_no_import_crosses_the_boundary()

    def test_the_neutral_runtime_records_are_not_a_crossing(self):
        """A console's runtime is contributed as typed CPU code through
        the platform-NEUTRAL records (ADR-0001), the way the HUD and
        the streamed animation do it. The neutral package is a
        neighbour; every console's crust stays across the line."""
        self.given_a_module_source(
            'runtime.py',
            'from eightiesdk_platform.runtime_contribution import '
            'RuntimeHook\n',
        )
        self.when_the_import_boundary_is_checked()
        self.assert_no_import_crosses_the_boundary()

    def test_a_crossing_import_is_refused_by_name(self):
        self.given_a_module_source(
            'leak.py',
            'from eightiesdk_platform_nes.video import upload\n',
        )

        self.when_the_import_boundary_is_checked()

        self.assert_the_crossing_import_is_named(
            'leak.py', 'eightiesdk_platform_nes.video'
        )

    def test_a_bare_import_is_refused_too(self):
        self.given_a_module_source('leak.py', 'import eightiesdk_runtime\n')

        self.when_the_import_boundary_is_checked()

        self.assert_the_crossing_import_is_named(
            'leak.py', 'eightiesdk_runtime'
        )

    def test_prose_naming_a_forbidden_package_is_not_an_import(self):
        self.given_a_module_source(
            'prose.py',
            '"""Measured on the quiz, against eightiesdk_runtime."""\n'
            '# eightiesdk_platform_nes does this by hand\n'
            'VALUE = "awgy"\n',
        )

        self.when_the_import_boundary_is_checked()

        self.assert_no_import_crosses_the_boundary()


__all__ = ['ImportBoundarySpec']
