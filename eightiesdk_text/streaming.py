"""A screen's tiles as a WORKING SET, not as the cartridge's store.

An atlas assigns every character a slot and expects them all to be
resident. That is right for a game whose tiles upload once at
boot, and it is why a Korean quiz measured out at eighteen
questions on a NES: 454 distinct cells against a 256-tile pattern
table.

THE PATTERN TABLE IS A WORKING SET. Measured on a real corpus, the
worst question screen shows 41 distinct characters — 164 tiles of
256 at four apiece. So a cartridge can hold every glyph in ROM and
upload only what the screen in front of the player needs, which
moves the bound from the pattern table to ROM. ROM is what banking
is for.

SHARED IN ROM, NOT IN VRAM, and the two halves are decided by
different numbers:

    in ROM, 1bpp at 8 bytes a cell
        61 questions unshared   10,944 bytes   over two 4KB banks
        61 questions shared      3,632 bytes   under half a bank
    in VRAM
        worst screen unshared      164 tiles   fits 256
        worst screen shared        119 tiles   also fits

  Sharing is the difference between fitting two banks and not. In
  VRAM it is the difference between two numbers that both fit, and
  it costs a per-screen slot table where a UNIFORM STRIDE is free
  arithmetic: character c owns tiles c*stride, which a console can
  compute without looking anything up.

  So the store deduplicates and the screen does not. A cell forty
  screens use is kept once and copied wherever each screen wants
  it.
"""


class Streamed:
    """One screen's characters and where their cells come from."""

    def __init__(self, characters, cells, stride, reserved):
        #: the screen's characters, in the order it uploads them
        self.characters = tuple(characters)
        #: per character, the store indices of its cells
        self.cells = tuple(cells)
        self.stride = stride
        self.reserved = reserved

    def tile(self, character, quadrant=0):
        """The tile number this screen draws `character` with.

        FREE ARITHMETIC, which is the point of the uniform stride:
        the console multiplies an ordinal and adds, where a shared
        layout would make it read a table per cell.
        """
        return (
            self.reserved
            + self.characters.index(character) * self.stride
            + quadrant
        )

    @property
    def tiles(self):
        return len(self.characters) * self.stride

    def __repr__(self):
        return f'<Streamed {len(self.characters)} characters>'


def plan(font, screens, stride=4, reserved=0):
    """Every screen's working set over one shared cell store.

    `screens` is a sequence of texts. Returns (store, streamed).
    The store holds each DISTINCT cell once; a screen names its
    characters in upload order and each keeps the store indices of
    its own cells, in reading order.

    `stride` is how many tiles a character is given whatever it
    needs — four for a script whose widest glyph is two cells by
    two. Uniform on purpose: it costs a narrow character two empty
    tiles and buys a tile number a console can compute.
    """
    store = []
    known = {}
    streamed = []
    for text in screens:
        characters = []
        cells = []
        for character in dict.fromkeys(text):
            if character == '\n':
                continue
            glyph = font.glyph(character)
            if len(glyph.cells) > stride:
                raise ValueError(
                    f'{character!r} needs {len(glyph.cells)} cells and '
                    f'the stride is {stride}: its last cells would be '
                    f'drawn from the next character'
                )
            indices = []
            for cell in glyph.cells:
                if cell not in known:
                    known[cell] = len(store)
                    store.append(cell)
                indices.append(known[cell])
            characters.append(character)
            cells.append(tuple(indices))
        streamed.append(Streamed(characters, cells, stride, reserved))
    return tuple(store), tuple(streamed)
