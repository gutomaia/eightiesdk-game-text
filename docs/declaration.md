# The declaration

Content is plain Python. A dataclass whose `str` and `list[str]`
fields hold text is a record stored by address, and a `TextStore` of
such records is what a game declares. From the package's README:

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

`TextStore` carries `__eightiesdk_declaration__ = 'text'`; the runtime,
which never imports this package, finds that kind on the class and
hands the instance to the installed `text` resolver. The dataclass with
ordinary annotations is the schema: there are no field descriptors and
no second language to keep in step with the first.

## `TextStore(records, typeface=None)`

| Rule | Refusal |
|---|---|
| at least one record | `ValueError`: a text store needs at least one record |
| records of one type | `ValueError` naming the types found |
| records are dataclasses | `ValueError` naming the type |
| `typeface` is a `Typeface` | `ValueError` naming what was given |

`TextStore.texts` is every distinct text the store carries, first
appearance first: the collection the glyph store is subset to, and
what a second store shares a pool with.

## The `text()` marker

A field annotated `Text` and holding a `text('WHO?')` value is text by
address: the same layout a plain `str` field gets, with a name a reader
can search for and a value that answers its string when called, which
is how the Python twin of a game reads what the compiled dialect reads
as an address. The encoder proves the bytes identical
(`text_marker_spec`).

## `Typeface`

Where a store's glyphs come from:

- `Typeface(path, height=16)` renders a TrueType or OpenType file at
  that height and subsets it to the characters the text uses;
- `Typeface.from_art({...})` takes glyphs drawn in source.

A typeface is one or the other, never both and never neither. A file
that is not there is refused naming the path and how many characters
it was to draw; a character the face cannot draw is refused by name
rather than drawn as a blank. A store without a typeface is stored and
claimed, and draws nothing.
