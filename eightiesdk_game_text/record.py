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
#: A rare character is written as this byte and then its position
#: past the one-byte range. Two reserved bytes leave 254 codes for
#: the common tier and 256 in the escaped one.
ESCAPE = 0xFE
DIRECT = 0xFE  # codes 0x00..0xFD are written as themselves
WIDEST = DIRECT + 256


class TooManyGlyphs(Exception):
    """The content uses more distinct characters than the code can
    name, even with the escaped tier."""


class RecordTable:
    """The encoded content, and the means to read it back.

    The read_* methods exist so a test can prove the bytes decode
    to what went in. A console does the same walk in assembly.
    """

    def __init__(
        self, records, pool, alphabet, layout, record_size, endian, tables=b''
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
        return int.from_bytes(self.records[at : at + OFFSET], self.endian)

    def read_int(self, index, field):
        return self.records[self._at(index, field)]

    def _text_at(self, offset):
        out = []
        at = offset
        while self.pool[at] != TERMINATOR:
            byte = self.pool[at]
            if byte == ESCAPE:
                out.append(self.alphabet[DIRECT + self.pool[at + 1]])
                at += 2
            else:
                out.append(self.alphabet[byte])
                at += 1
        return ''.join(out), at + 1

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


#: the annotations that mean "text by address": a plain str, or the
#: Text marker from declarations, spelled either as the type or as
#: its name under `from __future__ import annotations`
_TEXT_NAMES = ('str', 'Text')


def _is_text_type(annotation):
    if isinstance(annotation, str):
        return annotation in _TEXT_NAMES
    return getattr(annotation, '__name__', None) in _TEXT_NAMES


def is_text_annotation(annotation):
    """Whether a field annotation carries text: one string, or a
    list of them. Shared with the declarations so the store and
    the encoder agree on which fields are text."""
    return _is_text_type(annotation) or _is_text_list(annotation)


def _is_text_list(annotation):
    if isinstance(annotation, str):
        return annotation.startswith('list[') and any(
            name in annotation for name in _TEXT_NAMES
        )
    return getattr(annotation, '__origin__', None) is list and any(
        _is_text_type(argument)
        for argument in getattr(annotation, '__args__', ())
    )


def _text_fields(record_type):
    for field in fields(record_type):
        if _is_text_type(field.type):
            yield field.name, False
        elif _is_text_list(field.type):
            yield field.name, True


def _alphabet_of(records, record_type):
    """The characters used, COMMONEST FIRST.

    Frequency order is what keeps everyday text at one byte per
    character: only the first 254 fit the direct code, and past
    that a character costs an escape and a second byte.
    Alphabetical order would put common and rare characters in the
    same lottery and widen ordinary words for no reason.

    Ties break on the character itself so the same content always
    encodes to the same bytes — a build that changed its ROM when
    nothing changed would be impossible to diff.
    """
    counts = {}
    for record in records:
        for name, many in _text_fields(record_type):
            value = getattr(record, name)
            for text in value if many else [value]:
                # str() because a marked value is a Text and a
                # plain one is a str; both spell the same string
                for character in str(text):
                    counts[character] = counts.get(character, 0) + 1
    return ''.join(sorted(counts, key=lambda c: (-counts[c], c)))


def encode(records, endian):
    """Encode a list of dataclass instances into a record table."""
    if not records:
        raise ValueError('a record table needs at least one record')
    record_type = type(records[0])
    alphabet = _alphabet_of(records, record_type)
    if len(alphabet) > WIDEST:
        raise TooManyGlyphs(
            f'{len(alphabet)} distinct characters; the code names '
            f'{WIDEST} — {DIRECT} directly and 256 more behind an '
            f'escape'
        )
    index_of = {char: n for n, char in enumerate(alphabet)}

    def code(character):
        index = index_of[character]
        if index < DIRECT:
            return [index]
        return [ESCAPE, index - DIRECT]

    pool = bytearray()
    stored = {}

    def put(text):
        """Text into the pool, once. The same string appearing in
        two records is one string on the cartridge — content
        repeats itself far more than it looks like it does."""
        text = str(text)
        if text in stored:
            return stored[text]
        at = len(pool)
        for character in text:
            pool.extend(code(character))
        pool.append(TERMINATOR)
        stored[text] = at
        return at

    # WHAT EACH FIELD COSTS, and where it sits in a record.
    layout = {}
    size = 0
    for field in fields(record_type):
        layout[field.name] = size
        if _is_text_type(field.type):
            size += OFFSET
        elif _is_text_list(field.type):
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
        key = tuple(str(text) for text in texts)
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
            if _is_text_type(field.type):
                body += put(value).to_bytes(OFFSET, endian)
            elif _is_text_list(field.type):
                body.append(len(value))
                body += put_sequence(value).to_bytes(OFFSET, endian)
            else:
                body.append(value)

    return RecordTable(
        bytes(body),
        bytes(pool),
        alphabet,
        layout,
        size,
        endian,
        bytes(tables),
    )
