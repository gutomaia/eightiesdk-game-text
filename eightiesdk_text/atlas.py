"""Where a font's glyphs land in a console's tile memory.

A console draws a cell by naming a tile, and the simplest crust
treats a character AS a tile — `ord(character) * 16`. That works
for exactly one writing system and stops at everything else: a
glyph two cells by two has nowhere to put its other three cells.

An atlas is the indirection that lifts the limit. Ask it for a
character; it claims a slot per cell, remembers what it claimed,
and hands back the slots in reading order along with an upload
plan saying what belongs in each.

IT DOES NOT PROMISE ADJACENT SLOTS. Two identical cells sharing
one slot is worth about half of a real glyph table, and it is
what decides whether a dense screen fits a 256-tile pattern
table at all. A contract promising adjacency could never take
that saving, so this one does not.
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

    def claim(self, character):
        """The slots this character's cells occupy, reading order.

        Asking twice returns the same slots and uploads nothing
        further: a screen naming the same character forty times
        must cost one glyph, not forty.
        """
        if character in self._claimed:
            return self._claimed[character]
        glyph = self.font.glyph(character)
        if self._next + len(glyph.cells) > self.capacity:
            raise OutOfSlots(
                f'{character!r} needs {len(glyph.cells)} more tiles; '
                f'{self._next} of {self.capacity} are taken'
            )
        slots = tuple(
            range(self._next, self._next + len(glyph.cells))
        )
        self._next += len(glyph.cells)
        self._claimed[character] = slots
        for slot, cell in zip(slots, glyph.cells):
            self._upload[slot] = cell
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
