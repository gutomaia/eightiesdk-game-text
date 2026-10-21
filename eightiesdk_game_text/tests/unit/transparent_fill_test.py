"""A window whose inside is transparent, with a declared fallback.

ALttP's window shows the room through its inside. The declaration says
so once, for every console: `fill=Transparent(fallback=colour)`. Its
tiles keep the inside clear (a layer that draws colour 0 as nothing
shows what is below); its `opaque_tiles` paint every clear pixel the
fallback, for a console whose window replaces the room's own cells.
"""

from unittest import TestCase

from eightiesdk_game_text.tests.unit.text_window_test import (
    BORDER,
    CLEAR,
    window,
)
from eightiesdk_game_text.window import NineSlice, Transparent

BLACK = (0, 0, 0)


class TransparentFillTest(TestCase):
    def setUp(self):
        self.window = window(fill=Transparent(fallback=BLACK))

    def test_the_inside_is_clear(self):
        fill = self.window.tiles[self.window.tile_of('fill')]
        self.assertTrue(all(p[3] == 0 for row in fill for p in row))
        self.assertTrue(self.window.see_through)

    def test_the_fallback_paints_every_clear_pixel(self):
        opaque = self.window.opaque_tiles
        self.assertEqual(len(self.window.tiles), len(opaque))
        fill = opaque[self.window.tile_of('fill')]
        self.assertTrue(all(p == (*BLACK, 255) for row in fill for p in row))
        self.assertTrue(all(p[3] == 255 for t in opaque for r in t for p in r))

    def test_a_glyph_keeps_its_ink_and_clears_the_rest(self):
        glyph = self.window.tiles[self.window.tile_of(('A', 0))]
        self.assertTrue(any(p[3] for row in glyph for p in row))
        self.assertTrue(any(not p[3] for row in glyph for p in row))

    def test_a_border_fill_with_alpha_is_no_longer_refused(self):
        NineSlice(
            **{
                **{f: getattr(BORDER, f) for f in BORDER.__dataclass_fields__},
                'fill': tuple(
                    tuple(CLEAR for _ in range(8)) for _ in range(8)
                ),
            }
        )

    def test_an_opaque_window_is_as_it_was(self):
        plain = window()
        self.assertFalse(plain.see_through)
        self.assertEqual(plain.tiles, plain.opaque_tiles)
