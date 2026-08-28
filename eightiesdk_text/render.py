"""Turning a real typeface into glyphs a console can hold.

A game writing in a script of thousands of characters cannot ship
a whole typeface and does not need to. It needs the characters
ITS OWN CONTENT contains, so this takes the TEXT rather than an
alphabet: the subset is a consequence of the writing, not a list
somebody has to keep in step with it.

WIDTH IS MEASURED, HEIGHT IS FIXED. Every glyph is 16 pixels tall
— two cells — so mixed script sits on one baseline and a line is
two tile rows however it is written. A Latin letter measures 8
wide and takes one cell of that height; a Hangul syllable
measures 16 and takes two. Only the advance width varies.

Pillow is imported inside the function on purpose: it is needed
to BUILD a font and never to use one, so a project that ships
pre-rendered glyphs carries no imaging dependency.
"""

from eightiesdk_text.font import CELL, Font, Glyph

BODY = 16  # the em size these glyphs are drawn at
HEIGHT_CELLS = BODY // CELL


#: A noncharacter: permanently unassigned, so whatever a face
#: draws for it IS that face's .notdef.
NONCHARACTER = '\uffff'


class MissingGlyph(Exception):
    """The typeface does not cover a character it was asked for.

    Detected by comparing against the face's own .notdef rather
    than by looking for blank output, because A MISSING GLYPH IS
    NOT BLANK — it is a box. Measured on three faces: DejaVu Sans
    and Liberation Sans draw 30- and 36-pixel boxes for a Hangul
    syllable, while GNU Unifont draws the syllable. Shipping the
    box puts a screen of identical rectangles on the cartridge,
    which reads as a font bug rather than as a missing font.
    """


def render(typeface, text, body=BODY):
    """A Font holding one glyph per distinct character in `text`."""
    from PIL import Image, ImageDraw, ImageFont

    face = ImageFont.truetype(str(typeface), size=body)
    undrawable, _ = _draw(NONCHARACTER, face, body, Image, ImageDraw)
    glyphs = {}
    missing = []
    for character in sorted(set(text)):
        cells, columns = _draw(character, face, body, Image, ImageDraw)
        if not character.isspace() and cells == undrawable:
            # EVERY missing character, not the first. A face that
            # lacks one character of a script lacks the script,
            # and reporting them one run at a time turns a single
            # wrong-font mistake into a long afternoon.
            missing.append(character)
            continue
        glyphs[character] = Glyph(cells, columns)
    if missing:
        raise MissingGlyph(
            f'{typeface} does not cover {len(missing)} of the '
            f'characters asked for: {"".join(missing)} — it draws '
            f'the same .notdef box for each that it draws for '
            f'anything it lacks'
        )
    return Font(glyphs)


def _draw(character, face, body, Image, ImageDraw):
    columns = _columns(character, face, body)
    width = columns * CELL
    image = Image.new('1', (width, body), 0)
    ImageDraw.Draw(image).text((0, 0), character, fill=1, font=face)
    pixels = image.load()
    cells = [
        tuple(
            sum(
                0x80 >> x
                for x in range(CELL)
                if pixels[column * CELL + x, row * CELL + y]
            )
            for y in range(CELL)
        )
        for row in range(body // CELL)
        for column in range(columns)
    ]
    return cells, columns


def _columns(character, face, body):
    """How many cells wide this character advances.

    Measured from the typeface rather than decided from the code
    point: a font is what knows whether a character is wide, and
    a table of Unicode ranges maintained here would be a second
    opinion drifting away from the first.
    """
    advance = face.getlength(character)
    return max(1, min(2, -int(-advance // CELL)))
