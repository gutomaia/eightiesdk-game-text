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


class PageCountPerConsoleTest(TestCase):
    """A packed line can take fewer pages on a wide screen than on a
    handheld, so a script names pages it may not have."""

    def test_a_page_past_the_last_is_the_last(self):
        w = window(columns=6, messages=('AB',))
        self.assertEqual(1, len(w.page_ends))
        self.assertEqual(w.page_ends[0], w.page_end(1))
        self.assertEqual(w.page_ends[0], w.page_end(-1))


class HardBreakTest(TestCase):
    """A message says where its lines break (ALttP's [2], [3]); a
    narrower window still wraps inside a line."""

    def test_a_newline_starts_a_line(self):
        w = window(columns=6, rows=3)  # one line a page
        self.assertEqual((('A',), ('AB',)), w.pages('A\nAB'))

    def test_a_line_too_long_still_wraps(self):
        w = window(columns=4, rows=4)  # inner 16 px, two lines a page
        self.assertEqual((('A', 'AB A'), ('B',)), w.pages('A\nAB A B'))


class RevealedByCellTest(TestCase):
    """What a console with too few tile names falls back to: the same
    pages and step counts, only finished cells."""

    def test_it_keeps_the_page_ends_and_costs_fewer_tiles(self):
        w = window(messages=('ABABAB AB',), columns=6, rows=4)
        cellwise = w.revealed_by_cell()
        self.assertEqual('cell', cellwise.font.reveal)
        self.assertEqual(w.page_ends, cellwise.page_ends)
        self.assertLess(cellwise.tile_count, w.tile_count)
        self.assertEqual('glyph', w.font.reveal)

    def test_a_cell_font_window_is_itself(self):
        from eightiesdk_game_text.window import CellFont

        w = window(font=CellFont({'A': (bar(3),)}, rows=1), messages=('A',))
        self.assertIs(w, w.revealed_by_cell())


class FallbacksTest(TestCase):
    """The best a console can draw, in order: a glyph a step, finished
    cells, then the glyphs one cell each. The one a console settles on
    is the one its script's page ends read."""

    def test_the_fallbacks_go_glyph_cell_fixed(self):
        from types import SimpleNamespace

        w = window(messages=('ABAB AB',), columns=6, rows=4)
        screen = SimpleNamespace(width=256, height=224)
        found = w.fallbacks(screen)
        self.assertEqual(3, len(found))
        (first, none), (second, cell_note), (third, fixed_note) = found
        self.assertIsNone(none)
        self.assertEqual('glyph', first.font.reveal)
        self.assertEqual('cell', second.font.reveal)
        self.assertIn('finished cell', cell_note)
        self.assertNotIsInstance(third.font, PixelFont)
        self.assertIn('one cell', fixed_note)

    def test_a_page_end_reads_the_window_a_console_settled_on(self):
        from types import SimpleNamespace

        w = window(messages=('AB A B',), columns=4, rows=3)
        screen = SimpleNamespace(width=256, height=224)
        end = w.page_end(-1)
        packed = end.__eightiesdk_resolve__(screen)
        *_, (fixed, _note) = w.fallbacks(screen)
        w.settle(screen, fixed)
        self.assertEqual(fixed.page_ends[-1], end.__eightiesdk_resolve__(screen))
        self.assertNotEqual(packed, fixed.page_ends[-1])
        other = SimpleNamespace(width=256, height=224)
        self.assertEqual(packed, end.__eightiesdk_resolve__(other))


class FallbackRetryTest(TestCase):
    """A console whose build runs out of room only after the window
    is drawn (its code window full) builds again a fallback lower."""

    def test_drawn_for_follows_the_build_s_fallback_level(self):
        from types import SimpleNamespace

        from eightiesdk_game_text.window import retry_with_fallbacks

        w = window(messages=('AB A B',), columns=4, rows=3)
        screen = SimpleNamespace(width=256, height=224)
        seen = []

        def attempt():
            drawn, note = w.drawn_for(screen)
            seen.append((getattr(drawn.font, 'reveal', 'fixed'), note))
            if len(seen) < 3:
                raise ValueError('fixed code window full')
            return w.page_end(-1).__eightiesdk_resolve__(screen)

        end = retry_with_fallbacks(attempt, lambda e: 'full' in str(e))
        self.assertEqual(['glyph', 'cell', 'fixed'], [r for r, _ in seen])
        self.assertIsNone(seen[0][1])
        self.assertEqual(w.fixed().page_ends[-1], end)
        self.assertEqual('glyph', w.drawn_for(screen)[0].font.reveal)

    def test_a_refusal_it_does_not_name_is_raised(self):
        from eightiesdk_game_text.window import retry_with_fallbacks

        def attempt():
            raise KeyError('other')

        with self.assertRaises(KeyError):
            retry_with_fallbacks(attempt, lambda e: False)


class RetryNotesTest(TestCase):
    def test_a_failed_attempt_s_port_notes_are_dropped(self):
        from eightiesdk_runtime.port_notes import collecting, compromise

        from eightiesdk_game_text.window import retry_with_fallbacks

        tries = []

        def attempt():
            tries.append(1)
            compromise(f'attempt {len(tries)}')
            if len(tries) < 2:
                raise ValueError('full')
            return 'rom'

        with collecting() as notes:
            retry_with_fallbacks(
                attempt, lambda e: 'full' in str(e), notes=notes
            )
        self.assertEqual(['attempt 2'], [n.compromise for n in notes])
