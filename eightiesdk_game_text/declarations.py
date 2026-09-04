"""What a game declares to this extension.

A game assigns a text store in ``declare()``:

    def declare(self):
        self.bank = TextStore(QUESTIONS)

and the runtime, which never imports this package, finds the
``__eightiesdk_declaration__`` kind on the class and hands the
instance to the installed ``text`` resolver. The store is records:
plain dataclasses whose ``str`` and ``list[str]`` fields are text by
address, the shape ``record.encode`` has taken since the package
began.

The store knows the text it must carry. It does not know a page, a
window, a plane or a console; whoever renders asks for an address
and a surface, and neither of those lives here.
"""

from dataclasses import fields, is_dataclass
from pathlib import Path

from eightiesdk_game_text.font import Font
from eightiesdk_game_text.record import is_text_annotation


class Typeface:
    """Where a store's glyphs come from: a file, or authored art.

    ``Typeface(path, height=16)`` renders a TrueType or OpenType file
    at that height and subsets it to the characters a text uses.
    ``Typeface.from_art({...})`` takes glyphs drawn in source. Either
    way the store keeps only the glyphs its text needs, and a
    character the face cannot draw, or a file that is not there, is a
    refusal that names it rather than a blank on the glass.
    """

    def __init__(self, path=None, height=16, drawings=None):
        if (path is None) == (drawings is None):
            raise ValueError(
                'a typeface is a file rendered at a height, or drawings, '
                'not both and not neither'
            )
        self.path = None if path is None else Path(path)
        self.height = height
        self._font = None if drawings is None else Font.from_art(drawings)

    @classmethod
    def from_art(cls, drawings):
        return cls(drawings=dict(drawings))

    def glyphs_for(self, characters):
        """A Font holding exactly the characters asked for."""
        characters = ''.join(sorted(set(characters)))
        if self._font is not None:
            return Font(
                {
                    character: self._font.glyph(character)
                    for character in characters
                }
            )
        from eightiesdk_game_text.render import MissingGlyph, render

        if not self.path.exists():
            raise ValueError(
                f'typeface file {self.path} does not exist: the glyphs '
                f'for {len(characters)} characters cannot be drawn'
            )
        try:
            return render(self.path, characters, body=self.height)
        except MissingGlyph as missing:
            raise ValueError(str(missing)) from None

    def __repr__(self):
        if self._font is not None:
            return f'<Typeface art, {len(self._font.characters)} glyphs>'
        return f'<Typeface {self.path.name} at {self.height}px>'


class Text:
    """A string a cartridge carries by address.

    ``text('WHO?')`` in a record is the mark that says "this field
    is text, stored in the pool and reached by an offset". In the
    game's own Python the value answers its string when CALLED,
    which is how the twin reads what the compiled dialect reads as
    an address; on the cartridge it costs exactly what a plain
    ``str`` field always has, and the encoder proves the bytes
    identical.
    """

    __slots__ = ('value',)

    def __init__(self, value):
        if not isinstance(value, str):
            raise ValueError(
                f'text() carries a str, got {type(value).__name__}'
            )
        self.value = value

    def __call__(self):
        return self.value

    def __str__(self):
        return self.value

    def __eq__(self, other):
        return isinstance(other, Text) and other.value == self.value

    def __hash__(self):
        return hash(self.value)

    def __repr__(self):
        return f'text({self.value!r})'


#: the spelling content is written in: ``ask=text('WHO?')``
text = Text


class TextStore:
    """The records a cartridge carries as text by address."""

    __eightiesdk_declaration__ = 'text'

    def __init__(self, records, typeface=None):
        if typeface is not None and not isinstance(typeface, Typeface):
            raise ValueError(
                f'a text store takes a Typeface, got '
                f'{type(typeface).__name__}'
            )
        self.typeface = typeface
        records = tuple(records)
        if not records:
            raise ValueError('a text store needs at least one record')
        kinds = {type(record) for record in records}
        if len(kinds) != 1:
            names = ', '.join(sorted(kind.__name__ for kind in kinds))
            raise ValueError(
                f'a text store holds records of one type, got {names}'
            )
        if not is_dataclass(records[0]):
            raise ValueError(
                f'a text store holds dataclass records, got '
                f'{type(records[0]).__name__}'
            )
        self.records = records

    @property
    def texts(self):
        """Every distinct text the store carries, first appearance
        first, each once. THE COLLECTION: what the glyph store is
        later subset to, and what a second store shares a pool
        with."""
        seen = {}
        for record in self.records:
            for field in fields(type(record)):
                if not is_text_annotation(field.type):
                    continue
                value = getattr(record, field.name)
                values = value if isinstance(value, (list, tuple)) else [value]
                for item in values:
                    seen.setdefault(str(item), None)
        return tuple(seen)

    def __repr__(self):
        return (
            f'<TextStore {len(self.records)} '
            f'{type(self.records[0]).__name__}>'
        )


__all__ = ['Text', 'TextStore', 'Typeface', 'text']
