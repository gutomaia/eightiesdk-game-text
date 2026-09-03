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
    others, so the glyph table stays as small as the writing does.

    IT IS ORDERED BY FREQUENCY, commonest first, and that ordering
    is what lets most characters cost ONE byte. A one-byte code
    names 254 of them; past that a rare character is written as an
    escape and a second byte. Alphabetical order would put common
    and rare characters in the same lottery and push everyday text
    into two bytes for no reason. A real Korean bank crossed 254
    at about twenty-five questions, so this is the ordinary case
    and not the exotic one.

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

    def assert_commonest_character_is_first(self, character):
        raise NotImplementedError()

    def assert_encoded_width_of(self, index, field, width):
        """How many bytes that record's text occupies in the pool,
        not counting its terminator."""
        raise NotImplementedError()

    def given_records_over_the_one_byte_alphabet(self):
        """Content using more than 254 distinct characters, where
        record 0 asks in the commonest character and record 1 asks
        in characters that appear once each."""
        raise NotImplementedError()

    def given_records_over_every_code(self):
        raise NotImplementedError()

    def when_encoding_is_refused(self):
        raise NotImplementedError()

    def assert_refusal_names_the_limit(self):
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

    def test_the_alphabet_is_ordered_by_frequency(self):
        self.given_records()

        self.when_encoded()

        # '0' appears five times across the two records; '2' four
        self.assert_commonest_character_is_first('0')

    def test_a_common_character_costs_one_byte(self):
        self.given_records_over_the_one_byte_alphabet()

        self.when_encoded()

        self.assert_encoded_width_of(0, 'ask', 4)

    def test_a_rare_character_costs_two(self):
        """An escape and a second byte. It is what keeps the common
        case at one byte instead of widening every code."""
        self.given_records_over_the_one_byte_alphabet()

        self.when_encoded()

        self.assert_encoded_width_of(1, 'ask', 8)

    def test_text_past_the_one_byte_alphabet_still_reads_back(self):
        self.given_records_over_the_one_byte_alphabet()

        self.when_encoded()

        self.assert_text_of(1, 'ask', self.RARE)

    def test_more_characters_than_the_code_can_name_is_refused(self):
        self.given_records_over_every_code()

        self.when_encoding_is_refused()

        self.assert_refusal_names_the_limit()

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
