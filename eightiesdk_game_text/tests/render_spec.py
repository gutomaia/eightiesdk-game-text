"""Turning a real typeface into glyphs a console can hold."""


class RenderFontSpec:
    """Contract spec: a font file becomes a Font, subset to use.

    A game that writes in a script with thousands of characters
    cannot ship a whole typeface, and does not need to: it needs
    the characters ITS OWN CONTENT contains. So rendering takes
    the text, not an alphabet — the subset is a consequence of
    the writing rather than a list somebody maintains.

    Implementations must supply a renderer over a typeface that
    covers Latin and Hangul at a 16-pixel body, and say which.

    The rules the examples pin:
      - every requested character comes back as a glyph;
      - a glyph is 1bpp cells, so it can expand into any console's
        colour depth;
      - a Latin letter is one cell wide and two tall, a Hangul
        syllable two by two — height constant, width variable;
      - nothing outside the requested text is rendered;
      - a typeface that cannot write the script is REFUSED, by
        name. This is the realistic mistake — reaching for a
        Latin face and asking it for Hangul — and it is silent
        by default: a missing glyph does not come out blank, it
        comes out as the typeface's .notdef BOX. Measured on
        three faces: DejaVu Sans and Liberation Sans both draw a
        30- and 36-pixel box for a Hangul syllable. A cartridge
        would ship a screen of identical boxes and read as a
        font bug rather than as a missing font.
    """

    LATIN = 'AB1?'
    HANGUL = '백두산'

    def given_renderer(self):
        raise NotImplementedError()

    def when_rendering(self, text):
        raise NotImplementedError()

    def given_a_typeface_that_cannot_write_the_script(self):
        """A face covering Latin and not Hangul."""
        raise NotImplementedError()

    def when_rendering_is_refused_for(self, text):
        raise NotImplementedError()

    def assert_characters(self, characters):
        raise NotImplementedError()

    def assert_shape_of(self, character, columns, rows):
        raise NotImplementedError()

    def assert_glyph_has_ink(self, character):
        raise NotImplementedError()

    def assert_cells_in_reading_order(self, character):
        """Cell n holds the part of the drawing at that position,
        left to right then top to bottom.

        The binding must slice the drawing ITSELF rather than ask
        the renderer where its cells went — otherwise it checks
        the renderer against its own arithmetic and agrees with
        any ordering. It must also refuse a character whose cells
        are not all distinct, since a glyph with two identical
        quarters cannot show that they were swapped.
        """
        raise NotImplementedError()

    def assert_cells_are_row_bytes(self, character):
        """Every cell is eight integers in 0..255 — one bit per
        pixel, which is what makes a glyph portable and small."""
        raise NotImplementedError()

    def assert_refusal_names(self, character):
        raise NotImplementedError()

    def given_a_display_height(self, pixels):
        """Render at a taller body than the 16-pixel default, as a
        title face is: the height is the typeface's, not the
        fleet's."""
        raise NotImplementedError()

    def when_rendering_is_refused_for_the_height(self, text):
        raise NotImplementedError()

    def test_a_display_face_keeps_its_measured_width(self):
        """WIDTH IS MEASURED, NOT CAPPED. Unifont's W advances 8
        pixels at 16, so 24 at 48: three cells, six tall. The first
        renderer capped every glyph at two cells wide because
        nothing wider than a Hangul syllable had been asked for,
        and a display face's wide letters would have been clipped
        without a word."""
        self.given_renderer()
        self.given_a_display_height(48)

        self.when_rendering('W')

        self.assert_shape_of('W', columns=3, rows=6)

    def test_a_syllable_at_a_display_height_stays_square(self):
        self.given_renderer()
        self.given_a_display_height(32)

        self.when_rendering(self.HANGUL)

        self.assert_shape_of('백', columns=4, rows=4)

    def test_a_height_that_is_not_whole_cells_is_refused(self):
        """20 pixels is two cells and a half; truncating to two
        would cut the descenders off silently."""
        self.given_renderer()
        self.given_a_display_height(20)

        self.when_rendering_is_refused_for_the_height('A')

        self.assert_refusal_names('20')

    def test_every_requested_character_is_rendered(self):
        self.given_renderer()

        self.when_rendering(self.LATIN)

        self.assert_characters(self.LATIN)

    def test_nothing_beyond_the_requested_text_is_rendered(self):
        self.given_renderer()

        self.when_rendering('AA  BB')

        self.assert_characters('AB ')

    def test_a_latin_letter_is_one_cell_wide_and_two_tall(self):
        self.given_renderer()

        self.when_rendering('A')

        self.assert_shape_of('A', columns=1, rows=2)

    def test_a_hangul_syllable_is_two_cells_by_two(self):
        self.given_renderer()

        self.when_rendering(self.HANGUL)

        self.assert_shape_of('백', columns=2, rows=2)

    def test_a_rendered_glyph_actually_has_ink(self):
        """A renderer that silently produces blanks passes every
        structural check and shows an empty screen."""
        self.given_renderer()

        self.when_rendering(self.HANGUL)

        self.assert_glyph_has_ink('백')

    def test_a_wide_glyph_is_cut_up_in_reading_order(self):
        """A syllable whose quarters are reordered still renders,
        still measures 2x2, and draws as scrambled nonsense."""
        self.given_renderer()

        self.when_rendering(self.HANGUL)

        self.assert_cells_in_reading_order('\ubc31')

    def test_cells_are_one_bit_per_pixel_row_bytes(self):
        self.given_renderer()

        self.when_rendering('A')

        self.assert_cells_are_row_bytes('A')

    def test_a_typeface_that_cannot_write_the_script_is_refused(self):
        self.given_a_typeface_that_cannot_write_the_script()

        self.when_rendering_is_refused_for(self.HANGUL)

        self.assert_refusal_names('\ubc31')

    def test_the_right_typeface_is_not_refused_for_the_same_text(self):
        """The refusal must be about COVERAGE and not about the
        script, or a correct font would be rejected too."""
        self.given_renderer()

        self.when_rendering(self.HANGUL)

        self.assert_characters(self.HANGUL)

    def test_a_space_is_allowed_to_be_blank(self):
        self.given_renderer()

        self.when_rendering('A B')

        self.assert_characters('AB ')
