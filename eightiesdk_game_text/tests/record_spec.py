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

    def given_records_with_a_width_rule(self):
        """Content whose COMMONEST character is wide and whose
        narrow characters are rarer, encoded with a rule that says
        which characters are wide. Frequency alone would put the
        wide one first; that is what makes the ordering observable."""
        raise NotImplementedError()

    def assert_codes_in_order(self, characters):
        """The alphabet, in code order, exactly."""
        raise NotImplementedError()

    def assert_wide_boundary(self, code):
        """The one number a renderer compares a code against:
        every code below it is narrow, every code from it on is
        wide."""
        raise NotImplementedError()

    def given_records_with_a_line_break(self):
        """A record whose text holds a newline between two words."""
        raise NotImplementedError()

    def assert_the_line_break_is_one_code_and_no_glyph(self):
        """The newline costs one byte in the pool, is not in the
        alphabet (nothing draws it), and reads back as itself."""
        raise NotImplementedError()

    def given_three_byte_records(self):
        """Records of one text and one byte: three bytes each."""
        raise NotImplementedError()

    def when_encoded_aligned_to(self, alignment):
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

    def test_narrow_characters_take_the_low_codes(self):
        """WIDTH IS A THRESHOLD, NOT A FLAG. The owner's original
        cartridges told a narrow glyph from a wide one by comparing
        its address with one label. Here every narrow character
        takes a code below every wide one, and frequency orders each
        half, so a renderer compares the code against one number and
        carries no width table. The escape economy is kept inside
        each half: the narrow set is small and common, so it costs
        the wide half a handful of direct codes and no more."""
        self.given_records_with_a_width_rule()
        self.when_encoded()
        self.assert_codes_in_order('ba\uac00')
        self.assert_wide_boundary(2)

    def test_a_line_break_is_a_code_and_not_a_glyph(self):
        """THE CALLER COMPOSES THE LINES. A game that knows its
        surface's width wraps its text where it wants and stores the
        break in the text; the store keeps it as one control code
        beside the terminator and the escape, outside the alphabet,
        so no face is asked to draw it and a renderer starts the next
        line where it reads it."""
        self.given_records_with_a_line_break()
        self.when_encoded()
        self.assert_the_line_break_is_one_code_and_no_glyph()

    def test_a_record_is_padded_to_the_alignment_asked(self):
        """A 68000 reads a word at an odd address and takes an
        address error; a record whose text offset lands there is a
        crash on every second page. Measured on the Mega Drive:
        a three-byte record, the second page's offset at $2A11.
        A console that reads words aligned asks for records padded
        to an even size; the pad is bytes of nothing and the text
        reads back the same."""
        self.given_three_byte_records()
        self.when_encoded_aligned_to(2)
        self.assert_record_size(4)
        self.assert_record_count(2)
        self.assert_text_of(1, 'text', 'B')

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
