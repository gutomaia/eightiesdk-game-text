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


BORDER = NineSlice(
    *(cell((200, 160, 40 + i, 255)) for i in range(4)),
    cell(DARK),
    *(cell((100, 60, i, 255)) for i in range(4)),
)
FONT = PixelFont(
    {'A': (bar(3),), 'B': (bar(5),)},
    widths={'A': 4, 'B': 6, ' ': 2},
    rows=1,
)


def window(**kw):
    args = dict(
        column=0,
        row=0,
        columns=4,
        rows=3,
        border=BORDER,
        font=FONT,
        messages=('AB',),
    )
    args.update(kw)
    return TextWindow(**args)


class PixelFontTest(TestCase):
    def test_a_glyph_wider_than_its_cells_is_refused(self):
        with self.assertRaisesRegex(ValueError, "'A'"):
            PixelFont({'A': (bar(3),)}, widths={'A': 9, ' ': 2})

    def test_every_glyph_and_the_space_has_a_width(self):
        with self.assertRaisesRegex(ValueError, "'B'"):
            PixelFont(
                {'A': (bar(3),), 'B': (bar(3),)}, widths={'A': 4, ' ': 2}
            )

    def test_it_keeps_a_fixed_width_cell_font(self):
        fixed = FONT.fixed()
        self.assertIsInstance(fixed, CellFont)
        self.assertEqual(FONT.glyphs, fixed.glyphs)


class PackedLineTest(TestCase):
    def test_glyphs_sit_at_the_running_pen(self):
        w = window()
        steps = w.reveal(w.pages('AB')[0])[w.rows :]
        self.assertEqual(2, len(steps))
        # A: one cell; B starts at x 4 and reaches x 9: two cells
        self.assertEqual({(1, 1)}, {(r, c) for r, c, t in steps[0]})
        self.assertEqual({(1, 1), (1, 2)}, {(r, c) for r, c, t in steps[1]})
        first = w.tiles[dict(((r, c), t) for r, c, t in steps[1])[(1, 1)]]
        row = first[0]
        self.assertEqual([INK] * 3 + [DARK] + [INK] * 4, list(row))

    def test_a_cell_shows_each_glyph_as_it_is_typed(self):
        w = window()
        a, b = w.reveal(w.pages('AB')[0])[w.rows :]
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
        font = PixelFont(
            FONT.glyphs, widths=FONT.widths, rows=1, reveal='cell'
        )
        w = window(font=font)
        steps = w.reveal(w.pages('AB')[0])[w.rows :]
        self.assertEqual((), steps[0])
        self.assertEqual({(1, 1), (1, 2)}, {(r, c) for r, c, t in steps[1]})

    def test_it_costs_fewer_tiles(self):
        glyph = window(messages=('ABABAB',), columns=6)
        cellwise = window(
            messages=('ABABAB',),
            columns=6,
            font=PixelFont(
                FONT.glyphs, widths=FONT.widths, rows=1, reveal='cell'
            ),
        )
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
        self.assertEqual(4, len(found))
        (first, none), (fewer, fewer_note), *rest = found
        (second, cell_note), (third, fixed_note) = rest
        self.assertIsNone(none)
        self.assertEqual('glyph', first.font.reveal)
        # (b) FEWER LINES A PAGE, still a glyph a step: a page shows
        # (and a console streams) fewer patterns at once
        self.assertEqual('glyph', fewer.font.reveal)
        self.assertEqual(first.lines_per_page - 1, fewer.lines_per_page)
        self.assertIn('lines a page', fewer_note)
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
        self.assertEqual(
            fixed.page_ends[-1], end.__eightiesdk_resolve__(screen)
        )
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


class RetriesRunOutTest(TestCase):
    """A build still refused at the last level it may retry is
    refused, with its own refusal, even when a window has a fallback
    left below that level: a retry that gives up must never hand the
    director nothing, which it reported as a cartridge built."""

    def test_the_last_refusal_is_raised_when_the_retries_run_out(self):
        from types import SimpleNamespace

        from eightiesdk_game_text.window import retry_with_fallbacks

        w = window(messages=('AB A B',), columns=4, rows=3)
        screen = SimpleNamespace(width=256, height=224)
        tries = []

        def attempt():
            w.drawn_for(screen)
            tries.append(1)
            raise ValueError(f'sprite bank full, try {len(tries)}')

        with self.assertRaisesRegex(ValueError, 'sprite bank full, try 2'):
            retry_with_fallbacks(attempt, levels=1)
        self.assertEqual(2, len(tries))

    def test_inside_a_retry_past_its_levels_it_builds_once(self):
        from eightiesdk_game_text.window import _FALLBACK, retry_with_fallbacks

        token = _FALLBACK.set(3)
        try:
            self.assertEqual('rom', retry_with_fallbacks(lambda: 'rom'))
        finally:
            _FALLBACK.reset(token)


class RetryNotesTest(TestCase):
    def test_a_failed_attempt_s_port_notes_are_dropped(self):
        from eightiesdk_runtime.port_notes import collecting, compromise

        from eightiesdk_game_text.window import retry_with_fallbacks

        from types import SimpleNamespace

        w = window(messages=('AB A B',), columns=4, rows=3)
        screen = SimpleNamespace(width=256, height=224)
        tries = []

        def attempt():
            tries.append(1)
            w.drawn_for(screen)
            compromise(f'attempt {len(tries)}')
            if len(tries) < 2:
                raise ValueError('full')
            return 'rom'

        with collecting() as notes:
            retry_with_fallbacks(
                attempt, lambda e: 'full' in str(e), notes=notes
            )
        self.assertEqual(['attempt 2'], [n.compromise for n in notes])


class RetryOnlyWithAFallbackTest(TestCase):
    """The director retries any refusal, but only a build that drew a
    window with a fallback left: a game with no packed text, or one
    already at its last fallback, is refused at once."""

    def test_a_build_drawing_no_packed_window_is_not_retried(self):
        from eightiesdk_game_text.window import retry_with_fallbacks

        tries = []

        def attempt():
            tries.append(1)
            raise ValueError('room')

        with self.assertRaises(ValueError):
            retry_with_fallbacks(attempt)
        self.assertEqual(1, len(tries))

    def test_a_build_drawing_a_packed_window_is_retried_to_its_last(self):
        from types import SimpleNamespace

        from eightiesdk_game_text.window import retry_with_fallbacks

        w = window(messages=('AB A B',), columns=4, rows=3)
        screen = SimpleNamespace(width=256, height=224)
        drawn = []

        def attempt():
            drawn.append(w.drawn_for(screen)[0])
            raise ValueError('room')

        with self.assertRaises(ValueError):
            retry_with_fallbacks(attempt)
        self.assertEqual(3, len(drawn))


class RetryToldTest(TestCase):
    def test_the_build_that_fit_tells_what_its_windows_gave_up(self):
        from types import SimpleNamespace

        from eightiesdk_game_text.window import retry_with_fallbacks

        w = window(messages=('AB A B',), columns=4, rows=3)
        screen = SimpleNamespace(width=256, height=224)
        told = []

        def attempt():
            w.drawn_for(screen)
            w.drawn_for(screen)
            if not told and len(attempt.n) < 1:
                attempt.n.append(1)
                raise ValueError('room')
            return 'rom'

        attempt.n = []
        retry_with_fallbacks(attempt, told=told.append)
        self.assertEqual(1, len(told))
        self.assertIn('finished cell', told[0])


class FixedFallbackRewrapTest(TestCase):
    """A console that falls back to one cell a glyph rewraps the text to
    its own cells: the variable-width line breaks were placed for the
    cartridge's pixels, so a lone newline is a space; a blank line (a
    paragraph) still breaks."""

    def test_a_lone_newline_is_a_space_once_fixed(self):
        w = window(columns=6, rows=4, messages=('A\nAB A\n\nB',))
        self.assertEqual((('A', 'AB A'), ('B',)), w.pages(w.messages[0]))
        fixed = w.fixed()
        self.assertEqual(
            (('A AB', 'A'), ('B',)), fixed.pages(fixed.messages[0])
        )

    def test_a_declared_cell_font_keeps_its_newlines(self):
        w = window(columns=6, rows=4, font=FONT.fixed(), messages=('A\nAB',))
        self.assertEqual((('A', 'AB'),), w.pages('A\nAB'))


def _replayed(w, streamed):
    """The screen `streamed` draws, as tiles, after each step; and
    whether a step loaded a name a cell showed and then left (that
    cell shows the new tile until its run comes, a frame later)."""
    loaded, grid, screens, clobbered = {}, {}, [], False
    for uploads, runs in streamed:
        before = dict(grid)
        for name, tile in uploads:
            loaded[name] = tile
        for r, c, name, count in runs:
            for i in range(count):
                grid[(r, c + i)] = name
        for name, _tile in uploads:
            if any(
                n == name and grid[cell] != name for cell, n in before.items()
            ):
                clobbered = True
        screens.append({cell: loaded[n] for cell, n in grid.items()})
    return screens, clobbered


class StreamedNamesTest(TestCase):
    """A console with fewer tile names than a packed window's tiles
    loads each tile into a name as a step needs it: names no cell shows
    are reused, and a cell only it shows is redrawn in place."""

    def w(self):
        return window(messages=('ABAB BA AB\n\nBABA',), columns=6, rows=4)

    def expected(self, w):
        grid, out = {}, []
        for step in w.steps(0):
            for r, c, t in step:
                grid[(r, c)] = t
            out.append(dict(grid))
        return out

    def test_it_draws_every_step_as_the_window_does(self):
        w = self.w()
        names = tuple(range(100, 100 + w.tile_count))
        screens, clobbered = _replayed(w, w.streamed(names))
        self.assertEqual(self.expected(w), screens)
        self.assertFalse(clobbered)

    def test_it_fits_in_fewer_names_than_tiles(self):
        w = self.w()
        fewest = w.streamed_names_needed()
        self.assertLess(fewest, w.tile_count)
        names = tuple(range(7, 7 + fewest))
        streamed = w.streamed(names)
        used = {n for ups, runs in streamed for n, _t in ups} | {
            n for ups, runs in streamed for _r, _c, n, _k in runs
        }
        self.assertLessEqual(used, set(names))
        screens, clobbered = _replayed(w, streamed)
        self.assertEqual(self.expected(w), screens)
        self.assertFalse(clobbered)

    def test_too_few_names_is_refused(self):
        w = self.w()
        with self.assertRaisesRegex(ValueError, 'names'):
            w.streamed(tuple(range(w.streamed_names_needed() - 1)))


class FewerLinesTest(TestCase):
    def test_a_one_line_window_has_no_fewer_lines_level(self):
        w = window(messages=('AB',), columns=6, rows=3)
        self.assertEqual(1, w.lines_per_page)
        self.assertFalse(
            [n for _w, n in w.fallbacks(None) if n and 'lines a page' in n]
        )

    def test_its_pages_hold_fewer_lines(self):
        w = window(messages=('AB AB AB AB',), columns=4, rows=4)
        fewer = w.fewer_lines()
        self.assertGreater(len(fewer.page_ends), len(w.page_ends))
