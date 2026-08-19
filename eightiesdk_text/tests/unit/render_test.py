"""Rendering through GNU Unifont, which is drawn for this size."""

from pathlib import Path
from unittest import TestCase, skipUnless

from eightiesdk_text.render import MissingGlyph, render
from eightiesdk_text.tests.render_spec import RenderFontSpec

try:
    import PIL  # noqa: F401

    PILLOW = True
except ImportError:
    PILLOW = False

# Unifont is DRAWN at 16x16 rather than scaled to it, which is why
# it survives a 16-pixel body where an outline face turns to mush.
UNIFONT = (
    Path.home()
    / 'projects/projects/korean/quiz_nes/asset_tool/asset_tool'
    / 'GnuUnifontFull-Pm9P.ttf'
)


@skipUnless(PILLOW, 'Pillow not installed')
@skipUnless(UNIFONT.exists(), 'GNU Unifont not available')
class UnifontRenderTest(RenderFontSpec, TestCase):
    LATIN_ONLY = Path(
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    )

    def given_renderer(self):
        self.typeface = UNIFONT

    def given_a_typeface_that_cannot_write_the_script(self):
        if not self.LATIN_ONLY.exists():
            self.skipTest('no Latin-only face to prove refusal with')
        self.typeface = self.LATIN_ONLY

    def when_rendering(self, text):
        self.font = render(self.typeface, text)

    def when_rendering_is_refused_for(self, text):
        with self.assertRaises(MissingGlyph) as caught:
            render(self.typeface, text)
        self.refusal = caught.exception

    def assert_characters(self, characters):
        self.assertEqual(
            sorted(set(characters)), sorted(self.font.characters)
        )

    def assert_shape_of(self, character, columns, rows):
        glyph = self.font.glyph(character)
        self.assertEqual((columns, rows), (glyph.columns, glyph.rows))

    def assert_glyph_has_ink(self, character):
        cells = self.font.glyph(character).cells
        self.assertTrue(
            any(any(cell) for cell in cells),
            f'{character!r} rendered blank',
        )

    def assert_cells_in_reading_order(self, character):
        from PIL import Image, ImageDraw, ImageFont

        glyph = self.font.glyph(character)
        # slice the drawing here, independently of the renderer
        face = ImageFont.truetype(str(self.typeface), size=16)
        image = Image.new('1', (glyph.columns * 8, 16), 0)
        ImageDraw.Draw(image).text(
            (0, 0), character, fill=1, font=face
        )
        pixels = image.load()

        def cell(column, row):
            return tuple(
                sum(
                    0x80 >> x
                    for x in range(8)
                    if pixels[column * 8 + x, row * 8 + y]
                )
                for y in range(8)
            )

        expected = [
            cell(column, row)
            for row in range(2)
            for column in range(glyph.columns)
        ]
        self.assertEqual(
            len(set(expected)),
            len(expected),
            f'{character!r} has repeated cells, so a swap would '
            f'not show — pick another character',
        )
        self.assertEqual(expected, list(glyph.cells))

    def assert_cells_are_row_bytes(self, character):
        for cell in self.font.glyph(character).cells:
            self.assertEqual(8, len(cell))
            for row in cell:
                self.assertIsInstance(row, int)
                self.assertTrue(0 <= row <= 255)

    def assert_refusal_names(self, character):
        self.assertIn(character, str(self.refusal))
