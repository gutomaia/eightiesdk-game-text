"""Where a font's glyphs land in a console's tile memory."""


class AtlasSpec:
    """Contract spec: characters claim tile slots, and say which.

    A console draws a cell by naming a tile. A crust that treats a
    character AS a tile (`ord(c) * 16`) can only ever draw glyphs
    one cell big, which is every writing system except the one it
    was written for. An atlas is the indirection that removes
    that limit: ask it for a character, get back the slots its
    cells occupy, in reading order, and an upload plan saying what
    belongs in each slot.

    Implementations must supply an atlas over a font defining:

      'F'  one cell wide, two tall  (a Latin letter, 8x16)
      'W'  two cells by two         (a Hangul syllable, 16x16)

    built over a slot space of CAPACITY tiles, with slot 0
    reserved — a console needs one honestly blank tile and the
    fleet's crusts already zero tile 0 for it.

    WHAT THIS CONTRACT DOES NOT PROMISE, and the omission is the
    point: that a glyph's slots are CONSECUTIVE. IDENTICAL CELLS
    SHARE ONE SLOT — measured at two thirds of the cells in a real
    Korean glyph table, because syllables share their strokes — so
    a glyph's slots are wherever its cells already were. Examples
    ask where the cells went, never where they went in relation to
    each other.
    """

    CAPACITY = 8

    def given_atlas(self):
        raise NotImplementedError()

    def when_claiming(self, character):
        raise NotImplementedError()

    def when_claiming_until_full(self):
        """Claim distinct glyphs until the slot space is exhausted,
        keeping whatever the atlas raised."""
        raise NotImplementedError()

    def assert_slot_count(self, count):
        raise NotImplementedError()

    def assert_slots_are_the_same_as_last_time(self):
        raise NotImplementedError()

    def assert_reserved_slot_untouched(self, slot):
        raise NotImplementedError()

    def assert_upload_holds(self, character):
        """Every slot the character claimed carries that
        character's own cell rows, in reading order."""
        raise NotImplementedError()

    def assert_upload_slot_count(self, count):
        raise NotImplementedError()

    def assert_refusal_mentions_capacity(self):
        raise NotImplementedError()

    def when_claiming_a_glyph_whose_cells_are_all_present(self):
        """Fill the atlas to its last slot, then claim a character
        whose cells have all been claimed already."""
        raise NotImplementedError()

    def assert_it_was_not_refused(self):
        raise NotImplementedError()

    def when_claiming_two_glyphs_sharing_a_cell(self):
        """Claim two different characters whose drawings have one
        cell in common."""
        raise NotImplementedError()

    def assert_shared_cell_uploaded_once(self):
        raise NotImplementedError()

    def assert_shared_slot_appears_in_both(self):
        raise NotImplementedError()

    def test_a_narrow_glyph_claims_a_slot_for_each_of_its_two_cells(self):
        self.given_atlas()

        self.when_claiming('F')

        self.assert_slot_count(2)

    def test_a_two_by_two_glyph_claims_a_slot_for_every_cell(self):
        self.given_atlas()

        self.when_claiming('W')

        self.assert_slot_count(4)

    def test_the_upload_plan_carries_the_cells_in_reading_order(self):
        self.given_atlas()

        self.when_claiming('W')

        self.assert_upload_holds('W')

    def test_claiming_a_character_twice_reuses_its_slots(self):
        self.given_atlas()
        self.when_claiming('F')

        self.when_claiming('F')

        self.assert_slots_are_the_same_as_last_time()

    def test_a_character_claimed_twice_is_uploaded_once(self):
        self.given_atlas()
        self.when_claiming('W')

        self.when_claiming('W')

        self.assert_upload_slot_count(4)

    def test_a_reserved_slot_is_never_claimed(self):
        self.given_atlas()

        self.when_claiming('W')

        self.assert_reserved_slot_untouched(0)

    def test_two_glyphs_sharing_a_cell_share_its_slot(self):
        self.given_atlas()

        self.when_claiming_two_glyphs_sharing_a_cell()

        self.assert_shared_slot_appears_in_both()

    def test_a_shared_cell_is_uploaded_once(self):
        """The saving is real only if the tile is stored once as
        well as named twice."""
        self.given_atlas()

        self.when_claiming_two_glyphs_sharing_a_cell()

        self.assert_shared_cell_uploaded_once()

    def test_a_glyph_costs_only_its_unseen_cells(self):
        """With the atlas full to its last slot, a character whose
        cells are all already there still fits — it needs none.
        Counting a glyph's cells instead of its NEW ones would
        refuse a character the tile memory already holds, which is
        the failure sharing exists to prevent."""
        self.given_atlas()

        self.when_claiming_a_glyph_whose_cells_are_all_present()

        self.assert_it_was_not_refused()

    def test_running_out_of_slots_is_refused_by_name(self):
        self.given_atlas()

        self.when_claiming_until_full()

        self.assert_refusal_mentions_capacity()
