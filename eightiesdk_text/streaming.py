"""A screen's tiles as a WORKING SET, not as the cartridge's store.

An atlas assigns every character a slot and expects them all to be
resident. That is right for a game whose tiles upload once at
boot, and it is why a Korean quiz measured out at eighteen
questions on a NES: 454 distinct cells against a 256-tile pattern
table.

THE PATTERN TABLE IS A WORKING SET. One question screen uses 47 to
119 cells — under half the table even at its worst — so a
cartridge can hold every glyph in ROM and upload only what the
screen in front of the player needs.

That changes what bounds a game. Resident tiles bound it by the
PATTERN TABLE; streamed tiles bound it by ROM, and ROM is what
banking is for.

WHAT THIS PRODUCES for each screen:
  - a grid naming LOCAL slots, 0 upward, which is what the name
    table stores and what fits one byte;
  - the global cells to copy into those slots, in order.

The global store is shared: a cell used by forty screens is kept
once and copied forty times. That is the trade — ROM for VRAM —
and it is only worth making because the copy is cheap and the
table is small.
"""


class Streamed:
    """One screen's local numbering and its upload list."""

    def __init__(self, grid, upload, reserved=1):
        self.grid = grid
        self._reserved = reserved
        #: global cell indices, in the order local slots use them
        self.upload = tuple(upload)

    def upload_slots(self):
        """The local slots this screen writes into."""
        return tuple(range(self._reserved, self._reserved + len(self.upload)))

    @property
    def slots(self):
        return len(self.upload)

    def __repr__(self):
        return f'<Streamed {self.slots} cells>'


def plan(font, screens, reserved=1):
    """Every screen's working set over one shared cell store.

    `screens` is a sequence of texts. Returns (store, streamed):
    `store` is every distinct cell the screens use, and each
    `Streamed` names its own slots from `reserved` upward.

    SLOT ZERO IS LEFT ALONE by default, because a console that
    clears its name table to zero draws that tile everywhere a
    screen does not write — and a screen's first cell landing
    there would show through every gap.
    """
    store = []
    known = {}
    streamed = []
    for text in screens:
        local = {}
        upload = []
        grid = []
        for character in text:
            if character == '\n':
                grid.append('\n')
                continue
            cells = font.glyph(character).cells
            for cell in cells:
                if cell not in known:
                    known[cell] = len(store)
                    store.append(cell)
                index = known[cell]
                if index not in local:
                    local[index] = len(upload) + reserved
                    upload.append(index)
            grid.append(
                tuple(local[known[cell]] for cell in cells)
            )
        streamed.append(Streamed(grid, upload, reserved))
    return tuple(store), tuple(streamed)
