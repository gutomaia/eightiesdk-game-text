"""A screen's tiles as a working set."""

from unittest import TestCase

from eightiesdk_text.font import Font
from eightiesdk_text.streaming import plan

BAR = '''
XXXXXXXX
XXXXXXXX
'''
DOT = '''
X.X.X.X.
.X.X.X.X
'''
GAP = '''
........
........
'''


def _font():
    return Font.from_art({'a': BAR, 'b': DOT, ' ': GAP})


class StreamingPlanTest(TestCase):
    """WHY THIS EXISTS. An atlas assigns every character a slot and
    expects them all resident — right for tiles uploaded once at
    boot, and it is why a Korean quiz measured out at eighteen
    questions on a NES: 454 distinct cells against a 256-tile
    table.

    One question screen uses 47 to 119 of those cells. The table
    is a WORKING SET, so a cartridge can hold every glyph in ROM
    and upload what the screen in front of the player needs.
    """

    def test_a_screen_numbers_its_own_slots_from_the_bottom(self):
        _store, screens = plan(_font(), ['ab'])

        self.assertEqual([(1,), (2,)], screens[0].grid)

    def test_slot_zero_is_left_alone(self):
        """A console clears its name table to zero and draws that
        tile in every gap. A screen's first cell landing there
        would show through all of them."""
        _store, screens = plan(_font(), ['a'])

        self.assertNotIn(0, screens[0].upload_slots())

    def test_two_screens_number_independently(self):
        """THE WHOLE POINT. Each screen's slots start again, so a
        name-table byte only ever has to hold that screen's count
        — never the cartridge's."""
        _store, screens = plan(_font(), ['a', 'b'])

        self.assertEqual(screens[0].grid, screens[1].grid)
        self.assertNotEqual(screens[0].upload, screens[1].upload)

    def test_the_store_keeps_a_shared_cell_once(self):
        """ROM traded for VRAM: a cell forty screens use is kept
        once and copied forty times."""
        store, screens = plan(_font(), ['ab', 'ba'])

        self.assertEqual(2, len(store))
        self.assertEqual(2, screens[0].slots)
        self.assertEqual(2, screens[1].slots)

    def test_a_repeated_character_costs_one_slot(self):
        _store, screens = plan(_font(), ['aaaa'])

        self.assertEqual(1, screens[0].slots)

    def test_newlines_survive_so_a_grid_stays_a_grid(self):
        _store, screens = plan(_font(), ['a\nb'])

        self.assertIn('\n', screens[0].grid)

    def test_the_upload_is_in_slot_order(self):
        """The crust copies them one after another, so the list IS
        the order — a plan that needed sorting would be a plan the
        crust had to understand."""
        store, screens = plan(_font(), ['ab'])

        first = screens[0]
        self.assertEqual(
            [store[index] for index in first.upload],
            [_font().glyph('a').cells[0], _font().glyph('b').cells[0]],
        )
