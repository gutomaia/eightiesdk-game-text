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
#: two cells wide and two tall, like a Hangul syllable
BLOCK = '''
XXXXXXXXXXXXXXXX
XXXXXXXX........
XXXXXXXXXXXXXXXX
XXXXXXXX........
XXXXXXXXXXXXXXXX
XXXXXXXX........
XXXXXXXXXXXXXXXX
XXXXXXXX........
XXXXXXXXXXXXXXXX
'''


def _font():
    return Font.from_art({'a': BAR, 'b': DOT, ' ': GAP, 'W': BLOCK})


class StreamingPlanTest(TestCase):
    """WHY THIS EXISTS. An atlas assigns every character a slot and
    expects them all resident — right for tiles uploaded once at
    boot, and it is why a Korean quiz measured out at eighteen
    questions on a NES: 454 distinct cells against a 256-tile
    table.

    The worst question screen shows 41 distinct characters, which
    is 164 tiles of 256. The table is a WORKING SET, so a cartridge
    holds every glyph in ROM and uploads what the screen needs.

    SHARED IN ROM, NOT IN VRAM: sharing is the difference between
    fitting two 4KB banks and not (3,632 bytes against 10,944), and
    in VRAM it is the difference between two numbers that both fit.
    So the store deduplicates and the screen keeps a uniform
    stride, whose tile number a console can compute.
    """

    def test_the_store_keeps_a_shared_cell_once(self):
        """THE HALF THAT MATTERS. A cell forty screens use is kept
        once — which is what puts a whole corpus in two banks."""
        store, _screens = plan(_font(), ['ab', 'ba'])

        self.assertEqual(2, len(store))

    def test_a_screen_keeps_its_own_character_order(self):
        _store, screens = plan(_font(), ['ab', 'ba'])

        self.assertEqual(('a', 'b'), screens[0].characters)
        self.assertEqual(('b', 'a'), screens[1].characters)

    def test_a_tile_number_is_arithmetic_and_not_a_lookup(self):
        """The reason the stride is uniform: a console multiplies
        an ordinal and adds. A shared VRAM layout would make it
        read a table per cell, and both fit 256 anyway."""
        _store, screens = plan(_font(), ['ab'], stride=4)

        self.assertEqual(0, screens[0].tile('a'))
        self.assertEqual(4, screens[0].tile('b'))
        self.assertEqual(6, screens[0].tile('b', quadrant=2))

    def test_a_narrow_character_still_costs_the_stride(self):
        """It buys free arithmetic, and it is a real cost: a space
        takes four tiles in a four-tile script."""
        _store, screens = plan(_font(), ['a b'], stride=4)

        self.assertEqual(3 * 4, screens[0].tiles)

    def test_a_repeated_character_is_uploaded_once(self):
        _store, screens = plan(_font(), ['aaaa'])

        self.assertEqual(('a',), screens[0].characters)

    def test_a_wide_glyph_keeps_its_cells_in_reading_order(self):
        store, screens = plan(_font(), ['W'])

        cells = screens[0].cells[0]
        self.assertEqual(4, len(cells))
        self.assertEqual(
            [store[index] for index in cells],
            list(_font().glyph('W').cells),
        )

    def test_a_glyph_wider_than_the_stride_is_refused(self):
        """Its last cells would be drawn from the next character's
        tiles — a screen of neighbours' halves, which reads as
        corruption rather than as a stride too small."""
        with self.assertRaises(ValueError) as caught:
            plan(_font(), ['W'], stride=2)

        message = str(caught.exception)
        self.assertIn('4', message)
        self.assertIn('2', message)

    def test_reserved_tiles_are_left_alone(self):
        """A console that clears its name table to zero draws that
        tile in every gap a screen does not write."""
        _store, screens = plan(_font(), ['a'], reserved=1)

        self.assertEqual(1, screens[0].tile('a'))
