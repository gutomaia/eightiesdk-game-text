# The extension in one page

The text extension knows three things: the text a cartridge must
store, as records reached by address; the glyphs that text uses and
how to render them, from any typeface; and that only the glyphs the
text uses are stored. It does not know where text is drawn. A page, a
dialogue window or a level title is composed by the game or by another
extension from a surface they own.

| Fact | Value | Where it lives |
|---|---|---|
| A record | fixed size, so record `n` is `base + n * size` | `record.RecordTable` |
| Variable-length text | moved to one pool; the record keeps a 16-bit offset | `record.encode` |
| The alphabet | built from the text actually used, ordered by frequency; the 254 commonest characters cost one byte, the rest two | `record` |
| A glyph cell | 8 × 8 pixels, eight row bytes, bit 7 the leftmost pixel, one bit a pixel | `font.Glyph` |
| Glyph height | 16 pixels, two cells, so mixed scripts share one baseline | `render` |
| Glyph width | measured per glyph: a Latin letter one cell, a Hangul syllable two | `render`, `font.Font` |
| Identical cells | share one slot; measured on a Korean glyph table, 1358 cells held 454 distinct ones | `atlas.Atlas` |
| The claim | `cartridge/rom_payload_bytes`, owned `text:<owner>`, measured | `contribution.contribute_text` |
| Byte order | a parameter of the encoder; offsets cost two bytes either way | `record.encode` |

## What it provides

The declarations
: `declarations.TextStore`, `declarations.Typeface` and the `text()`
  marker. See [The declaration](declaration.md).

The store
: `record` (dataclasses to ROM tables), `font` and `render` (a
  typeface file subset to the characters a text uses, drawn with
  Pillow), `glyphs` (the cells a store's text needs, each once),
  `atlas` (where glyphs land in tile memory), `streaming` (a screen's
  working set over one shared cell store). See [Storage](storage.md).

The resolver
: `contribution.contribute_text`, announced as the `text` game
  extension: it encodes every store a game declares into one pool,
  claims only the bytes each adds, and on a console with a text
  runtime contributes the typed code that draws a record at run time.

Drawing
: `megadrive.runtime`, the 68000 routines that draw a record on the
  Mega Drive, and `window.TextWindow`, a window of cells that
  border-unrolls and types its message, declared once for every
  console. See [Drawing](drawing.md).

## What it depends on

`eightiesdk-game` (the game nouns it may reference),
`eightiesdk-resources` (the claim records it publishes through),
`eightiesdk-platform` (the neutral runtime records), `eightiesdk-cpu`
and `eightiesdk-cpu-m68000` (the typed encoder the Mega Drive runtime
is assembled with), and Pillow, imported inside `render.render` only:
it is needed to build a font and never to use one.

No platform crust, no runtime, no sibling extension and no product is
imported. `tests/architecture_spec` reads the imports (not the source
as a string) and refuses a crossing by name; the neutral records of
`eightiesdk_platform` are not a crossing.

## How it is proven

Twelve spec files under `eightiesdk_game_text/tests`: ten bound on
the host, two bound on the Mega Drive, one of those on a booted
cartridge whose VRAM is read back. See [Proving](proving.md).
