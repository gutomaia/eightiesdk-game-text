"""Plain dataclasses becoming cartridge bytes.

Content is authored as ordinary Python. A dataclass with ordinary
annotations IS the schema — there are no field descriptors to
learn and no second language to keep in step with the first:

    @dataclass
    class Question:
        ask: str
        alternatives: list[str]
        correct: int

THE LAYOUT follows from what an 8-bit CPU can afford. Records are
FIXED SIZE, so reaching record n is `base + n * size` — a shift
and an add. Anything of variable length moves to a pool and the
record keeps a 16-bit offset into it.

THE ALPHABET IS BUILT FROM THE TEXT ACTUALLY USED. A cartridge
carries glyphs for the characters its content contains and no
others, which is what makes a character cost one byte and keeps
the glyph table as small as the writing. Nothing declares the
alphabet; it is a consequence of the content.

BYTE ORDER IS THE ONLY THING THAT VARIES between the consoles
this reaches. The 6502 and Z80 families are little-endian; the
68000 is big-endian. It is a parameter rather than a default
because an offset written the wrong way round still encodes,
still decodes to something, and points into nowhere.
"""

from dataclasses import fields

OFFSET = 2  # a 16-bit offset into the pool
COUNT = 1  # a one-byte length for a sequence
TERMINATOR = 0xFF


class TooManyGlyphs(Exception):
    """The content uses more distinct characters than a one-byte
    index can name."""


class RecordTable:
    """The encoded content, and the means to read it back.

    The read_* methods exist so a test can prove the bytes decode
    to what went in. A console does the same walk in assembly.
    """

    def __init__(
        self, records, pool, alphabet, layout, record_size, endian,
        tables=b''
    ):
        self.records = records
        self.pool = pool
        self.tables = tables
        self.alphabet = alphabet
        self.layout = layout
        self.record_size = record_size
        self.endian = endian

    @property
    def count(self):
        return len(self.records) // self.record_size

    def _at(self, index, field):
        return index * self.record_size + self.layout[field]

    def offset_of(self, index, field):
        at = self._at(index, field)
        return int.from_bytes(
            self.records[at : at + OFFSET], self.endian
        )

    def read_int(self, index, field):
        return self.records[self._at(index, field)]

    def _text_at(self, offset):
        end = self.pool.index(TERMINATOR, offset)
        return ''.join(
            self.alphabet[byte] for byte in self.pool[offset:end]
        ), end + 1

    def read_text(self, index, field):
        return self._text_at(self.offset_of(index, field))[0]

    def read_texts(self, index, field):
        at = self._at(index, field)
        how_many = self.records[at]
        table = int.from_bytes(
            self.records[at + COUNT : at + COUNT + OFFSET], self.endian
        )
        out = []
        for n in range(how_many):
            entry = table + n * OFFSET
            offset = int.from_bytes(
                self.tables[entry : entry + OFFSET], self.endian
            )
            out.append(self._text_at(offset)[0])
        return out


def _text_fields(record_type):
    for field in fields(record_type):
        if field.type in (str, 'str'):
            yield field.name, False
        elif 'list' in str(field.type):
            yield field.name, True


def _alphabet_of(records, record_type):
    used = set()
    for record in records:
        for name, many in _text_fields(record_type):
            value = getattr(record, name)
            for text in value if many else [value]:
                used.update(text)
    return ''.join(sorted(used))


def encode(records, endian):
    """Encode a list of dataclass instances into a record table."""
    if not records:
        raise ValueError('a record table needs at least one record')
    record_type = type(records[0])
    alphabet = _alphabet_of(records, record_type)
    if len(alphabet) > 256:
        raise TooManyGlyphs(
            f'{len(alphabet)} distinct characters; a one-byte index '
            f'names 256'
        )
    index_of = {char: n for n, char in enumerate(alphabet)}

    pool = bytearray()
    stored = {}

    def put(text):
        """Text into the pool, once. The same string appearing in
        two records is one string on the cartridge — content
        repeats itself far more than it looks like it does."""
        if text in stored:
            return stored[text]
        at = len(pool)
        pool.extend(index_of[c] for c in text)
        pool.append(TERMINATOR)
        stored[text] = at
        return at

    # WHAT EACH FIELD COSTS, and where it sits in a record.
    layout = {}
    size = 0
    for field in fields(record_type):
        layout[field.name] = size
        if field.type in (str, 'str'):
            size += OFFSET
        elif 'list' in str(field.type):
            size += COUNT + OFFSET
        else:
            size += 1

    # SEQUENCES ARE TABLES OF OFFSETS, not runs of text.
    # Laying a sequence's strings down consecutively would let a
    # reader walk them with no table at all — and would forbid
    # sharing, because a string already stored elsewhere is not
    # adjacent to its neighbours. Content repeats itself far more
    # than it looks like it does (two questions here answer
    # '2500'), so the two bytes an entry costs buy back more than
    # they spend, and the rule stays uniform: everything of
    # variable length is reached by an offset.
    tables = bytearray()
    table_at = {}

    def put_sequence(texts):
        key = tuple(texts)
        if key in table_at:
            return table_at[key]
        offsets = [put(text) for text in texts]
        at = len(tables)
        for offset in offsets:
            tables.extend(offset.to_bytes(OFFSET, endian))
        table_at[key] = at
        return at

    body = bytearray()
    for record in records:
        for field in fields(record_type):
            value = getattr(record, field.name)
            if field.type in (str, 'str'):
                body += put(value).to_bytes(OFFSET, endian)
            elif 'list' in str(field.type):
                body.append(len(value))
                body += put_sequence(value).to_bytes(OFFSET, endian)
            else:
                body.append(value)

    return RecordTable(
        bytes(body), bytes(pool), alphabet, layout, size, endian,
        bytes(tables),
    )
