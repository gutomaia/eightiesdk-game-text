"""A window fitted to the screen a console shows, and its page ends read
from that fitted window (ZELDA-NPC-TALK).

The declaration is the same on every console. A screen narrower than the
window narrows it (its message rewraps); the game reads where pages end
through `page_end(n)`, which the build resolves for the console it is
for, so the script and the window always agree.
"""

from types import SimpleNamespace
from unittest import TestCase

from .text_window_test import window


def screen(width, height):
    return SimpleNamespace(width=width, height=height)


class FittedWindowTest(TestCase):
    def test_a_window_the_screen_holds_is_itself(self):
        declared = window(columns=6)
        self.assertIs(declared, declared.fitted_for(screen(64, 64)))

    def test_a_narrow_screen_narrows_the_window_and_keeps_it_on_screen(self):
        fitted = window(column=1, columns=6).fitted_for(screen(40, 64))
        self.assertEqual((0, 5), (fitted.column, fitted.columns))

    def test_a_short_screen_shortens_the_window(self):
        fitted = window(rows=6).fitted_for(screen(64, 32))
        self.assertEqual(4, fitted.rows)

    def test_a_narrowed_window_rewraps_its_message(self):
        declared = window(columns=7, messages=('AB CD',))
        fitted = declared.fitted_for(screen(48, 64))
        self.assertEqual((('AB CD',),), declared.pages('AB CD'))
        self.assertEqual((('AB', 'CD'),), fitted.pages('AB CD'))


class PageEndTest(TestCase):
    def test_a_page_end_resolves_against_the_console_screen(self):
        declared = window(columns=7, rows=6, messages=('AB CD E',))
        end = declared.page_end(0)
        narrow = declared.fitted_for(screen(48, 64))
        self.assertEqual(
            declared.page_ends[0], end.__eightiesdk_resolve__(screen(64, 64))
        )
        self.assertEqual(
            narrow.page_ends[0], end.__eightiesdk_resolve__(screen(48, 64))
        )
        self.assertNotEqual(declared.page_ends[0], narrow.page_ends[0])

    def test_no_screen_is_the_declared_window(self):
        declared = window()
        self.assertEqual(
            declared.page_ends[0],
            declared.page_end(0).__eightiesdk_resolve__(None),
        )
