"""Fonts: the glyph source a console crust uploads into VRAM.

Nothing here knows a console. A glyph is a grid of 8x8 cells and
a cell is eight row bytes with bit 7 the leftmost pixel, because
that is the one shape every console in this fleet can expand into
its own colour depth — 2bpp planar on the NES, 4bpp planar on the
Sega 8-bits, 4bpp packed on the 16-bits. Storing one bit per
pixel is half of the cheapest of those and a quarter of the
dearest, so the portable representation is also the small one.

Glyph sizes are per glyph, not per font. A Latin letter is one
cell; a Hangul syllable is two by two. A font that imposed one
size could not hold both, and holding both is the point.
"""

CELL = 8


class UndefinedGlyph(LookupError):
    """Asked for a character the font does not draw.

    A refusal rather than a blank, because a screen of blanks
    reads as a rendering bug and costs an afternoon, while a
    named character costs a second.
    """


class Glyph:
    """One character's pixels, as cells in reading order."""

    def __init__(self, cells, columns):
        cells = [tuple(cell) for cell in cells]
        if columns < 1:
            raise ValueError('a glyph is at least one cell wide')
        if len(cells) % columns:
            raise ValueError(
                f'{len(cells)} cells do not fill rows of {columns}'
            )
        for cell in cells:
            if len(cell) != CELL:
                raise ValueError(
                    f'a cell is {CELL} row bytes, not {len(cell)}'
                )
        self.cells = tuple(cells)
        self.columns = columns

    @property
    def rows(self):
        return len(self.cells) // self.columns

    def __repr__(self):
        return f'<Glyph {self.columns}x{self.rows}>'


class Font:
    """A mapping from characters to glyphs, and nothing else."""

    def __init__(self, glyphs):
        self._glyphs = dict(glyphs)

    @classmethod
    def from_art(cls, drawings):
        """Build from drawings: '.' is unset, 'X' is set.

        This is how a human authors a font in source and can still
        read it a year later.
        """
        return cls(
            {
                character: _glyph_from_art(drawing)
                for character, drawing in drawings.items()
            }
        )

    def glyph(self, character):
        try:
            return self._glyphs[character]
        except KeyError:
            raise UndefinedGlyph(
                f'the font draws no glyph for {character!r}'
            ) from None

    @property
    def characters(self):
        return tuple(self._glyphs)

    def __contains__(self, character):
        return character in self._glyphs


def _glyph_from_art(drawing):
    lines = [line for line in drawing.splitlines() if line.strip()]
    if not lines:
        raise ValueError('a glyph drawing has at least one row')
    width = max(len(line) for line in lines)
    columns = -(-width // CELL)
    rows = -(-len(lines) // CELL)
    lines = [line.ljust(columns * CELL, '.') for line in lines]
    lines += ['.' * columns * CELL] * (rows * CELL - len(lines))
    cells = [
        tuple(
            sum(
                0x80 >> x
                for x in range(CELL)
                if lines[row * CELL + y][column * CELL + x] == 'X'
            )
            for y in range(CELL)
        )
        for row in range(rows)
        for column in range(columns)
    ]
    return Glyph(cells, columns)
