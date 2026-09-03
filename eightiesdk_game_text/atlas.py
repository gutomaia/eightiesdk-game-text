"""Where a font's glyphs land in a console's tile memory.

A console draws a cell by naming a tile, and the simplest crust
treats a character AS a tile — `ord(character) * 16`. That works
for exactly one writing system and stops at everything else: a
glyph two cells by two has nowhere to put its other three cells.

An atlas is the indirection that lifts the limit. Ask it for a
character; it claims a slot per cell, remembers what it claimed,
and hands back the slots in reading order along with an upload
plan saying what belongs in each.

IT DOES NOT PROMISE ADJACENT SLOTS, because IDENTICAL CELLS SHARE
ONE. Measured on a real Korean glyph table: 1358 cells hold only
454 distinct ones, so two thirds of the tiles repeat and the
saving is 54% — bit-exact, since a shared cell is the same eight
bytes either way. THE DUPLICATION IS THE JAMO: syllables share
their strokes, and only 0.2% of those cells are blank, so this
is structure rather than padding.

It also makes the glyph pool SATURATE. Marginal cost fell from
102 bytes a question to 26 across a 62-question bank as the
stroke pool filled, which is the property composing syllables
from jamo was supposed to buy — reached here with no font risk
and no dependency.
"""


class OutOfSlots(Exception):
    """More cells were asked for than the tile memory holds.

    Named rather than silent because the alternative is a screen
    that draws the wrong glyphs from the last thing to occupy
    those slots, which reads as corruption and is not.
    """


class Atlas:
    """Slot assignments for the characters a screen shows.

    `capacity` is how many tiles the console's memory holds;
    `reserved` is how many at the bottom belong to someone else.
    A console wants at least one honestly blank tile — the
    fleet's crusts already zero tile 0 for it — so reserved=1 is
    the usual case rather than an exotic one.
    """

    def __init__(self, font, capacity, reserved=0):
        self.font = font
        self.capacity = capacity
        self.reserved = reserved
        self._next = reserved
        self._claimed = {}
        self._upload = {}
        self._slot_of_cell = {}

    def claim(self, character):
        """The slots this character's cells occupy, reading order.

        Asking twice returns the same slots and uploads nothing
        further: a screen naming the same character forty times
        must cost one glyph, not forty.
        """
        if character in self._claimed:
            return self._claimed[character]
        glyph = self.font.glyph(character)
        fresh = {
            cell for cell in glyph.cells if cell not in self._slot_of_cell
        }
        if self._next + len(fresh) > self.capacity:
            raise OutOfSlots(
                f'{character!r} needs {len(fresh)} more tiles; '
                f'{self._next} of {self.capacity} are taken'
            )
        slots = []
        for cell in glyph.cells:
            slot = self._slot_of_cell.get(cell)
            if slot is None:
                slot = self._next
                self._next += 1
                self._slot_of_cell[cell] = slot
                self._upload[slot] = cell
            slots.append(slot)
        slots = tuple(slots)
        self._claimed[character] = slots
        return slots

    @property
    def upload(self):
        """Slot -> cell rows, for everything claimed so far."""
        return dict(self._upload)

    @property
    def characters(self):
        return tuple(self._claimed)

    def columns_of(self, character):
        """How many cells wide the character is, so a caller can
        fold its slots into rows without re-reading the font."""
        return self.font.glyph(character).columns
