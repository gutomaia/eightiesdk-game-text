# Drawing

The resolver knows what text costs and not where it is drawn. Two
things in this package reach a screen: a record drawn at run time on
a console with a text runtime, and a text window declared once for
every console.

## A record drawn at run time

The game asks for a draw through state, not a call, the way the HUD
reads a score variable and a streamed animation reads its facing byte.
A store declared as `self.<owner>` gives the game three bytes:

| Byte | Meaning |
|---|---|
| `<owner>_request` | the index of the record to draw; `0xFF` draws nothing; a request that has not changed costs the V-int hook its guard only |
| `<owner>_row` | the row of the record's top cells; its bottom cells go on `row + 1`; a line break continues two rows down |
| `<owner>_column` | the first column; a narrow character takes one, a wide one two |

The V-int hook draws the requested record's first text field when the
request changes (`drawn_record_spec`). Each store draws on its own
request.

`contribution.RUNTIMES` names the consoles with a runtime module:
today the Mega Drive, `megadrive.runtime`. The console gets the pool,
the store's record array and a slot table (four name-table words per
code) as ROM data; the 1bpp cells and a 256-entry expansion table; a
reset hook that expands every cell into the 4bpp pattern table once,
with the display off, into a reservation of this owner's (the console
names 2,044 patterns, so every cell stays resident); and a V-int hook
that writes the cells' names to plane A, top row then bottom row, from
the game's row and column bytes. Width is one compare against
`wide_from`, no table. The hooks clobber D0 to D2 and preserve A0 and
D3 to D7 through the stack. The escape code, for an alphabet past 254
characters, is refused by the runtime by name until the routine reads
it.

A store drawn at run time claims what its runtime places: pool and
records as text, slot table, cells and expansion table as glyphs, the
two routines beside them (`drawn_store_cost_spec`). A store on a
console without a runtime module is claim-only.

## The text window

`window.TextWindow` is the same declaration on every console. From the
module's own example:

```python
    self.talk = TextWindow(
        column=4, row=18, columns=24, rows=8,
        border=NineSlice(...), font=CellFont({...}, rows=2),
        messages=("LINK, I'm going out for a while...",),
    )
```

Everything a console needs follows from that, console-free:

- the tile set, once: the solid fill, the eight border cells, then the
  cells of only the glyphs the messages use, each drawn over the fill
  and kept once;
- the pages a message wraps into: words to the inner width, lines of
  the font's height, as many lines as the inner height holds;
- the reveal as cell writes (`write_runs`): the border one window row
  a step, then one glyph a step.

The window is carried as a band field of kind `text-window` whose value
is the steps drawn so far, one byte of game state. A console's runtime
writes those cells into the layer it resolves the window to; the room
under it never moves. Nothing in `window` knows a console, a layer or
a CPU.

| Part | What it adds |
|---|---|
| `NineSlice` | the border's nine cells |
| `CellFont` | glyphs one cell wide and `rows` tall; a space is never drawn |
| `PixelFont` | a variable-width font packed at the pen's running x; `reveal` is `'glyph'` (every cell a glyph touches, a step) or `'cell'` (only the cells it finishes) |
| `Transparent(fallback)` | an inside that shows the room through on a console whose window is a layer, and the fallback colour on one whose window replaces the room's cells |
| `Choice` | a question's options under the message, a cursor glyph that moves between them, the option chosen read from the steps past the question |
| `page_end(n)` | a `PageEnd` the build resolves for each console's fitted window, so the script and the window agree |
| `scroll`, `scroll_x` | a window placed relative to the camera's scroll when it opens, with the first and last position the camera can be at |
| `retry_with_fallbacks` | a build tried again with every window a fallback lower (`TextWindow.fallbacks`) while it fails for want of names, pattern bytes or code window, which a console learns only once the window is laid out; a build that fits is never built another way |

A window narrower than its border or shorter than one line is refused
with its size.
