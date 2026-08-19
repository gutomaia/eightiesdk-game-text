"""The contract every font must satisfy, whatever it was made from."""


class FontSpec:
    """Contract spec: a font answers with the pixels of a character.

    A font is the glyph source a console crust uploads into its
    pattern table. It knows nothing about consoles. A glyph is a
    GRID OF 8x8 CELLS, each cell eight row bytes with bit 7 the
    leftmost pixel, ordered left to right and then top to bottom.
    That is the one shape every console in this fleet can expand
    into its own colour depth, and the order matters more than it
    looks: get it wrong and every wide glyph renders as four
    quarters in the wrong corners, which reads as a font bug
    rather than a packing bug.

    A font may mix glyph sizes. Latin letters are one cell wide;
    a Hangul syllable is two by two. So a glyph carries its own
    shape and the font does not impose one.

    Implementations must supply a font that defines exactly two
    characters:

      'F'  one cell, drawn as NARROW below
      'W'  two by two cells, drawn as WIDE below

    and defines nothing for 'z'. Both drawings use '.' for an
    unset pixel and 'X' for a set one, top row first.
    """

    NARROW = (
        'XXXXXXX.',
        'X.......',
        'X.......',
        'XXXXXX..',
        'X.......',
        'X.......',
        'X.......',
        '........',
    )

    # FOUR DISTINCT, NON-EMPTY QUADRANTS. The first version of
    # this drawing was a diagonal, described in this comment as
    # "deliberately asymmetric" — and its top-right and
    # bottom-left cells were BOTH BLANK, so swapping them changed
    # nothing and the cell-order example passed with the cell
    # order reversed. A drawing that cannot tell two cells apart
    # cannot prove where they went. Each quadrant here is a
    # different edge of its own cell:
    #   top-left  top row      top-right  left column
    #   bottom-left bottom row bottom-right right column
    WIDE = (
        'XXXXXXXXX.......',
        '........X.......',
        '........X.......',
        '........X.......',
        '........X.......',
        '........X.......',
        '........X.......',
        '........X.......',
        '...............X',
        '...............X',
        '...............X',
        '...............X',
        '...............X',
        '...............X',
        '...............X',
        'XXXXXXXX.......X',
    )

    def given_font(self):
        """Build the font described in the class docstring."""
        raise NotImplementedError()

    def when_glyph_for(self, character):
        raise NotImplementedError()

    def when_glyph_is_refused_for(self, character):
        """Ask for a character the font does not define, and keep
        whatever the font raised so it can be asserted on."""
        raise NotImplementedError()

    def assert_cell_shape(self, columns, rows):
        raise NotImplementedError()

    def assert_cell(self, index, rows):
        """Cell `index` in reading order holds exactly these eight
        row bytes."""
        raise NotImplementedError()

    def assert_defined_characters(self, characters):
        raise NotImplementedError()

    def assert_refusal_names(self, character):
        raise NotImplementedError()

    def test_a_defined_character_gives_its_pixels(self):
        self.given_font()

        self.when_glyph_for('F')

        self.assert_cell(0, rows_of(self.NARROW, 0, 0))

    def test_a_narrow_glyph_is_a_single_cell(self):
        self.given_font()

        self.when_glyph_for('F')

        self.assert_cell_shape(columns=1, rows=1)

    def test_a_wide_glyph_is_two_cells_by_two(self):
        self.given_font()

        self.when_glyph_for('W')

        self.assert_cell_shape(columns=2, rows=2)

    def test_a_wide_glyph_reads_left_to_right_then_top_to_bottom(self):
        self.given_font()

        self.when_glyph_for('W')

        self.assert_cell(0, rows_of(self.WIDE, 0, 0))
        self.assert_cell(1, rows_of(self.WIDE, 1, 0))
        self.assert_cell(2, rows_of(self.WIDE, 0, 1))
        self.assert_cell(3, rows_of(self.WIDE, 1, 1))

    def test_a_font_lists_the_characters_it_defines(self):
        self.given_font()

        self.assert_defined_characters('FW')

    def test_an_undefined_character_is_refused(self):
        self.given_font()

        self.when_glyph_is_refused_for('z')

        self.assert_refusal_names('z')


def rows_of(art_lines, column, row):
    """The eight row bytes of one 8x8 cell of a drawing.

    Lives in the spec because both the examples and every binding
    need to say the same thing about the same drawing, and a
    binding that computed it differently would be proving its own
    arithmetic rather than the font's.
    """
    return tuple(
        sum(
            0x80 >> x
            for x in range(8)
            if art_lines[row * 8 + y][column * 8 + x] == 'X'
        )
        for y in range(8)
    )
