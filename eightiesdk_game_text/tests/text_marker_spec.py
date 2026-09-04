"""text() marks a value as text stored by address.

A record's field carries text by address when it is annotated
``Text`` and holds a ``text(...)`` value. That is the standard for
any dataclass a cartridge carries, a question, a dialogue line, an
item name, and it is the same layout the encoder has always given
plain ``str`` fields: fixed records, one pool, an alphabet ordered
by frequency. The marker adds a name a reader can search for and a
value that answers the string when called, which is how the
Python twin of a game reads what the compiled dialect reads as an
address.

Records used by the examples are two questions sharing one
alternative, the same content the record spec uses, so the
byte-identity example compares like with like.
"""


class TextMarkerSpec:
    def given_a_text(self, value):
        raise NotImplementedError()

    def given_two_texts_with_the_same_value(self, value):
        raise NotImplementedError()

    def given_marked_records(self):
        raise NotImplementedError()

    def given_the_same_records_with_plain_str_fields(self):
        raise NotImplementedError()

    def when_called(self):
        raise NotImplementedError()

    def when_both_are_encoded(self):
        raise NotImplementedError()

    def when_the_marked_records_are_encoded(self):
        raise NotImplementedError()

    def when_the_records_are_stored(self):
        raise NotImplementedError()

    def assert_it_answers(self, value):
        raise NotImplementedError()

    def assert_they_are_equal_and_hash_alike(self):
        raise NotImplementedError()

    def assert_the_two_tables_are_byte_identical(self):
        raise NotImplementedError()

    def assert_text_of(self, index, field, value):
        raise NotImplementedError()

    def assert_texts_of(self, index, field, values):
        raise NotImplementedError()

    def assert_the_store_lists_each_distinct_text_once(self, values):
        raise NotImplementedError()

    def test_a_text_answers_its_string_when_called(self):
        self.given_a_text('HOW TALL?')

        self.when_called()

        self.assert_it_answers('HOW TALL?')

    def test_texts_are_equal_by_value(self):
        self.given_two_texts_with_the_same_value('2500')

        self.assert_they_are_equal_and_hash_alike()

    def test_marked_fields_encode_exactly_like_str_fields(self):
        """The marker changes nothing on the cartridge. It names the
        field for a reader and gives the twin a value to call; the
        bytes are the encoder's, as they always were."""
        self.given_marked_records()
        self.given_the_same_records_with_plain_str_fields()

        self.when_both_are_encoded()

        self.assert_the_two_tables_are_byte_identical()

    def test_a_marked_field_reads_back(self):
        self.given_marked_records()

        self.when_the_marked_records_are_encoded()

        self.assert_text_of(1, 'ask', 'WHO?')

    def test_a_marked_list_reads_back(self):
        self.given_marked_records()

        self.when_the_marked_records_are_encoded()

        self.assert_texts_of(0, 'alternatives', ['2744', '2500'])

    def test_a_store_lists_the_distinct_texts_it_carries(self):
        """THE COLLECTION. Every text a store carries, each once, in
        first-appearance order: '2500' is in both records and is
        listed once. This is what the glyph store is later subset
        to."""
        self.given_marked_records()

        self.when_the_records_are_stored()

        self.assert_the_store_lists_each_distinct_text_once(
            ['HOW TALL?', '2744', '2500', 'WHO?', '2850']
        )


__all__ = ['TextMarkerSpec']
