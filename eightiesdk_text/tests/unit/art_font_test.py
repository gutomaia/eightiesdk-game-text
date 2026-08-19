"""A font drawn as art strings, which is how a human authors one."""

from unittest import TestCase

from eightiesdk_text.font import Font, UndefinedGlyph
from eightiesdk_text.tests.font_spec import FontSpec


class ArtFontTest(FontSpec, TestCase):
    def given_font(self):
        self.font = Font.from_art(
            {
                'F': '\n'.join(self.NARROW),
                'W': '\n'.join(self.WIDE),
            }
        )

    def when_glyph_for(self, character):
        self.glyph = self.font.glyph(character)

    def when_glyph_is_refused_for(self, character):
        with self.assertRaises(UndefinedGlyph) as caught:
            self.font.glyph(character)
        self.refusal = caught.exception

    def assert_cell_shape(self, columns, rows):
        self.assertEqual((columns, rows), (self.glyph.columns, self.glyph.rows))

    def assert_cell(self, index, rows):
        self.assertEqual(rows, self.glyph.cells[index])

    def assert_defined_characters(self, characters):
        self.assertEqual(sorted(characters), sorted(self.font.characters))

    def assert_refusal_names(self, character):
        self.assertIn(character, str(self.refusal))
