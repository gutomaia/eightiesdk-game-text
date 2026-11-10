# Proving the extension

Every behaviour is a spec class under `eightiesdk_game_text/tests` with
`given_`/`when_`/`assert_` hooks; a binding subclasses it and supplies
the wiring. The host bindings live under `tests/unit`; the Mega Drive
binds two specs of its own under `megadrive/tests`.

| Spec | Rule | Bound by |
|---|---|---|
| `ImportBoundarySpec` | no production module imports a platform, the runtime, a sibling or a product; the rule reads imports, not prose | `unit/architecture_test` |
| `RecordTableSpec` | fixed records, one pool, a frequency alphabet, line breaks as codes, too many characters refused | `unit/record_test` |
| `TextMarkerSpec` | `text()` encodes exactly like a `str` field and reads back | `unit/text_marker_test` |
| `FontSpec` | every font gives a defined character's pixels, keeps one height, reads cells in order, refuses an undefined character | fonts from art, from rows, the atlas test and the Mega Drive |
| `RenderFontSpec` | a typeface subset to the text, widths measured, cells one bit a pixel, the wrong face refused | `unit/render_test` |
| `AtlasSpec` | slots per cell, shared cells uploaded once, reserved slots never claimed, running out refused | `unit/atlas_test` |
| `GlyphStoreSpec` | a glyph only for a used character, claimed in bytes, missing faces and characters refused | `unit/glyph_store_test` |
| `TextContributionSpec` | a store costs its encoded bytes; missing state, port and owner refused; target and state agree; the resolver is announced | `unit/contribution_test` |
| `SharedPoolSpec`, `SharedGlyphsSpec` | one pool and one glyph store per face across stores; each store claims what it adds | `unit/shared_pool_test`, `unit/shared_glyphs_test` |
| `DrawnRecordSpec` | nothing drawn until asked; a record drawn where the game says; wide characters, redraws, line breaks, the vblank window | `megadrive/tests/integration/drawn_record_test`: a cartridge built with the runtime, booted on Musashi, its VRAM read back from the port traffic |
| `DrawnStoreCostSpec` | a drawn store claims the bytes its runtime places; a second store carries its own text only | `megadrive/tests/unit/drawn_store_cost_test` |

The text window keeps its examples as unit tests beside them:
`text_window_test`, `vwf_text_window_test`, `choice_test`,
`transparent_fill_test`, `resolved_page_ends_test`,
`window_under_scroll_test` and `window_under_both_scrolls_test`. The
package also binds the shared gate-tools contract of
`eightiesdk_fitness`.

`docs/red/` keeps the recorded failure that drove the fallbacks for
pages holding fewer lines: the red step of that slice, kept so the
reason for the design can be read later.

```bash
make test                the fast tier
make code_check          black, pycodestyle, flake8, bandit
make architecture-test   the import rule
```
