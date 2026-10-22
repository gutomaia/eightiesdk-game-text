"""A question in a text window: options under it, a cursor glyph that
moves between them (ZELDA-QUESTION).

The game declares the options, the cursor glyph and how many moves the
player may make; the window says the question with the options on its
last page, the cursor on the first, and each step after that redraws
the option lines with the cursor one option further (round). The
option the cursor is on is the steps past the question, modulo the
options: a byte of game state, as every window step is. What follows
an answer is the game's: each answer is its own window declared over
the same cells. Nothing here knows a console.
"""

from unittest import TestCase

from eightiesdk_game_text.window import (
    Choice,
    PixelFont,
    TextWindow,
)

from eightiesdk_game_text.tests.unit.text_window_test import (
    BORDER,
    FONT,
)
from eightiesdk_game_text.tests.unit import vwf_text_window_test as vwf


def window(**kw):
    args = dict(
        column=0,
        row=0,
        columns=8,
        rows=8,
        border=BORDER,
        font=FONT,
        messages=('AB',),
        choice=Choice(options=('CD', 'E'), cursor='A', indent=1, moves=3),
    )
    args.update(kw)
    return TextWindow(**args)


class ChoicePagesTest(TestCase):
    def test_the_options_follow_the_question_cursor_on_the_first(self):
        self.assertEqual(
            window().pages(window().messages[0]),
            (('AB', ' A CD', '   E'),),
        )

    def test_options_that_do_not_fit_the_page_start_the_next(self):
        w = window(messages=('AB\nCD',))
        self.assertEqual(
            w.pages(w.messages[0]), (('AB', 'CD'), (' A CD', '   E'))
        )


class ChoiceStepsTest(TestCase):
    def test_moves_follow_the_whole_question(self):
        w = window()
        start = w.choice_start
        self.assertEqual(start, w.page_ends[-1])
        self.assertEqual(len(w.steps()), start + 3)

    def test_a_move_writes_only_the_cells_that_change(self):
        """The cursor's cells, on the option it leaves and the one it
        lands on: a move is a few cells, whatever the options say."""
        w = window()
        move = w.steps()[w.choice_start]
        cells = {(r, c) for r, c, _ in move}
        self.assertEqual(cells, {(3, 2), (4, 2), (5, 2), (6, 2)})

    def test_a_move_puts_the_cursor_on_the_next_option(self):
        w = window()
        move = {(r, c): t for r, c, t in w.steps()[w.choice_start]}
        cursor = (w.tile_of(('A', 0)), w.tile_of(('A', 1)))
        fill = w.tile_of('fill')
        # option 0's cursor cell (inner column 1) cleared, option 1's set
        self.assertEqual((move[(3, 2)], move[(4, 2)]), (fill, fill))
        self.assertEqual((move[(5, 2)], move[(6, 2)]), cursor)

    def test_the_option_chosen_is_the_moves_modulo_the_options(self):
        w = window()
        start = w.choice_start
        self.assertEqual([w.chosen(start + k) for k in range(4)], [0, 1, 0, 1])

    def test_the_cursor_and_options_are_in_the_tile_set(self):
        w = window()
        for character in 'ACDE':
            w.tile_of((character, 0))


class PackedChoiceTest(TestCase):
    def test_a_packed_move_tiles_are_in_the_set(self):
        w = TextWindow(
            column=0,
            row=0,
            columns=6,
            rows=5,
            border=vwf.BORDER,
            font=vwf.FONT,
            messages=('AB',),
            choice=Choice(options=('B', 'A'), cursor='A', indent=1, moves=2),
        )
        tiles = set(range(w.tile_count))
        for step in w.steps():
            for _r, _c, tile in step:
                self.assertIn(tile, tiles)
        self.assertEqual(len(w.steps()), w.choice_start + 2)

    def test_the_fixed_fallback_keeps_the_choice(self):
        w = TextWindow(
            column=0,
            row=0,
            columns=8,
            rows=5,
            border=vwf.BORDER,
            font=vwf.FONT,
            messages=('AB',),
            choice=Choice(options=('B', 'A'), cursor='A', indent=1, moves=2),
        )
        self.assertEqual(w.fixed().choice_start + 2, len(w.fixed().steps()))


class NarrowChoiceTest(TestCase):
    def test_options_too_wide_give_up_their_indent_first(self):
        # inner 6 cells: ' A CD' needs 5 with indent 1, '>' + ' ' + 'CDE'
        w = window(
            columns=7,
            choice=Choice(options=('CDE', 'E'), cursor='A', indent=3),
        )
        self.assertEqual(w.pages(w.messages[0])[-1][-2:], ('A CDE', '  E'))

    def test_an_option_wider_than_the_window_is_refused(self):
        with self.assertRaises(ValueError):
            window(
                columns=5,
                choice=Choice(options=('CDE', 'E'), cursor='A', indent=0),
            )


class FallbacksChoiceTest(TestCase):
    def test_a_fallback_that_cannot_say_the_options_is_left_out(self):
        w = TextWindow(
            column=0,
            row=0,
            columns=6,
            rows=5,
            border=vwf.BORDER,
            font=vwf.FONT,
            messages=('AB',),
            # packed: 'A' at x 0, 'BBBB' from x 6 -> 30 px of 32; a cell
            # a glyph needs 1 + 1 + 4 = 6 cells of 4
            choice=Choice(options=('BBBB', 'A'), cursor='A', indent=0),
        )
        levels = w.fallbacks(None)
        self.assertTrue(levels)
        for fallback, _note in levels:
            self.assertTrue(fallback.packed)


class WidenedForOptionsTest(TestCase):
    def test_the_fixed_fallback_widens_on_a_screen_with_room(self):
        from types import SimpleNamespace

        w = TextWindow(
            column=2,
            row=0,
            columns=6,
            rows=5,
            border=vwf.BORDER,
            font=vwf.FONT,
            messages=('AB',),
            choice=Choice(options=('BBBB', 'A'), cursor='A', indent=0),
        )
        screen = SimpleNamespace(width=80, height=64)
        fixed = [f for f, _n in w.fallbacks(screen) if not f.packed]
        self.assertEqual(len(fixed), 1)
        self.assertEqual(fixed[0].inner_columns, 6)
        self.assertLessEqual(fixed[0].column + fixed[0].columns, 10)
