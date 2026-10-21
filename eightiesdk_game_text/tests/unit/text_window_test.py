"""A text window: a rect of cells, a 9-slice border, a cell font.

The declaration is the same on every console. What it resolves to is
shared too: one tile set (the fill, the eight border cells, and the
cells of only the glyphs the messages use, each once), the pages a
message wraps into, and the reveal as a stream of cell writes - the
border one row a step, then one glyph a step (ZELDA-NPC-TALK).
"""

from unittest import TestCase

from eightiesdk_game_text.window import (
    CellFont,
    NineSlice,
    TextWindow,
    window_tiles,
)

CLEAR = (0, 0, 0, 0)
DARK = (16, 16, 48, 255)
GOLD = (248, 200, 64, 255)
INK = (248, 248, 248, 255)


def cell(colour):
    return tuple(tuple(colour for _ in range(8)) for _ in range(8))


def ink_cell(mark):
    """A glyph cell: one ink pixel at `mark`, the rest clear."""
    return tuple(
        tuple(INK if y * 8 + x == mark else CLEAR for x in range(8))
        for y in range(8)
    )


BORDER = NineSlice(
    top_left=cell(GOLD),
    top=cell((200, 160, 40, 255)),
    top_right=cell((180, 140, 30, 255)),
    left=cell((160, 120, 20, 255)),
    fill=cell(DARK),
    right=cell((140, 100, 10, 255)),
    bottom_left=cell((120, 80, 0, 255)),
    bottom=cell((100, 60, 0, 255)),
    bottom_right=cell((80, 40, 0, 255)),
)
FONT = CellFont(
    {
        ch: (ink_cell(2 * i), ink_cell(2 * i + 1))
        for i, ch in enumerate('ABCDE')
    },
    rows=2,
)


def window(**kw):
    args = dict(
        column=1,
        row=2,
        columns=6,
        rows=6,
        border=BORDER,
        font=FONT,
        messages=('AB CD', 'E'),
    )
    args.update(kw)
    return TextWindow(**args)


class TextWindowTest(TestCase):
    def test_it_is_a_declaration_kind(self):
        self.assertEqual('text_window', TextWindow.__eightiesdk_declaration__)

    def test_the_tiles_are_fill_border_and_only_the_used_glyphs(self):
        tiles = window_tiles(window(messages=('AB',)))
        # fill first, then 8 border cells, then A and B (2 cells each)
        self.assertEqual(1 + 8 + 4, len(tiles))
        self.assertEqual(cell(DARK), tiles[0])

    def test_glyph_cells_are_drawn_over_the_solid_fill(self):
        tiles = window_tiles(window(messages=('A',)))
        self.assertTrue(
            all(p[3] == 255 for t in tiles for row in t for p in row)
        )

    def test_a_message_wraps_at_words_into_pages(self):
        w = window(columns=6, rows=6)  # inner 4 wide, 2 lines of 2 rows
        pages = w.pages('AB CD ED E')
        self.assertEqual((('AB', 'CD'), ('ED E',)), pages)

    def test_a_character_the_font_lacks_is_refused_by_name(self):
        with self.assertRaisesRegex(ValueError, "'Z'"):
            window(messages=('AZ',))

    def test_the_reveal_unrolls_one_row_then_types_one_glyph(self):
        w = window()
        steps = w.reveal(w.pages('AB CD ED E')[0])
        self.assertEqual(6 + 4, len(steps))
        self.assertEqual(6, len(steps[0]))  # a border row: 6 cells
        self.assertTrue(all(r == 2 for r, c, t in steps[0]))
        self.assertEqual(2, len(steps[6]))  # one glyph: two cells
        self.assertEqual({(3, 2), (4, 2)}, {(r, c) for r, c, t in steps[6]})

    def test_cells_after_a_step_show_the_border_rows_so_far(self):
        w = window()
        grid = w.cells(w.pages('AB')[0], 2)
        self.assertIsNotNone(grid[0][0])
        self.assertIsNotNone(grid[1][0])
        self.assertIsNone(grid[2][0])

    def test_the_tile_count_is_measured(self):
        self.assertEqual(1 + 8 + 10, window().tile_count)
