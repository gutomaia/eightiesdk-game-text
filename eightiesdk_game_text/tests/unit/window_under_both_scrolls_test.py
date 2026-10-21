"""A text window opens under the camera's horizontal scroll too: it
states the variable and the first and last position the camera can be
at, as for the vertical one (ZELDA-NPC-TALK)."""

from types import SimpleNamespace
from unittest import TestCase

from .text_window_test import window
from .window_under_scroll_test import Resolving


class WindowUnderBothScrollsTest(TestCase):
    def test_a_window_states_no_horizontal_scroll_by_default(self):
        self.assertIsNone(window().scroll_x)
        self.assertIsNone(window().scroll_x_for(None))

    def test_a_window_carries_its_horizontal_scroll(self):
        self.assertEqual(
            ('camera_x', 0, 32),
            window(scroll_x=('camera_x', 0, 32)).scroll_x,
        )

    def test_the_horizontal_scroll_resolves_for_the_screen(self):
        declared = window(
            scroll_x=('camera_x', Resolving(0, 16), Resolving(0, 80))
        )
        screen = SimpleNamespace(width=160, height=144)
        self.assertEqual(('camera_x', 16, 80), declared.scroll_x_for(screen))
        self.assertEqual(('camera_x', 0, 0), declared.scroll_x_for(None))

    def test_a_horizontal_scroll_is_validated(self):
        for wrong in (('camera_x', 8, 0), ('camera_x', 0), (1, 0, 8)):
            with self.assertRaises(ValueError):
                window(scroll_x=wrong)

    def test_a_fitted_window_keeps_both_scrolls(self):
        declared = window(
            columns=7,
            rows=4,
            messages=('AB CD E',),
            scroll=('camera_y', 0, 8),
            scroll_x=('camera_x', 0, 16),
        )
        fitted = declared.fitted_for(SimpleNamespace(width=48, height=64))
        self.assertEqual(('camera_x', 0, 16), fitted.scroll_x)
        self.assertEqual(('camera_y', 0, 8), fitted.scroll)
