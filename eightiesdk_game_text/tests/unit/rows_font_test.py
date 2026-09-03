"""A font handed the row bytes directly, which is how a converter
that rendered them from a real typeface delivers one."""

from unittest import TestCase

from eightiesdk_game_text.font import Font, Glyph, UndefinedGlyph
from eightiesdk_game_text.tests.font_spec import FontSpec, rows_of


class RowsFontTest(FontSpec, TestCase):
    def given_font(self):
        self.font = Font(
            {
                'F': Glyph(
                    [
                        rows_of(self.NARROW, 0, 0),
                        rows_of(self.NARROW, 0, 1),
                    ],
                    columns=1,
                ),
                'W': Glyph(
                    [
                        rows_of(self.WIDE, 0, 0),
                        rows_of(self.WIDE, 1, 0),
                        rows_of(self.WIDE, 0, 1),
                        rows_of(self.WIDE, 1, 1),
                    ],
                    columns=2,
                ),
            }
        )

    def when_glyph_for(self, character):
        self.glyph = self.font.glyph(character)

    def when_glyph_is_refused_for(self, character):
        with self.assertRaises(UndefinedGlyph) as caught:
            self.font.glyph(character)
        self.refusal = caught.exception

    def assert_cell_shape(self, columns, rows):
        self.assertEqual(
            (columns, rows), (self.glyph.columns, self.glyph.rows)
        )

    def assert_cell(self, index, rows):
        self.assertEqual(rows, self.glyph.cells[index])

    def assert_defined_characters(self, characters):
        self.assertEqual(sorted(characters), sorted(self.font.characters))

    def assert_refusal_names(self, character):
        self.assertIn(character, str(self.refusal))
