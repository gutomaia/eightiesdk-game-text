"""A variable-width font: glyphs packed at their own widths (ZELDA-VWF).

The game declares the font once, with each glyph's width (ALttP reads
them off $0E:CADF). The window packs the glyphs side by side at the
pen's running x, cuts each line into 8x8 cells and types one glyph a
step; a step writes every cell the glyph touches, as it looks once
that glyph is drawn. Nothing here knows a console.
"""

from unittest import TestCase

from eightiesdk_game_text.window import (
    CellFont,
    NineSlice,
    PixelFont,
    TextWindow,
)

CLEAR = (0, 0, 0, 0)
DARK = (16, 16, 48, 255)
INK = (248, 248, 248, 255)


def cell(colour):
    return tuple(tuple(colour for _ in range(8)) for _ in range(8))


def bar(width):
    """A glyph cell inked in its `width` leftmost columns."""
    return tuple(
        tuple(INK if x < width else CLEAR for x in range(8)) for _ in range(8)
    )


BORDER = NineSlice(*(cell((200, 160, 40 + i, 255)) for i in range(4)),
                   cell(DARK),
                   *(cell((100, 60, i, 255)) for i in range(4)))
FONT = PixelFont(
    {'A': (bar(3),), 'B': (bar(5),)},
    widths={'A': 4, 'B': 6, ' ': 2},
    rows=1,
)


def window(**kw):
    args = dict(column=0, row=0, columns=4, rows=3, border=BORDER,
                font=FONT, messages=('AB',))
    args.update(kw)
    return TextWindow(**args)


class PixelFontTest(TestCase):
    def test_a_glyph_wider_than_its_cells_is_refused(self):
        with self.assertRaisesRegex(ValueError, "'A'"):
            PixelFont({'A': (bar(3),)}, widths={'A': 9, ' ': 2})

    def test_every_glyph_and_the_space_has_a_width(self):
        with self.assertRaisesRegex(ValueError, "'B'"):
            PixelFont({'A': (bar(3),), 'B': (bar(3),)},
                      widths={'A': 4, ' ': 2})

    def test_it_keeps_a_fixed_width_cell_font(self):
        fixed = FONT.fixed()
        self.assertIsInstance(fixed, CellFont)
        self.assertEqual(FONT.glyphs, fixed.glyphs)


class PackedLineTest(TestCase):
    def test_glyphs_sit_at_the_running_pen(self):
        w = window()
        steps = w.reveal(w.pages('AB')[0])[w.rows:]
        self.assertEqual(2, len(steps))
        # A: one cell; B starts at x 4 and reaches x 9: two cells
        self.assertEqual({(1, 1)}, {(r, c) for r, c, t in steps[0]})
        self.assertEqual({(1, 1), (1, 2)}, {(r, c) for r, c, t in steps[1]})
        first = w.tiles[dict(((r, c), t) for r, c, t in steps[1])[(1, 1)]]
        row = first[0]
        self.assertEqual([INK] * 3 + [DARK] + [INK] * 4, list(row))

    def test_a_cell_shows_each_glyph_as_it_is_typed(self):
        w = window()
        a, b = w.reveal(w.pages('AB')[0])[w.rows:]
        self.assertNotEqual(a[0][2], b[0][2])

    def test_lines_wrap_by_pixels_not_characters(self):
        w = window(columns=4, rows=4)  # inner 16 px
        # 'AB' 10 + ' ' 2 + 'A' 4 = 16 fits; another 'B' does not
        self.assertEqual((('AB A', 'B'),), w.pages('AB A B'))

    def test_a_word_wider_than_the_window_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'BBB'):
            window(messages=('BBB',))

    def test_the_tile_set_holds_every_cell_the_reveal_writes(self):
        w = window(messages=('AB A', 'BA'))
        for m in range(2):
            for step in w.steps(m):
                for r, c, t in step:
                    self.assertLess(t, w.tile_count)


class FinishedCellRevealTest(TestCase):
    """reveal='cell': only finished cells, so fewer tiles."""

    def test_a_cell_is_written_once_it_is_finished(self):
        font = PixelFont(FONT.glyphs, widths=FONT.widths, rows=1,
                         reveal='cell')
        w = window(font=font)
        steps = w.reveal(w.pages('AB')[0])[w.rows:]
        self.assertEqual((), steps[0])
        self.assertEqual({(1, 1), (1, 2)}, {(r, c) for r, c, t in steps[1]})

    def test_it_costs_fewer_tiles(self):
        glyph = window(messages=('ABABAB',), columns=6)
        cellwise = window(
            messages=('ABABAB',), columns=6,
            font=PixelFont(FONT.glyphs, widths=FONT.widths, rows=1,
                           reveal='cell'))
        self.assertLess(cellwise.tile_count, glyph.tile_count)
