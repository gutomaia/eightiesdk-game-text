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

from dataclasses import is_dataclass


class TextStore:
    """The records a cartridge carries as text by address."""

    __eightiesdk_declaration__ = 'text'

    def __init__(self, records):
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

    def __repr__(self):
        return (
            f'<TextStore {len(self.records)} '
            f'{type(self.records[0]).__name__}>'
        )


__all__ = ['TextStore']
