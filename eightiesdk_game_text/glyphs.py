"""The glyph store: the cells a store's text needs, each once.

Built from a font and the characters actually used, never from an
alphabet somebody declared. Identical cells share one slot through
the atlas, which on a Korean glyph table measured two thirds of the
cells as repeats, so the store is the distinct strokes and a table
saying which strokes each glyph is made of.

What it costs in ROM at one bit per pixel: eight bytes a distinct
cell, plus one slot byte per cell per glyph. Where the cells go in a
console's pattern memory, resident or streamed, is the renderer's
question and not this one.
"""

from eightiesdk_game_text.atlas import Atlas

#: one bit per pixel, eight rows: what a cell costs in ROM
CELL_BYTES = 8

#: the atlas is asked for a slot per distinct cell and must never
#: run out here; how many fit a console is a claim against a target,
#: made later by whoever uploads
UNBOUNDED = 1 << 20


class GlyphStore:
    """Every glyph a store's text uses, over one shared set of cells."""

    def __init__(self, font, characters, reserved=0):
        """`reserved` slots at the bottom belong to someone else: a
        console wants an honestly blank tile 0, so a screen store
        starts its cells above it."""
        self.font = font
        self._atlas = Atlas(font, capacity=UNBOUNDED, reserved=reserved)
        self._slots = {}
        for character in sorted(set(characters)):
            self._slots[character] = self._atlas.claim(character)

    @property
    def characters(self):
        """The characters that have a glyph: exactly the ones used."""
        return tuple(self._slots)

    @property
    def cells(self):
        """Slot -> the eight row bytes, one entry per distinct cell."""
        return self._atlas.upload

    def slots_of(self, character):
        """The cell slots this character draws with, reading order."""
        return self._slots[character]

    @property
    def size(self):
        """ROM bytes: the distinct cells, and the slot table."""
        table = sum(len(slots) for slots in self._slots.values())
        return len(self.cells) * CELL_BYTES + table

    def __repr__(self):
        return (
            f'<GlyphStore {len(self._slots)} glyphs over '
            f'{len(self.cells)} cells>'
        )


__all__ = ['CELL_BYTES', 'GlyphStore']
