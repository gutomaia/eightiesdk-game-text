"""Stores that name the same typeface share one glyph store.

A cartridge with a question bank per language draws them all in one
face, and the digits, the punctuation and the Latin letters repeat
across every language. Measured on the real corpus: three language
stores over Unifont cost 7,506 bytes of glyphs kept apart and 6,178
kept together; the two Latin languages alone go from 1,858 to 1,002.

So a store's glyphs join the glyph store of every earlier store that
named the SAME typeface, identical cells share a slot across them,
and the later store claims only the cells and slots it adds. Two
stores naming different typefaces keep separate glyph stores, even
when the drawings happen to match: a different face is a different
set of cells until the atlas says otherwise.
"""


class SharedGlyphsSpec:
    def given_a_typeface_drawn_as_art(self, drawings):
        raise NotImplementedError()

    def given_a_second_typeface_with_the_same_drawings(self):
        raise NotImplementedError()

    def given_two_stores_saying(self, first, second):
        """Two stores over the current typeface: the first with the
        texts `first`, the second with the texts `second`."""
        raise NotImplementedError()

    def given_the_second_store_names_the_other_typeface(self):
        raise NotImplementedError()

    def when_both_stores_are_contributed(self):
        raise NotImplementedError()

    def assert_the_stores_share_one_glyph_store_holding(self, characters):
        raise NotImplementedError()

    def assert_the_second_glyph_claim_spends(self, size):
        raise NotImplementedError()

    def assert_the_stores_keep_separate_glyph_stores(self):
        raise NotImplementedError()

    def test_the_same_typeface_means_one_glyph_store(self):
        self.given_a_typeface_drawn_as_art(('A', 'B', 'Z'))
        self.given_two_stores_saying(('AB',), ('BZ',))

        self.when_both_stores_are_contributed()

        self.assert_the_stores_share_one_glyph_store_holding('ABZ')

    def test_the_second_store_claims_only_the_cells_it_adds(self):
        """HAND-COUNTED. The first store: A and B, two cells at eight
        bytes plus two slot bytes, 18. The second adds Z, one cell
        and one slot byte, 9; B is already there. Alone it would
        have claimed 18."""
        self.given_a_typeface_drawn_as_art(('A', 'B', 'Z'))
        self.given_two_stores_saying(('AB',), ('BZ',))

        self.when_both_stores_are_contributed()

        self.assert_the_second_glyph_claim_spends(9)

    def test_a_different_typeface_keeps_its_own_glyph_store(self):
        self.given_a_typeface_drawn_as_art(('A', 'B', 'Z'))
        self.given_a_second_typeface_with_the_same_drawings()
        self.given_two_stores_saying(('AB',), ('BZ',))
        self.given_the_second_store_names_the_other_typeface()

        self.when_both_stores_are_contributed()

        self.assert_the_stores_keep_separate_glyph_stores()
        self.assert_the_second_glyph_claim_spends(18)


__all__ = ['SharedGlyphsSpec']
