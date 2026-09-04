"""The glyph store: only the glyphs the text uses, from any typeface.

A store may name the typeface its text is drawn in, a file rendered
at a height or glyphs authored as art. The extension then keeps a
glyph for every character the store's text uses and for no other:
a character the face draws but no text needs has no glyph, and a
character the text needs but the face cannot draw is a refusal that
names both. Identical cells share one slot, so the strokes Hangul
syllables repeat are stored once. What the glyphs cost in ROM is
claimed with the text under the store's one owner, and the split
is recorded on the contribution as numbers, measured.
"""


class GlyphStoreSpec:
    def given_a_typeface_drawn_as_art(self, drawings):
        raise NotImplementedError()

    def given_a_typeface_file_that_cannot_draw_hangul(self):
        raise NotImplementedError()

    def given_a_typeface_file_that_does_not_exist(self):
        raise NotImplementedError()

    def given_records_saying(self, *texts):
        raise NotImplementedError()

    def when_the_store_is_contributed(self):
        raise NotImplementedError()

    def when_contribution_is_refused(self):
        raise NotImplementedError()

    def assert_glyphs_exist_exactly_for(self, characters):
        raise NotImplementedError()

    def assert_distinct_cells_stored(self, count):
        raise NotImplementedError()

    def assert_the_glyph_claim_spends(self, size):
        raise NotImplementedError()

    def assert_the_refusal_names(self, *fragments):
        raise NotImplementedError()

    def test_a_glyph_exists_only_for_a_character_the_text_uses(self):
        self.given_a_typeface_drawn_as_art(('A', 'B', 'Z'))
        self.given_records_saying('AB', 'BA')

        self.when_the_store_is_contributed()

        self.assert_glyphs_exist_exactly_for('AB')

    def test_identical_cells_share_one_slot(self):
        """Two characters drawn with the same eight rows are two
        glyphs over ONE cell."""
        self.given_a_typeface_drawn_as_art(('I', 'l'))
        self.given_records_saying('Il')

        self.when_the_store_is_contributed()

        self.assert_glyphs_exist_exactly_for('Il')
        self.assert_distinct_cells_stored(1)

    def test_the_glyph_store_is_claimed_in_bytes(self):
        """HAND-COUNTED: two one-cell glyphs with different rows are
        two cells at eight bytes, plus one slot byte per cell per
        glyph: 16 + 2 = 18."""
        self.given_a_typeface_drawn_as_art(('A', 'B', 'Z'))
        self.given_records_saying('AB', 'BA')

        self.when_the_store_is_contributed()

        self.assert_the_glyph_claim_spends(18)

    def test_a_character_the_face_cannot_draw_is_refused_by_name(self):
        self.given_a_typeface_file_that_cannot_draw_hangul()
        self.given_records_saying('한')

        self.when_contribution_is_refused()

        self.assert_the_refusal_names('한')

    def test_a_missing_typeface_file_is_refused_by_name(self):
        self.given_a_typeface_file_that_does_not_exist()
        self.given_records_saying('AB')

        self.when_contribution_is_refused()

        self.assert_the_refusal_names('no-such-face.ttf')


__all__ = ['GlyphStoreSpec']
