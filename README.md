# eightiesdk-game-text

Fonts for the Eighties SDK.

A font maps characters to glyphs; a glyph is a grid of 8x8 cells and
a cell is eight row bytes, one bit per pixel, bit 7 leftmost. That is
the one shape every console in the fleet can expand into its own
colour depth — 2bpp planar on the NES, 4bpp planar on the Sega
8-bits, 4bpp packed on the 16-bits — so the portable representation
is also the compact one.

Glyph sizes are per glyph, not per font: a Latin letter is one cell,
a Hangul syllable is two by two.

```python
from eightiesdk_game_text.font import Font

font = Font.from_art({'?': '''
.XXXX...
XX..XX..
....XX..
...XX...
...XX...
........
...XX...
........
'''})
font.glyph('?').cells      # one 8-tuple of row bytes
font.glyph('!')            # UndefinedGlyph: named, never silently blank
```

The contract lives in `eightiesdk_game_text/tests/font_spec.py`; any new way
of building a font proves itself by subclassing it.
