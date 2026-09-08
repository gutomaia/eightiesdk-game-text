# ADR-0001: The runtime half is typed CPU code contributed through the neutral records

Date: 2026-09-08. Status: accepted.

## Context

The extension stored text by address and claimed its bytes, and no
console drew any of it: the quiz shipped pre-rendered screen maps
instead, one glyph set resident per cartridge, so three languages
were three blocks of screens and the 8-bit consoles held one. The
owner decided the layout (one record array per language, glyphs in
a bank of their own, narrow before wide, 1bpp in ROM) and asked for
three languages with the most questions a cartridge holds. Drawing a
record at run time is the missing half.

This package's boundary said "no platform, no runtime": it imported
the game nouns and the resource records only, and its architecture
example banned `eightiesdk_platform` as a family, which also banned
the neutral runtime records that live in the bare package.

## Decision

The extension draws at run time by contributing TYPED CPU code and
data through `eightiesdk_platform.runtime_contribution` (the
platform-neutral `RuntimeContribution` and its sections, imports,
exports and hooks), encoded with the CPU packages' typed encoders,
one module per console under `eightiesdk_game_text/<console>/`. It
is the shape the HUD and the streamed-animation extensions already
have. Production dependencies grow by `eightiesdk-platform` (the
neutral records), `eightiesdk-cpu` and `eightiesdk-cpu-m68000`; the
crusts and the runtime stay dev-only, for the booted proofs. The
boundary example bans the crust family `eightiesdk_platform_` and
admits the bare package.

The game asks for a draw through STATE, not a call: the store's
owner gives the game `<owner>_request`, `<owner>_row` and
`<owner>_column` (an initial-state compiler input this package
publishes, duck-typed to the runtime's), and the V-int hook draws
when the request changes. That is the dialect's one binding idiom
(the HUD's score, the animation's facing), and a `draw()` verb would
be a new dialect design, not this decision.

On the Mega Drive every glyph cell is resident (the console names
2,044 patterns; the whole corpus is 563 cells): the reset hook
expands 1bpp rows to 4bpp once, and a page turn writes name-table
words only. The routines are written inside the operand forms the
68000 encoder accepts today, with the stack standing in for the
registers it withholds; nothing here asks the CPU package for a
form.

## Consequences

- `eightiesdk-game-text` gains a per-console adapter layer; the
  domain modules (records, glyphs, fonts, streaming) stay console-
  free and the architecture example proves it.
- A store on a console without a runtime module is claim-only, as
  before.
- The escape code (alphabets past 254) is refused by the runtime by
  name until the routine reads it; the quiz corpus needs it.
- Register contract: the hooks clobber D0-D2 and preserve A0 and
  D3-D7 through the stack, per the Mega Drive runtime linker.

## Revisit when

A second console's runtime module lands (the streamed path, where
cells are not resident); when the encoder grows forms that would
halve the routine; when a surface port (R1) exists and the draw's
row and column become a surface's.
