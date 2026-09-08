"""A record's text drawn on the console, at run time, where the game
says.

THE RENDER PRIMITIVE AS STATE. This dialect has no call into an
extension: the HUD reads the game's score variable and the streamed
animation reads its facing byte. Text follows: a store declared as
`self.<owner>` gives the game three bytes, `<owner>_request`,
`<owner>_row` and `<owner>_column`; the game writes a record's index
into the request and the next V-int draws that record's first text
field with its top cells on `row` and its bottom cells on `row + 1`,
starting at `column`, a narrow character one cell wide and a wide one
two. `0xFF` in the request draws nothing, and a request that has not
changed costs the V-int a compare and nothing more.

The glyphs are 1bpp in ROM and expanded into the console's own
depth on the way to the pattern table, once, at reset, so a page
turn writes name-table words and nothing else on a console with the
room; the streamed path for the consoles without it is a later
binding of these same examples.

Bound on a real console runner: the examples read the name table
and the pattern table back off the machine's VRAM.
"""


class DrawnRecordSpec:
    #: two records over a fixed art face: two narrow characters, then
    #: a wide one followed by a narrow one
    FIRST = 'AB'
    SECOND = 'WA'

    def given_a_cartridge_with_the_two_records(self):
        raise NotImplementedError()

    def when_booted(self):
        raise NotImplementedError()

    def when_the_game_asks_for(self, index, row, column):
        raise NotImplementedError()

    def when_a_frame_passes(self):
        raise NotImplementedError()

    def assert_nothing_drawn_at(self, row, column):
        raise NotImplementedError()

    def assert_drawn_at(self, row, column, text):
        """Every character's cells sit at the expected name-table
        positions, in reading order, and each named pattern holds
        that cell's pixels."""
        raise NotImplementedError()

    def assert_within_the_vblank_window(self):
        raise NotImplementedError()

    def test_nothing_is_drawn_until_the_game_asks(self):
        self.given_a_cartridge_with_the_two_records()
        self.when_booted()
        self.when_a_frame_passes()
        self.assert_nothing_drawn_at(2, 3)

    def test_a_record_is_drawn_where_the_game_says(self):
        self.given_a_cartridge_with_the_two_records()
        self.when_booted()
        self.when_the_game_asks_for(0, 2, 3)
        self.assert_drawn_at(2, 3, self.FIRST)

    def test_a_wide_character_takes_two_columns(self):
        self.given_a_cartridge_with_the_two_records()
        self.when_booted()
        self.when_the_game_asks_for(1, 5, 1)
        self.assert_drawn_at(5, 1, self.SECOND)

    def test_another_request_redraws(self):
        self.given_a_cartridge_with_the_two_records()
        self.when_booted()
        self.when_the_game_asks_for(0, 2, 3)
        self.when_the_game_asks_for(1, 2, 3)
        self.assert_drawn_at(2, 3, self.SECOND)

    def given_a_cartridge_past_the_one_byte_alphabet(self):
        """A store whose first record uses 254 distinct characters
        and whose second uses two more: the pool writes those two as
        an escape and a second byte, and the draw must read them the
        same way. `ESCAPED` is the second record's text."""
        raise NotImplementedError()

    def test_a_character_past_the_one_byte_alphabet_is_drawn(self):
        self.given_a_cartridge_past_the_one_byte_alphabet()
        self.when_booted()
        self.when_the_game_asks_for(1, 4, 2)
        self.assert_drawn_at(4, 2, self.ESCAPED)

    def test_the_draw_fits_the_vblank_window(self):
        self.given_a_cartridge_with_the_two_records()
        self.when_booted()
        self.when_the_game_asks_for(1, 2, 3)
        self.assert_within_the_vblank_window()
