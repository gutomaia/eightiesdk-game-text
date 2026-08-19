"""Plain dataclasses becoming cartridge bytes."""


class RecordTableSpec:
    """Contract spec: a list of dataclasses encodes to a table.

    Content is authored as ordinary Python — a dataclass with
    ordinary annotations, no field descriptors, no schema
    language:

        @dataclass
        class Question:
            ask: str
            alternatives: list[str]
            correct: int

    The encoder reads the annotations and lays each record out at
    a FIXED SIZE, so an 8-bit CPU reaches record n at
    `base + n * size` with a shift and an add. Anything of
    variable length — text — moves to a pool and the record keeps
    an offset into it.

    THE ALPHABET IS BUILT FROM THE TEXT ACTUALLY USED. A cartridge
    carries glyphs for the characters its content contains and no
    others, so a character costs one byte in the pool and the
    glyph table stays as small as the writing does.

    Implementations must supply an encoder for one platform's
    BYTE ORDER, and say which. That is the only thing that varies
    between consoles here: the 6502 family and the Z80 family are
    little-endian, the 68000 is big-endian, and an offset written
    the wrong way round reads as a pointer into nowhere.

    Records used by the examples are two questions sharing one
    alternative, which is what makes the sharing rule observable.
    """

    def given_records(self):
        raise NotImplementedError()

    def when_encoded(self):
        raise NotImplementedError()

    def assert_record_size(self, size):
        raise NotImplementedError()

    def assert_record_count(self, count):
        raise NotImplementedError()

    def assert_alphabet(self, characters):
        raise NotImplementedError()

    def assert_text_of(self, index, field, text):
        """Decode a record's text field back through the pool and
        the alphabet, and get the original string."""
        raise NotImplementedError()

    def assert_int_of(self, index, field, value):
        raise NotImplementedError()

    def assert_alternatives_of(self, index, texts):
        raise NotImplementedError()

    def assert_repeated_text_stored_once(self, text):
        raise NotImplementedError()

    def assert_offset_byte_order(self, text):
        """The record pointing at `text` holds that text's real
        position in the pool, written in the platform's order.

        The position must be found INDEPENDENTLY of the record
        table — by locating the text in the pool — because a
        decoder asked to check its own encoder agrees with itself
        whichever order both use. The first version of this hook
        did exactly that and passed with the byte order hardcoded.

        It must also REFUSE a text whose offset cannot tell the
        two orders apart. Offset 0 is the same bytes either way,
        and an example that happens to pick it proves nothing
        while looking like it proves everything.
        """
        raise NotImplementedError()

    def test_every_record_is_the_same_size(self):
        self.given_records()

        self.when_encoded()

        self.assert_record_size(6)

    def test_one_entry_per_record(self):
        self.given_records()

        self.when_encoded()

        self.assert_record_count(2)

    def test_text_survives_the_round_trip(self):
        self.given_records()

        self.when_encoded()

        self.assert_text_of(0, 'ask', 'HOW TALL?')

    def test_an_integer_field_keeps_its_value(self):
        self.given_records()

        self.when_encoded()

        self.assert_int_of(0, 'correct', 1)

    def test_a_list_of_text_survives_the_round_trip(self):
        self.given_records()

        self.when_encoded()

        self.assert_alternatives_of(0, ['2744', '2500'])

    def test_the_alphabet_holds_only_the_characters_used(self):
        self.given_records()

        self.when_encoded()

        self.assert_alphabet(' 024578?AHLOTW')

    def test_the_same_text_is_stored_once(self):
        self.given_records()

        self.when_encoded()

        self.assert_repeated_text_stored_once('2500')

    def test_offsets_are_written_in_the_platform_byte_order(self):
        self.given_records()

        self.when_encoded()

        # NOT the first text: it sits at offset 0, whose bytes are
        # the same in both orders.
        self.assert_offset_byte_order('WHO?')
