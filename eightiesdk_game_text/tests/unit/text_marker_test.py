"""Python binding for the text marker contract."""

from dataclasses import dataclass
from unittest import TestCase

from eightiesdk_game_text.declarations import Text, TextStore, text
from eightiesdk_game_text.record import encode
from eightiesdk_game_text.tests.text_marker_spec import TextMarkerSpec


@dataclass
class Question:
    ask: Text
    alternatives: list[Text]
    correct: int


@dataclass
class PlainQuestion:
    ask: str
    alternatives: list[str]
    correct: int


class TextMarkerTest(TextMarkerSpec, TestCase):
    endian = 'little'

    def given_a_text(self, value):
        self.text = text(value)

    def given_two_texts_with_the_same_value(self, value):
        self.left = text(value)
        self.right = text(value)

    def given_marked_records(self):
        self.marked = [
            Question(text('HOW TALL?'), [text('2744'), text('2500')], 1),
            Question(text('WHO?'), [text('2500'), text('2850')], 0),
        ]

    def given_the_same_records_with_plain_str_fields(self):
        self.plain = [
            PlainQuestion('HOW TALL?', ['2744', '2500'], 1),
            PlainQuestion('WHO?', ['2500', '2850'], 0),
        ]

    def when_called(self):
        self.answer = self.text()

    def when_both_are_encoded(self):
        self.marked_table = encode(self.marked, endian=self.endian)
        self.plain_table = encode(self.plain, endian=self.endian)

    def when_the_marked_records_are_encoded(self):
        self.marked_table = encode(self.marked, endian=self.endian)

    def when_the_records_are_stored(self):
        self.store = TextStore(self.marked)

    def assert_it_answers(self, value):
        self.assertEqual(value, self.answer)
        self.assertIsInstance(self.answer, str)

    def assert_they_are_equal_and_hash_alike(self):
        self.assertEqual(self.left, self.right)
        self.assertEqual(hash(self.left), hash(self.right))
        self.assertNotEqual(self.left, text('2501'))

    def assert_the_two_tables_are_byte_identical(self):
        for part in ('records', 'pool', 'tables', 'alphabet'):
            self.assertEqual(
                getattr(self.plain_table, part),
                getattr(self.marked_table, part),
                f'{part} differs between marked and plain records',
            )
        self.assertEqual(
            self.plain_table.record_size, self.marked_table.record_size
        )

    def assert_text_of(self, index, field, value):
        self.assertEqual(value, self.marked_table.read_text(index, field))

    def assert_texts_of(self, index, field, values):
        self.assertEqual(values, self.marked_table.read_texts(index, field))

    def assert_the_store_lists_each_distinct_text_once(self, values):
        self.assertEqual(values, list(self.store.texts))


__all__ = ['TextMarkerTest']
