# What a cartridge stores

## Records

`record.encode` turns a list of dataclasses into `CartridgeText`.
Records are fixed size, so reaching record `n` is a shift and an add.
Anything of variable length moves to a pool and the record keeps a
16-bit offset into it; every distinct string is in the pool once, and
a list of text is a list of offsets.

The alphabet is a consequence of the content, never a declaration: the
characters the text contains, ordered by frequency, so the 254
commonest cost one byte each and the rest two through an escape tier.
Narrow characters take the low codes, a line break is a code and not a
glyph, and more characters than the code can name is
`record.TooManyGlyphs` (`record_spec`).

Byte order is the one thing that varies between the consoles this
reaches: the 6502 and Z80 families are little-endian, the 68000
big-endian. It is a parameter of the encoder, because an offset written
the wrong way round still encodes and points into nowhere.

## Glyphs

A `font.Font` holds `font.Glyph` values: grids of 8 × 8 cells, each
cell eight row bytes with bit 7 the leftmost pixel. One bit per pixel
is the one shape every console in the fleet expands into its own
depth, so the portable representation is also the small one. Sizes are
per glyph, not per font: a Latin letter is one cell wide and two tall,
a Hangul syllable two by two, and a wide glyph reads left to right then
top to bottom (`font_spec`).

`render.render` takes a typeface file and the text, not an alphabet,
and draws exactly the characters the text contains. Width is measured
per glyph; height is fixed at 16 pixels so mixed script sits on one
baseline. A height that is not whole cells and a typeface that cannot
write the script are refused (`render_spec`).

`glyphs.GlyphStore` is the cells a store's text needs, each once: the
distinct strokes and a table saying which strokes each glyph is made
of. In ROM at one bit per pixel it costs eight bytes a distinct cell
plus one slot byte per cell per glyph (`glyph_store_spec`).

## The atlas

A console draws a cell by naming a tile. `atlas.Atlas` claims a slot
per cell, remembers what it claimed, and answers the slots in reading
order with an upload plan. It does not promise adjacent slots, because
identical cells share one: Hangul syllables share their strokes, and
on a real glyph table two thirds of the cells repeat. Running out of
slots is `atlas.OutOfSlots`, by name (`atlas_spec`).

## The working set

An atlas expects every character resident, which bounds a Korean text
game at the pattern table: 454 distinct cells against 256 tiles.
`streaming.plan` treats the pattern table as a working set instead:
measured on a real corpus, the worst question screen shows 41 distinct
characters, 164 tiles of 256, so a cartridge can hold every glyph in
ROM and upload only what the screen in front of the player needs. The
store deduplicates (61 questions: 10,944 bytes unshared, 3,632 shared)
and the screen does not, because a uniform stride is free arithmetic.

## One pool, one glyph store per face

A cartridge carries one alphabet and one pool however many stores
declare into it. The resolver is called once per store and reads what
earlier stores left on the build state's retained contributions: the
last `TextContribution` carries every store so far. Each call encodes
them all again with its own store added and claims only the bytes it
adds, so the claims of all stores add up to the cartridge's text
exactly once (`shared_pool_spec`).

Stores that name the same `Typeface` share one glyph store: identical
cells share a slot across them and the later store claims only the
cells and slots it adds. Measured on three language stores over one
face, 7,506 bytes kept apart became 6,178 kept together
(`shared_glyphs_spec`).

## The claim

One claim per owner per resource: `cartridge/rom_payload_bytes`, owned
`text:<owner>`, evidence measured, its detail naming record bytes,
pool bytes, table bytes, the glyphs over their distinct cells, and the
strings already in the pool from earlier owners. The split between
text and glyphs rides on the contribution as numbers. The resolver
refuses a missing build state, a missing owner, a build state without
the claim or contribution port, and a target whose profile, cartridge
or configuration disagrees with the build state's.
