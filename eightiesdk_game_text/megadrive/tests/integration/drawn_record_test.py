"""The drawn record on the Mega Drive: a cartridge built by the
runtime with the text extension, booted on Musashi, its VRAM read
back from the port traffic."""

from dataclasses import dataclass
from unittest import TestCase, skipUnless

from eightiesdk_cpu_m68000.tests.harness import musashi_available
from eightiesdk_game_text.declarations import TextStore, Typeface
from eightiesdk_game_text.tests.drawn_record_spec import DrawnRecordSpec
from eightiesdk_game_text.tests.font_spec import FontSpec
from eightiesdk_platform_megadrive.tests.game_runner import (
    MdGameRunner,
    traced_frame,
    traced_reset,
)
from eightiesdk_platform_megadrive.video import PLANE_A, ROW_WORDS
from eightiesdk_runtime.game import Game

#: a plane A word's tile name
NAME_MASK = 0x07FF
#: one 4bpp pattern
PATTERN_BYTES = 32

FACE = Typeface.from_art(
    {
        'A': '\n'.join(FontSpec.NARROW),
        'B': '\n'.join(FontSpec.NARROW),
        'W': '\n'.join(FontSpec.WIDE),
    }
)


@dataclass
class Line:
    ask: str


class DrawnGame(Game):
    def declare(self):
        self.text = TextStore([Line('AB'), Line('WA')], typeface=FACE)

    def init(self, ctx):
        self.idle = 0

    def update(self, ctx):
        self.idle = 1

    def render(self, frame):
        # a playable game draws something; the text is not a sprite
        frame.sprite(16, 16, tile=0)


class TextEntry:
    name = 'text'

    @staticmethod
    def load():
        from eightiesdk_game_text.contribution import contribute_text

        return contribute_text


def expanded(rows):
    """The console's 4bpp pattern for eight 1bpp row bytes: colour 1
    where the bit is set, the left pixel in the high nibble."""
    out = bytearray()
    for row in rows:
        for pair in range(4):
            left = (row >> (7 - pair * 2)) & 1
            right = (row >> (6 - pair * 2)) & 1
            out.append((left << 4) | right)
    return bytes(out)


def bit_glyph(index):
    """A narrow glyph nobody could mistake for another: its top
    cell's rows are the index's bits, its bottom cell's their
    complement."""
    top = ''.join('X' if index & (0x80 >> bit) else '.' for bit in range(8))
    bottom = ''.join('.' if c == 'X' else 'X' for c in top)
    return '\n'.join([top] * 8 + [bottom] * 8)


#: 256 distinct characters, each one narrow glyph
MANY = ''.join(chr(0x100 + index) for index in range(256))
MANY_FACE = Typeface.from_art(
    {character: bit_glyph(index) for index, character in enumerate(MANY)}
)


#: declare() is read, not run: its arguments are names, so the two
#: records are named here
MANY_DIRECT = MANY[:254]
MANY_ESCAPED = MANY[254:]


class ManyGame(Game):
    def declare(self):
        self.text = TextStore(
            [Line(MANY_DIRECT), Line(MANY_ESCAPED)], typeface=MANY_FACE
        )

    def init(self, ctx):
        self.idle = 0

    def update(self, ctx):
        self.idle = 1

    def render(self, frame):
        frame.sprite(16, 16, tile=0)


FIRST_RECORDS = [Line('AB')]
SECOND_RECORDS = [Line('WA')]


class TwoStoreGame(Game):
    def declare(self):
        self.first = TextStore(FIRST_RECORDS, typeface=FACE)
        self.second = TextStore(SECOND_RECORDS, typeface=FACE)

    def init(self, ctx):
        self.idle = 0

    def update(self, ctx):
        self.idle = 1

    def render(self, frame):
        frame.sprite(16, 16, tile=0)


@skipUnless(musashi_available(), 'musashi library not built')
class DrawnRecordOnMegaDriveTest(DrawnRecordSpec, TestCase):
    STORES = ('first', 'second')

    ESCAPED = MANY_ESCAPED

    def _build(self, game, face, characters):
        from eightiesdk_platform_megadrive import builder

        self.cartridge, self.packager = builder.build_with_packager(
            game, None, extension_entries=(TextEntry(),)
        )
        self.font = face.glyphs_for(characters)

    def given_a_cartridge_with_the_two_records(self):
        self._build(DrawnGame, FACE, 'ABW')

    def given_a_cartridge_past_the_one_byte_alphabet(self):
        self._build(ManyGame, MANY_FACE, MANY)

    def given_a_cartridge_with_two_stores(self):
        self._build(TwoStoreGame, FACE, 'ABW')

    def when_the_game_asks_store_for(self, store, index, row, column):
        owner = self.STORES[store]
        self._poke(f'{owner}_row', row)
        self._poke(f'{owner}_column', column)
        self._poke(f'{owner}_request', index)
        self.when_a_frame_passes()

    def when_booted(self):
        park = self.packager.park_address
        self.patterns, _ = traced_reset(self.cartridge, park)
        self.runner = MdGameRunner()
        self.runner.run_reset(self.cartridge, park)
        self.plane = {}

    def _poke(self, name, value):
        self.runner.poke(self.packager.program.variables[name], value)

    def when_the_game_asks_for(self, index, row, column):
        self._poke('text_row', row)
        self._poke('text_column', column)
        self._poke('text_request', index)
        self.when_a_frame_passes()

    def when_a_frame_passes(self):
        vram, _ = traced_frame(self.runner)
        self.plane.update(vram)

    def _word(self, row, column):
        return self.plane.get(PLANE_A + (row * ROW_WORDS + column) * 2)

    def assert_nothing_drawn_at(self, row, column):
        self.assertIsNone(self._word(row, column))
        self.assertIsNone(self._word(row + 1, column))

    def _pattern(self, name):
        base = name * PATTERN_BYTES
        words = [self.patterns.get(base + at) for at in range(0, 32, 2)]
        self.assertNotIn(None, words, f'pattern {name} was never uploaded')
        return b''.join(word.to_bytes(2, 'big') for word in words)

    def assert_drawn_at(self, row, column, text):
        at = column
        for character in text:
            glyph = self.font.glyph(character)
            cells = iter(glyph.cells)
            for line in range(glyph.rows):
                for offset in range(glyph.columns):
                    word = self._word(row + line, at + offset)
                    self.assertIsNotNone(
                        word,
                        f'{character!r} has no cell at {row + line},'
                        f' {at + offset}',
                    )
                    self.assertEqual(
                        expanded(next(cells)),
                        self._pattern(word & NAME_MASK),
                        f'{character!r} cell {line},{offset} pattern',
                    )
            at += glyph.columns

    def assert_within_the_vblank_window(self):
        # the traced frame single-steps without a clock; the capped
        # frame is the one that knows the window (MD-008), so a fresh
        # draw of the other record runs under it
        self._poke('text_request', 0)
        self.runner.run_frame()
        self.assertFalse(self.runner.last_frame_hit_deadline)
