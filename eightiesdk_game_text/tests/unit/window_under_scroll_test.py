"""A text window placed relative to the camera's scroll at open: it
states the variable and the first and last position the camera can be
at (ZELDA-NPC-TALK)."""

from types import SimpleNamespace
from unittest import TestCase

from .text_window_test import window


class Resolving(int):
    def __new__(cls, value, on_screen):
        made = super().__new__(cls, value)
        made.on_screen = on_screen
        return made

    def __eightiesdk_resolve__(self, screen):
        return self.on_screen


class WindowUnderScrollTest(TestCase):
    def test_a_window_states_no_scroll_by_default(self):
        self.assertIsNone(window().scroll)

    def test_a_window_carries_its_scroll(self):
        self.assertEqual(
            ('camera_y', 0, 32), window(scroll=('camera_y', 0, 32)).scroll
        )

    def test_the_scroll_resolves_for_the_screen(self):
        declared = window(
            scroll=('camera_y', Resolving(0, 40), Resolving(0, 40))
        )
        screen = SimpleNamespace(width=256, height=192)
        self.assertEqual(('camera_y', 40, 40), declared.scroll_for(screen))
        self.assertEqual(('camera_y', 0, 0), declared.scroll_for(None))

    def test_a_fitted_window_keeps_its_scroll(self):
        declared = window(
            columns=7, rows=4, messages=('AB CD E',), scroll=('camera_y', 0, 8)
        )
        fitted = declared.fitted_for(SimpleNamespace(width=48, height=64))
        self.assertEqual(('camera_y', 0, 8), fitted.scroll)

    def test_a_scroll_must_name_a_variable_and_two_positions(self):
        with self.assertRaisesRegex(ValueError, 'scroll'):
            window(scroll=('camera_y', 8))
        with self.assertRaisesRegex(ValueError, 'scroll'):
            window(scroll=('camera_y', 16, 8))
