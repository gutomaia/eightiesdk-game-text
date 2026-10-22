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

from contextvars import ContextVar
from copy import copy
from dataclasses import dataclass, fields

CELL = 8
SPACE = ' '

#: how many fallbacks down the build in progress draws its windows
#: (see retry_with_fallbacks): 0 is the best each console can draw
_FALLBACK = ContextVar('text_window_fallback', default=0)
#: whether the attempt in progress drew a window with a fallback below
#: the one it drew (a list the retry sets per attempt; None outside one)
_LOWER = ContextVar('text_window_has_lower_fallback', default=None)
#: the port notes of the windows the attempt drew below their best
_SAID = ContextVar('text_window_fallback_notes', default=None)


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


@dataclass(frozen=True)
class Transparent:
    """The window's inside shows what is under it.

    A console whose window is a layer of its own (colour 0 draws
    nothing) shows the room through; one whose window replaces the
    room's cells paints the inside `fallback` (an RGB colour) and says
    so in its port notes."""

    fallback: tuple


_CLEAR_CELL = tuple(
    tuple((0, 0, 0, 0) for _ in range(CELL)) for _ in range(CELL)
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


class PixelFont(CellFont):
    """A variable-width font: each glyph `widths[character]` pixels
    wide (the space too), packed side by side at the pen's running x.

    The glyph's cells hold its pixels left-aligned; a width is at most
    its cells' width (8). `reveal` is how the window types it:

    * 'glyph': a step writes every cell the glyph touches as it looks
      once the glyph is drawn: the typing the cartridge shows, at the
      cost of a tile for every in-between cell.
    * 'cell': a step writes only the cells the glyph finishes (a
      line's last glyph finishes the rest): one tile per finished
      cell, the text appears a cell at a time.

    fixed() is the same glyphs as a CellFont, one cell each: what a
    console falls back to when even the finished cells do not fit.
    """

    REVEALS = ('glyph', 'cell')

    def __init__(self, glyphs, widths, rows=1, reveal='glyph'):
        super().__init__(glyphs, rows)
        if reveal not in self.REVEALS:
            raise ValueError(f'a reveal is one of {self.REVEALS}')
        self.reveal = reveal
        self.widths = dict(widths)
        for character in (SPACE, *self.glyphs):
            width = self.widths.get(character)
            if width is None:
                raise ValueError(f'the font has no width for {character!r}')
            if not 0 < width <= CELL:
                raise ValueError(
                    f'glyph {character!r} is {width} px wide; a glyph is '
                    f'1..{CELL} px'
                )

    def width(self, text):
        return sum(self.widths[c] for c in text)

    def fixed(self):
        return CellFont(self.glyphs, self.rows)


def _over(cell, fill):
    return tuple(
        tuple(p if p[3] else f for p, f in zip(row, frow))
        for row, frow in zip(cell, fill)
    )


@dataclass(frozen=True)
class Choice:
    """A question's options (ZELDA-QUESTION): said under the message on
    its last page, `indent` spaces in, the `cursor` glyph and a space
    before each, the cursor on the first. `moves` steps follow the
    question, each the option lines redrawn with the cursor one option
    further (round): the option chosen is the steps past the question
    modulo the options (TextWindow.chosen). What an answer leads to is
    the game's: its own window, declared over the same cells."""

    options: tuple
    cursor: str = '>'
    indent: int = 4
    moves: int = 16

    def __post_init__(self):
        object.__setattr__(self, 'options', tuple(self.options))
        if len(self.options) < 2:
            raise ValueError('a choice needs two options or more')
        if self.moves < 1:
            raise ValueError('a choice needs a move at least')

    def lines(self, chosen):
        """The option lines with the cursor on option `chosen`."""
        return tuple(
            _OptionLine(self, number, number == chosen)
            for number in range(len(self.options))
        )


class _OptionLine(str):
    """An option line: as text (a cell font draws it as it reads), and
    with its glyphs' pen positions for a packed font, so the option's
    text starts at the same x whether the cursor is on it or not."""

    def __new__(cls, choice, number, on):
        text = (
            SPACE * choice.indent
            + (choice.cursor if on else SPACE)
            + SPACE
            + choice.options[number]
        )
        line = super().__new__(cls, text)
        line.choice, line.number, line.on = choice, number, on
        return line

    def placed(self, font):
        """(character, pen x) of each glyph, as the font packs it."""
        choice = self.choice
        at = font.widths[SPACE] * choice.indent
        out = [(choice.cursor, at)] if self.on else []
        pen = at + font.widths[choice.cursor] + font.widths[SPACE]
        for character in choice.options[self.number]:
            out.append((character, pen))
            pen += font.widths[character]
        return out


class TextWindow:
    """A window of cells that border-unrolls, then types its message."""

    __eightiesdk_declaration__ = 'text_window'
    #: carried as a band field: the value is the steps drawn so far
    kind = 'text-window'
    #: the steps drawn are one byte of game state: up to 255 a message
    storage_width = 1

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
        fill=None,
        scroll=None,
        scroll_x=None,
        choice=None,
    ):
        #: a question's options under message 0 (Choice), or None
        self.choice = choice
        scroll = _checked_scroll(scroll)
        #: the horizontal camera scroll, stated as the vertical one
        self.scroll_x = _checked_scroll(scroll_x)
        #: PLACED RELATIVE TO THE CAMERA'S SCROLL AT OPEN: the window's
        #: row and column are on the screen, and a console whose camera
        #: moves the plane draws it where the scroll is when it opens
        self.scroll = scroll
        if columns < 3 or rows < 2 + font.rows:
            raise ValueError(
                f'a {columns}x{rows} window has no room inside its border '
                f'for a line {font.rows} cells tall'
            )
        self.column, self.row = column, row
        self.columns, self.rows = columns, rows
        #: None: the border's own fill cell; Transparent: a clear inside
        self.fill = fill
        if isinstance(fill, Transparent):
            border = NineSlice(
                **{
                    **{
                        f.name: getattr(border, f.name) for f in fields(border)
                    },
                    'fill': _CLEAR_CELL,
                }
            )
        self.border, self.font = border, font
        self.messages = tuple(messages)
        self.unroll_frames, self.type_frames = unroll_frames, type_frames
        said = self.messages + (
            (choice.cursor + ''.join(choice.options),) if choice else ()
        )
        for message in said:
            for character in message:
                if character != '\n' and character not in font:
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
        choice = getattr(self, 'choice', None)
        extra = (choice.cursor + ''.join(choice.options),) if choice else ()
        for message in self.messages + extra:
            for character in message:
                if character not in (SPACE, '\n'):
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
        if self.packed:
            for message in self.messages:
                for page in self.pages(message):
                    for number, line in enumerate(page):
                        for step in self._packed_line(line):
                            for n, c, pixels in step:
                                add(pixels, pixels)
            for line in self._option_states():
                for row in self._line_cells(line):
                    for pixels in row:
                        add(pixels, pixels)
            return tuple(tiles), index
        for character in self._used():
            for n, glyph_cell in enumerate(self.font.glyphs[character]):
                add((character, n), _over(glyph_cell, b.fill))
        return tuple(tiles), index

    def _packed_line(self, line):
        """A line's steps as (row in the line, inner column, pixels):
        one step per glyph that is not a space."""
        font, fill = self.font, self.border.fill
        width = self.inner_columns * CELL
        bitmap = [[None] * width for _ in range(font.rows * CELL)]
        pen, finished, steps = 0, 0, []

        def cell(n, c):
            return tuple(
                tuple(
                    bitmap[n * CELL + y][c * CELL + x] or fill[y][x]
                    for x in range(CELL)
                )
                for y in range(CELL)
            )

        placed = (
            line.placed(font)
            if isinstance(line, _OptionLine)
            else _pen_positions(line, font)
        )
        for i, (character, start) in enumerate(placed):
            advance = font.widths[character]
            pen = start + advance
            if character == SPACE:
                continue
            for n, glyph_cell in enumerate(font.glyphs[character]):
                for y in range(CELL):
                    for x in range(advance):
                        p = glyph_cell[y][x]
                        if p[3] and start + x < width:
                            bitmap[n * CELL + y][start + x] = p
            if font.reveal == 'glyph':
                columns = range(start // CELL, (pen - 1) // CELL + 1)
            else:
                last = i == len(placed) - 1
                upto = -(-pen // CELL) if last else pen // CELL
                columns = range(finished, upto)
                finished = max(finished, upto)
            steps.append(
                tuple(
                    (n, c, cell(n, c))
                    for n in range(font.rows)
                    for c in columns
                )
            )
        return steps

    @property
    def tiles(self):
        return self._tiles

    @property
    def see_through(self):
        """Whether the inside is declared transparent."""
        return isinstance(self.fill, Transparent)

    @property
    def opaque_tiles(self):
        """The tiles with every clear pixel the declared fallback: what
        a console draws when the window replaces the room's cells. An
        opaque window's are its tiles."""
        if not self.see_through:
            return self._tiles
        colour = (*tuple(self.fill.fallback)[:3], 255)
        return tuple(
            tuple(tuple(p if p[3] else colour for p in row) for row in tile)
            for tile in self._tiles
        )

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

    @property
    def packed(self):
        """Whether the font packs glyphs at their own widths."""
        return isinstance(self.font, PixelFont)

    def _measure(self, text):
        if self.packed:
            return self.font.width(text), self.inner_columns * CELL
        return len(text), self.inner_columns

    # a fixed-width fallback's text was broken for the declared pixels
    _rewraps = False

    def pages(self, message):
        lines = []
        if self._rewraps:  # a lone newline is a space, a blank line breaks
            message = '\n'.join(
                ' '.join(p.split('\n')) for p in message.split('\n\n')
            )
        for said in message.split('\n'):
            lines.extend(self._wrapped(said))
        n = self.lines_per_page
        pages = [list(lines[i : i + n]) for i in range(0, len(lines), n)] or [
            []
        ]
        if self.choice is not None and message == self.messages[0]:
            options = self.choice.lines(0)
            if len(options) > n:
                raise ValueError(
                    f'{len(options)} options do not fit a page of {n} lines'
                )
            if len(pages[-1]) + len(options) > n:
                pages.append([])
            pages[-1].extend(options)
        return tuple(tuple(page) for page in pages)

    def _wrapped(self, message):
        """One said line wrapped to the inner width."""
        lines, line = [], ''
        for word in message.split():
            if self._measure(word)[0] > self._measure(word)[1]:
                raise ValueError(f'the word {word!r} is wider than the window')
            candidate = word if not line else f'{line} {word}'
            size, room = self._measure(candidate)
            if size <= room:
                line = candidate
            else:
                lines.append(line)
                line = word
        if line:
            lines.append(line)
        return lines

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
        if self.packed:
            for number, line in enumerate(page):
                top = self.row + 1 + number * self.font.rows
                for step in self._packed_line(line):
                    steps.append(
                        tuple(
                            (top + n, self.column + 1 + c, self.tile_of(px))
                            for n, c, px in step
                        )
                    )
            return tuple(steps)
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
        if self.choice is not None and message == 0:
            top = (
                self.row
                + 1
                + (len(pages[-1]) - len(self.choice.options)) * self.font.rows
            )
            count = len(self.choice.options)
            for move in range(1, self.choice.moves + 1):
                steps.append(self._option_writes(top, move % count))
        return tuple(steps)

    # -- a choice ----------------------------------------------------------
    @property
    def choice_start(self):
        """The steps at which the question and its options are whole:
        each step past it is a move of the cursor."""
        return self.page_ends[-1]

    def chosen(self, step):
        """The option the cursor is on once `step` steps are drawn."""
        return max(0, step - self.choice_start) % len(self.choice.options)

    def _option_states(self):
        choice = getattr(self, 'choice', None)
        if choice is None:
            return ()
        return tuple(
            line
            for chosen in range(len(choice.options))
            for line in choice.lines(chosen)
        )

    def _line_cells(self, line):
        """Every inner cell of a line, rows of the font by inner
        columns: a glyph's cell, or the fill where it draws nothing."""
        if self.packed:
            drawn = {}
            for step in self._packed_line(line):
                for n, c, pixels in step:
                    drawn[(n, c)] = pixels
            return tuple(
                tuple(
                    drawn.get((n, c), self.border.fill)
                    for c in range(self.inner_columns)
                )
                for n in range(self.font.rows)
            )
        return tuple(
            tuple(
                (line[c], n) if c < len(line) and line[c] != SPACE else 'fill'
                for c in range(self.inner_columns)
            )
            for n in range(self.font.rows)
        )

    def _option_writes(self, top, chosen):
        writes = []
        for number, line in enumerate(self.choice.lines(chosen)):
            for n, row in enumerate(self._line_cells(line)):
                for c, key in enumerate(row):
                    writes.append(
                        (
                            top + number * self.font.rows + n,
                            self.column + 1 + c,
                            self.tile_of(key),
                        )
                    )
        return tuple(writes)

    @property
    def page_ends(self):
        """The step count at which each page of message 0 is whole."""
        pages = self.pages(self.messages[0])
        ends = [len(self.reveal(pages[0]))]
        for page in pages[1:]:
            ends.append(ends[-1] + len(self.reveal(page)) - self.rows + 1)
        return tuple(ends)

    def fitted_for(self, screen):
        """This window as a screen of `screen.width` x `screen.height`
        pixels holds it: narrowed (its messages rewrap) and moved left
        to stay on the screen, shortened to its rows. A window the
        screen holds is returned as it is. Where it sits vertically is
        the console's to resolve (a window may be raised to fit)."""
        if screen is None:
            return self
        screen_columns, screen_rows = screen.width // 8, screen.height // 8
        columns = min(self.columns, screen_columns)
        rows = min(self.rows, screen_rows)
        column = max(0, min(self.column, screen_columns - columns))
        if (columns, rows, column) == (self.columns, self.rows, self.column):
            return self
        fitted = copy(self)
        fitted.columns, fitted.rows, fitted.column = columns, rows, column
        for message in fitted.messages:
            fitted.pages(message)  # a word wider than the window refuses
        if fitted.packed:
            # packed cells depend on where lines wrap
            fitted._tiles, fitted._index = fitted._tile_set()
        return fitted

    def revealed_by_cell(self):
        """This window typing only finished cells (see PixelFont): the
        same pages and steps for fewer tiles, what a console short of
        tile names falls back to. A cell font's window is itself."""
        if not self.packed or self.font.reveal == 'cell':
            return self
        font = self.font
        cellwise = copy(self)
        cellwise.font = PixelFont(
            font.glyphs, widths=font.widths, rows=font.rows, reveal='cell'
        )
        cellwise._tiles, cellwise._index = cellwise._tile_set()
        return cellwise

    def fixed(self):
        """This window with its packed glyphs one cell each (a cell
        font's window is itself): it wraps and pages anew."""
        if not self.packed:
            return self
        fixed = copy(self)
        fixed.font = self.font.fixed()
        fixed._rewraps = True
        for message in fixed.messages:
            fixed.pages(message)  # a word wider than the window refuses
        fixed._tiles, fixed._index = fixed._tile_set()
        return fixed

    def fallbacks(self, screen):
        """The windows a console can draw for `screen`, best first, each
        with the compromise its port notes say (None: as declared): a
        glyph a step, finished cells a step, then one cell a glyph."""
        fitted = self.fitted_for(screen)
        found = [(fitted, None)]
        cellwise = fitted.revealed_by_cell()
        if cellwise is not fitted:
            found.append(
                (
                    cellwise,
                    'the variable-width text is typed a finished cell at a '
                    'time, not a glyph at a time',
                )
            )
        fixed = fitted.fixed()
        if fixed is not fitted:
            found.append(
                (
                    fixed,
                    'the variable-width text is drawn one cell a glyph (fixed '
                    'width) and rewraps',
                )
            )
        return tuple(found)

    def settle(self, screen, window):
        """A console draws `window` (one of fallbacks(screen)): the page
        ends its script reads for `screen` are that window's."""
        self.__dict__.setdefault('_settled', {})[id(screen)] = (
            screen,
            window,
        )

    def settled_for(self, screen):
        screen_window = self.__dict__.get('_settled', {}).get(id(screen))
        if screen_window is not None and screen_window[0] is screen:
            return screen_window[1]
        return self.drawn_for(screen)[0]

    def drawn_for(self, screen):
        """(window, port note) the build in progress draws for
        `screen`: its fallbacks as far down as the build has retried
        (see retry_with_fallbacks)."""
        found = self.fallbacks(screen)
        level = min(_FALLBACK.get(), len(found) - 1)
        lower = _LOWER.get()
        if lower is not None and level < len(found) - 1:
            lower.append(self)
        said = _SAID.get()
        if said is not None and found[level][1]:
            said.setdefault(found[level][1], None)
        return found[level]

    def scroll_for(self, screen):
        """The scroll with its positions resolved for `screen` (a
        camera limit is a number the build resolves per console); on
        the host, the declared numbers."""
        return _resolved_scroll(self.scroll, screen)

    def scroll_x_for(self, screen):
        """The horizontal scroll, resolved as `scroll_for`."""
        return _resolved_scroll(getattr(self, 'scroll_x', None), screen)

    def page_end(self, page):
        """The step at which `page` of message 0 is whole, on the
        screen of the console the build is for (see PageEnd)."""
        return PageEnd(self, page)

    def step_runs(self, message=0):
        """Every step as its write_runs: what a console's vblank drains,
        reached through the field so a resolver imports nothing."""
        return tuple(write_runs(step) for step in self.steps(message))

    def streamed(self, names, message=0):
        """THE TILES LOADED AS THE STEPS NEED THEM, for a console with
        fewer tile names than this window has tiles: per step, (loads,
        runs). `loads` are (name, tile) to copy into the console's
        pattern memory before the step's `runs` (write_runs, with names
        for tiles). A name no cell shows is reused (the one freed
        longest ago first; one a step frees is free from the next), and
        a cell the only one showing its name is redrawn by loading that
        name. Refused (ValueError) when more tiles show at once than
        `names` holds; streamed_names_needed() says how many do."""
        names = tuple(names)
        free = list(names)  # never used first, then oldest freed
        loaded, refs, grid, out = {}, {}, {}, []
        for step in self.steps(message):
            loads, writes, freed = [], [], []
            for row, column, tile in step:
                old = grid.get((row, column))
                resident = next(
                    (n for n, t in loaded.items() if t == tile), None
                )
                if resident is not None:
                    name = resident
                    if not refs.get(name) and name in free:
                        free.remove(name)
                elif old is not None and refs[old] == 1:
                    # the only cell showing it: redrawn in place
                    loaded[old] = tile
                    loads.append((old, tile))
                    continue
                else:
                    if not free:
                        raise ValueError(
                            f'the window shows more tiles at once than '
                            f'the {len(names)} names hold'
                        )
                    name = free.pop(0)
                    loaded[name] = tile
                    loads.append((name, tile))
                if name == old:
                    continue
                refs[name] = refs.get(name, 0) + 1
                if old is not None:
                    refs[old] -= 1
                    if not refs[old]:
                        freed.append(old)
                grid[(row, column)] = name
                writes.append((row, column, name))
            free.extend(n for n in freed if not refs[n])
            out.append((tuple(loads), write_runs(writes)))
        return tuple(out)

    def streamed_names_needed(self, message=0):
        """The fewest names streamed() draws this window in."""
        low, high = 1, self.tile_count
        while low < high:
            middle = (low + high) // 2
            try:
                self.streamed(range(middle), message)
            except ValueError:
                low = middle + 1
            else:
                high = middle
        return low

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


def _pen_positions(line, font):
    out, pen = [], 0
    for character in line:
        out.append((character, pen))
        pen += font.widths[character]
    return out


class PageEnd(int):
    """A page end the build resolves for its console: the game
    declares `PAGE = window.page_end(0)` once, and every console reads
    it from the window fitted to its own screen. Where no console is
    (a script run on the host) it is the declared window's number."""

    def __new__(cls, window, page):
        end = super().__new__(cls, _clamped(window.page_ends, page))
        end.window, end.page = window, page
        return end

    def __eightiesdk_resolve__(self, screen):
        return _clamped(self.window.settled_for(screen).page_ends, self.page)

    def __repr__(self):
        return f'PageEnd(page={self.page}, declared={int(self)})'


def retry_with_fallbacks(
    attempt, ran_out=None, levels=2, notes=None, told=None
):
    """attempt(), built again with every text window a fallback lower
    (TextWindow.fallbacks) while it fails and drew a window with a
    fallback left: a console learns it ran out of names, pattern bytes
    or its code window only once the window is laid out. `ran_out`
    narrows the failures retried (default: any). A build that fits is
    never built another way. `notes` (the build's port-note list) loses
    what a failed attempt said; `told(note)` hears, once each, what the
    windows of the build that fit gave up."""
    first = _FALLBACK.get()
    for level in range(first, levels + 1):
        token = _FALLBACK.set(level)
        lower, said = [], {}
        lowered, saying = _LOWER.set(lower), _SAID.set(said)
        kept = len(notes) if notes is not None else 0
        try:
            built = attempt()
            for note in said if told is not None else ():
                told(note)
            return built
        except Exception as error:
            if not lower or (ran_out is not None and not ran_out(error)):
                raise
            if notes is not None:
                # the build it said them of is not the one that ships
                del notes[kept:]
        finally:
            _SAID.reset(saying)
            _LOWER.reset(lowered)
            _FALLBACK.reset(token)


def _clamped(ends, page):
    """A page past the last is the last: the same script reads a page
    a wider screen does not have."""
    return ends[min(page, len(ends) - 1)]


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
    'PixelFont',
    'NineSlice',
    'PageEnd',
    'TextWindow',
    'window_tiles',
    'retry_with_fallbacks',
    'write_runs',
]


def _checked_scroll(scroll):
    """A camera scroll (variable, first, last), or None."""
    if scroll is None:
        return None
    scroll = tuple(scroll)
    if (
        len(scroll) != 3
        or not isinstance(scroll[0], str)
        or any(
            isinstance(v, bool) or not isinstance(v, int) for v in scroll[1:]
        )
        or scroll[1] > scroll[2]
    ):
        raise ValueError(
            'a text window scroll is (variable, first, last): the '
            'camera variable it opens under and the first and '
            'last position the camera can be at'
        )
    return scroll


def _resolved_scroll(scroll, screen):
    """`scroll` with its positions resolved for `screen`."""
    if scroll is None:
        return None
    variable, *limits = scroll
    return (variable,) + tuple(
        (
            type(v).__eightiesdk_resolve__(v, screen)
            if screen is not None
            and hasattr(type(v), '__eightiesdk_resolve__')
            else int(v)
        )
        for v in limits
    )
