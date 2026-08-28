"""The record table at both byte orders.

Two bindings, because byte order is the only thing that differs
between the consoles this has to reach — and it is exactly where
a defect hides: an offset written the wrong way round still
encodes, still decodes to SOMETHING, and points into nowhere.
"""

from dataclasses import dataclass
from unittest import TestCase

from eightiesdk_text.record import TooManyGlyphs, encode
from eightiesdk_text.tests.record_spec import RecordTableSpec


@dataclass
class Question:
    ask: str
    alternatives: list[str]
    correct: int


class RecordTableBinding(RecordTableSpec):
    endian = None

    def given_records(self):
        self.records = [
            Question('HOW TALL?', ['2744', '2500'], 1),
            Question('WHO?', ['2500', '2850'], 0),
        ]

    def when_encoded(self):
        self.table = encode(self.records, endian=self.endian)

    def assert_record_size(self, size):
        self.assertEqual(size, self.table.record_size)

    def assert_record_count(self, count):
        self.assertEqual(count, self.table.count)

    def assert_alphabet(self, characters):
        self.assertEqual(sorted(characters), sorted(self.table.alphabet))

    def assert_commonest_character_is_first(self, character):
        self.assertEqual(character, self.table.alphabet[0])

    def assert_encoded_width_of(self, index, field, width):
        offset = self.table.offset_of(index, field)
        end = self.table.pool.index(0xFF, offset)
        self.assertEqual(width, end - offset)

    def given_records_over_the_one_byte_alphabet(self):
        # 'A' is far and away the commonest, so it takes index 0.
        # The rare four appear ONCE each and sort after every
        # filler, so they land past the direct range — which is
        # what makes them cost two bytes. Ties break on the
        # character, so this is deterministic rather than lucky.
        filler = [chr(0x4E00 + n) for n in range(300)]
        self.RARE = ''.join(chr(0x9F00 + n) for n in range(4))
        self.records = [
            Question('AAAA', ['AA'], 0),
            Question(self.RARE, ['AA'], 0),
        ] + [
            Question(''.join(filler[n : n + 6]), ['AA'], 0)
            for n in range(0, 300, 6)
        ]

    def given_records_over_every_code(self):
        filler = [chr(0x4E00 + n) for n in range(600)]
        self.records = [
            Question(''.join(filler[n : n + 6]), ['A'], 0)
            for n in range(0, 600, 6)
        ]

    def when_encoding_is_refused(self):
        with self.assertRaises(TooManyGlyphs) as caught:
            encode(self.records, endian=self.endian)
        self.refusal = caught.exception

    def assert_refusal_names_the_limit(self):
        self.assertIn('510', str(self.refusal))

    def assert_text_of(self, index, field, text):
        self.assertEqual(text, self.table.read_text(index, field))

    def assert_int_of(self, index, field, value):
        self.assertEqual(value, self.table.read_int(index, field))

    def assert_alternatives_of(self, index, texts):
        self.assertEqual(texts, self.table.read_texts(index, 'alternatives'))

    def assert_repeated_text_stored_once(self, text):
        encoded = bytes(self.table.alphabet.index(c) for c in text)
        self.assertEqual(
            1,
            self.table.pool.count(encoded),
            f'{text!r} appears more than once in the pool',
        )

    def assert_offset_byte_order(self, text):
        encoded = bytes(self.table.alphabet.index(c) for c in text)
        # where the text REALLY is, found in the pool rather than
        # asked of the decoder under test
        where = self.table.pool.index(encoded)
        expected = where.to_bytes(2, self.endian)
        self.assertNotEqual(
            expected[0],
            expected[1],
            f'offset {where} reads the same in both byte orders, '
            f'so {text!r} cannot prove this rule',
        )
        index = [record.ask for record in self.records].index(text)
        at = index * self.table.record_size + self.table.layout['ask']
        self.assertEqual(expected, self.table.records[at : at + 2])


class LittleEndianRecordTest(RecordTableBinding, TestCase):
    """The 6502 and Z80 families: NES, SNES, PC Engine, SMS, GG, GB."""

    endian = 'little'


class BigEndianRecordTest(RecordTableBinding, TestCase):
    """The 68000: Mega Drive and Neo Geo."""

    endian = 'big'
