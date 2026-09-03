# eightiesdk-game-text

The text extension for the Eighties SDK. It knows three things:

- **the text a cartridge must store**, as records reached by address;
- **the glyphs that text uses, and how to render them**, from any
  typeface a game brings;
- **only the glyphs the text uses.** Nothing more is stored.

It does not know where text is drawn. A page, a dialogue window, a
level title on a plane above the scene: those are composed by the game
or by another extension from a surface they own and the render
primitive this package provides.

## Declaring a text store

Content is plain Python. A dataclass whose `str` and `list[str]` fields
hold text is a record stored by address:

```python
from dataclasses import dataclass
from eightiesdk_game_text.declarations import TextStore

@dataclass
class Question:
    asks: str
    answers: list[str]
    correct_answer: int

QUESTIONS = [
    Question("What is the capital of Brazil?",
             ["Rio", "São Paulo", "Salvador", "Brasília"], 3),
]

class Quiz(Game):
    def declare(self):
        self.bank = TextStore(QUESTIONS)
```

The runtime finds `self.bank` by the `__eightiesdk_declaration__` kind
on `TextStore` and hands it to the resolver this package announces:

```toml
[tool.poetry.plugins."eightiesdk.game_extensions"]
text = "eightiesdk_game_text.contribution:contribute_text"
```

`contribute_text` encodes the records once, records fixed size, every
distinct string once in a pool, an alphabet ordered by frequency so the
254 commonest characters cost one byte, and publishes what that takes
as a `cartridge/rom_payload_bytes` claim owned `text:bank`, measured
rather than estimated, through the build state's neutral claim port. It
refuses a missing build state, a missing owner, a build state without
the port, and a target that disagrees with the build state.

## The model underneath

The lower layer is console-free and was the whole of `eightiesdk-text`
before this package took its name:

| module | what it holds |
|---|---|
| `font.py` | `Font`, `Glyph`: cells of eight row bytes, one bit a pixel; a glyph is any number of cells wide and tall |
| `render.py` | a typeface file subset to the characters a text uses; a character the face cannot draw is refused by name |
| `atlas.py` | slot assignment where identical cells share one slot |
| `streaming.py` | a screen's working set over one shared cell store |
| `record.py` | dataclasses to ROM tables: fixed records, offset pool, frequency alphabet with an escape tier |

One bit per pixel is the one shape every console in the fleet expands
into its own depth, so the portable representation is also the small
one. Height is constant per typeface and width is measured per glyph:
a Latin letter is one cell wide, a Hangul syllable two, and both sit on
one baseline.

## Rules

- No platform, runtime, sibling extension or product is imported;
  `make architecture-test` refuses one.
- Every behaviour is a spec class under `eightiesdk_game_text/tests/`
  with `given_/when_/assert_` hooks; a binding subclasses it.
- Byte order is not decided here. Offsets cost two bytes either way;
  the bytes are laid by a target strategy that knows its CPU.

```
make test                the fast tier
make code_check          black, pycodestyle, flake8, bandit
make architecture-test   the import rule
```

Renamed from `eightiesdk-text` on 2026-09-03; the history is
continuous in this repository.
