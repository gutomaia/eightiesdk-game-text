"""A text window: the same declaration on every console.

A game declares where the window sits in cells, the 9-slice its
border is drawn with, the cell font, and the messages it says:

    self.talk = TextWindow(
        column=4, row=18, columns=24, rows=8,
        border=NineSlice(...), font=CellFont({...}, rows=2),
        messages=("LINK, I'm going out for a while...",),
    )

Everything a console needs follows from that, here and console-free:

* THE TILE SET, once: the solid fill, the eight border cells, then the
  cells of only the glyphs the messages use, each drawn over the fill
  so the inside of the window is opaque, and every cell kept once.
  That is the window's whole pattern cost: tens of tiles, not frames.
* THE PAGES a message wraps into: words to the inner width, lines of
  the font's height, as many lines as the inner height holds.
* THE REVEAL as cell writes: the border one window row a step (the
  inside filled), then one glyph a step. A console's runtime writes
  those cells into the layer it resolves the window to; the room
  under it never moves.

Nothing here knows a console, a layer or a CPU.
"""

from dataclasses import dataclass, fields

CELL = 8
SPACE = ' '


@dataclass(frozen=True)
class NineSlice:
    """The border's nine cells, each 8x8 rows of RGBA tuples."""

    top_left: tuple
    top: tuple
    top_right: tuple
    left: tuple
    fill: tuple
    right: tuple
    bottom_left: tuple
    bottom: tuple
    bottom_right: tuple

    def __post_init__(self):
        for f in fields(self):
            rows = getattr(self, f.name)
            if len(rows) != CELL or any(len(r) != CELL for r in rows):
                raise ValueError(f'border cell {f.name!r} is not 8x8')
        if any(p[3] != 255 for row in self.fill for p in row):
            raise ValueError(
                'the border fill must be solid: the inside of the window '
                'is opaque'
            )


class CellFont:
    """Glyphs one cell wide and `rows` cells tall, by character.

    A glyph is a tuple of `rows` 8x8 RGBA cells, top first; clear
    pixels show the window's fill. A space is never drawn.
    """

    def __init__(self, glyphs, rows=1):
        self.rows = rows
        self.glyphs = {}
        for character, cells in dict(glyphs).items():
            cells = tuple(cells)
            if len(cells) != rows:
                raise ValueError(
                    f'glyph {character!r} has {len(cells)} cells, the '
                    f'font is {rows} tall'
                )
            self.glyphs[character] = cells

    def __contains__(self, character):
        return character == SPACE or character in self.glyphs


def _over(cell, fill):
    return tuple(
        tuple(p if p[3] else f for p, f in zip(row, frow))
        for row, frow in zip(cell, fill)
    )


class TextWindow:
    """A window of cells that border-unrolls, then types its message."""

    __eightiesdk_declaration__ = 'text_window'
    #: carried as a band field: the value is the steps drawn so far
    kind = 'text-window'

    def __init__(
        self,
        *,
        column,
        row,
        columns,
        rows,
        border,
        font,
        messages,
        unroll_frames=1,
        type_frames=1,
    ):
        if columns < 3 or rows < 2 + font.rows:
            raise ValueError(
                f'a {columns}x{rows} window has no room inside its border '
                f'for a line {font.rows} cells tall'
            )
        self.column, self.row = column, row
        self.columns, self.rows = columns, rows
        self.border, self.font = border, font
        self.messages = tuple(messages)
        self.unroll_frames, self.type_frames = unroll_frames, type_frames
        for message in self.messages:
            for character in message:
                if character not in font:
                    raise ValueError(
                        f'the window font draws no glyph for {character!r}'
                    )
        self._tiles, self._index = self._tile_set()
        #: steps the game asks to be drawn; 0 is no window
        self.value = 0

    @property
    def width(self):
        return self.columns

    @property
    def height(self):
        return self.rows

    # -- the tile set ----------------------------------------------------
    def _used(self):
        seen = {}
        for message in self.messages:
            for character in message:
                if character != SPACE:
                    seen.setdefault(character, None)
        return tuple(seen)

    def _tile_set(self):
        b = self.border
        tiles, index = [], {}

        def add(key, pixels):
            if pixels not in tiles:
                tiles.append(pixels)
            index[key] = tiles.index(pixels)

        add('fill', b.fill)
        for f in fields(b):
            if f.name != 'fill':
                add(f.name, getattr(b, f.name))
        for character in self._used():
            for n, glyph_cell in enumerate(self.font.glyphs[character]):
                add((character, n), _over(glyph_cell, b.fill))
        return tuple(tiles), index

    @property
    def tiles(self):
        return self._tiles

    @property
    def tile_count(self):
        return len(self._tiles)

    def tile_of(self, key):
        return self._index[key]

    # -- pages -----------------------------------------------------------
    @property
    def inner_columns(self):
        return self.columns - 2

    @property
    def lines_per_page(self):
        return (self.rows - 2) // self.font.rows

    def pages(self, message):
        lines, line = [], ''
        for word in message.split():
            if len(word) > self.inner_columns:
                raise ValueError(f'the word {word!r} is wider than the window')
            candidate = word if not line else f'{line} {word}'
            if len(candidate) <= self.inner_columns:
                line = candidate
            else:
                lines.append(line)
                line = word
        if line:
            lines.append(line)
        n = self.lines_per_page
        return tuple(
            tuple(lines[i : i + n]) for i in range(0, len(lines), n)
        ) or ((),)

    # -- the reveal ------------------------------------------------------
    def _border_row(self, y):
        if y == 0:
            left, mid, right = 'top_left', 'top', 'top_right'
        elif y == self.rows - 1:
            left, mid, right = 'bottom_left', 'bottom', 'bottom_right'
        else:
            left, mid, right = 'left', 'fill', 'right'
        keys = (left,) + (mid,) * (self.columns - 2) + (right,)
        return tuple(
            (self.row + y, self.column + x, self.tile_of(k))
            for x, k in enumerate(keys)
        )

    def reveal(self, page):
        """The cell writes, one step each: border rows, then glyphs."""
        steps = [self._border_row(y) for y in range(self.rows)]
        for number, line in enumerate(page):
            top = self.row + 1 + number * self.font.rows
            for x, character in enumerate(line):
                if character == SPACE:
                    continue
                steps.append(
                    tuple(
                        (
                            top + n,
                            self.column + 1 + x,
                            self.tile_of((character, n)),
                        )
                        for n in range(self.font.rows)
                    )
                )
        return tuple(steps)

    def _refill(self):
        fill = self.tile_of('fill')
        return tuple(
            (self.row + y, self.column + x, fill)
            for y in range(1, self.rows - 1)
            for x in range(1, self.columns - 1)
        )

    def steps(self, message=0):
        """Every step of a message: page one's reveal, then for each
        later page one step refilling the inside and its glyphs."""
        pages = self.pages(self.messages[message])
        steps = list(self.reveal(pages[0]))
        for page in pages[1:]:
            steps.append(self._refill())
            steps.extend(self.reveal(page)[self.rows :])
        return tuple(steps)

    @property
    def page_ends(self):
        """The step count at which each page of message 0 is whole."""
        pages = self.pages(self.messages[0])
        ends = [len(self.reveal(pages[0]))]
        for page in pages[1:]:
            ends.append(ends[-1] + len(self.reveal(page)) - self.rows + 1)
        return tuple(ends)

    def step_runs(self, message=0):
        """Every step as its write_runs: what a console's vblank drains,
        reached through the field so a resolver imports nothing."""
        return tuple(write_runs(step) for step in self.steps(message))

    @staticmethod
    def runs(writes):
        return write_runs(writes)

    def window_cells(self):
        """Every (row, column) the window covers: what closing clears."""
        return tuple(
            (self.row + y, self.column + x)
            for y in range(self.rows)
            for x in range(self.columns)
        )

    def cells(self, page, step):
        """The window's cells after `step` steps (None: not drawn)."""
        grid = [[None] * self.columns for _ in range(self.rows)]
        for writes in self.reveal(page)[:step]:
            for r, c, tile in writes:
                grid[r - self.row][c - self.column] = tile
        return grid


def write_runs(writes):
    """THE CELL-WRITE QUEUE a console's vblank drains, console-free.

    A step's (row, column, tile) writes as (row, column, tile, count)
    runs: consecutive cells of one row showing one tile are one run,
    so a border row is three runs and a glyph one run per cell. A
    console maps (row, column) to its layer's address and the tile to
    its own word, and writes each run with its auto-increment.
    """
    runs = []
    for row, column, tile in sorted(writes):
        if runs:
            r, c, t, n = runs[-1]
            if r == row and t == tile and c + n == column:
                runs[-1] = (r, c, t, n + 1)
                continue
        runs.append((row, column, tile, 1))
    return tuple(runs)


def window_tiles(window):
    return window.tiles


__all__ = [
    'CellFont',
    'NineSlice',
    'TextWindow',
    'window_tiles',
    'write_runs',
]
