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

      'F'  one cell
      'W'  two cells by two

    built over a slot space of CAPACITY tiles, with slot 0
    reserved — a console needs one honestly blank tile and the
    fleet's crusts already zero tile 0 for it.

    WHAT THIS CONTRACT DOES NOT PROMISE, and the omission is the
    point: that a glyph's slots are CONSECUTIVE. Letting two
    identical cells share one slot is worth about half of a real
    glyph table, and a contract promising adjacency could never
    adopt it. Examples ask where the cells went, never where they
    went in relation to each other.
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

    def test_a_one_cell_glyph_claims_one_slot(self):
        self.given_atlas()

        self.when_claiming('F')

        self.assert_slot_count(1)

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

    def test_running_out_of_slots_is_refused_by_name(self):
        self.given_atlas()

        self.when_claiming_until_full()

        self.assert_refusal_mentions_capacity()
