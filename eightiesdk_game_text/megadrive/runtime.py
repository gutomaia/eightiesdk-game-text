"""Text drawn on the Mega Drive at run time: a contributed 68000
routine over the store's own bytes.

WHAT THE CONSOLE GETS. The pool, the store's record array and a
slot table (four name-table words per code: top-left, top-right,
bottom-left, bottom-right; a narrow code fills two of them) as ROM
data; the 1bpp cells and a 256-entry expansion table; a reset hook
that expands every cell into the console's 4bpp pattern table once,
into a reservation of this owner's; and a V-int hook that, when the
game's request byte changes, walks the requested record's first text
field and writes its cells' names to plane A, top row then bottom
row, from the game's row and column bytes. Width is the code against
`wide_from`, one compare, no table.

WHY 1BPP IN ROM AND 4BPP IN VRAM. The owner's rule: the glyphs are
stored once at one bit per pixel and rendered right for each
console. This console has the pattern room to keep every cell
resident (2,044 names), so the expansion happens once, at reset,
with the display off, and a page turn writes name-table words only.
"""

from dataclasses import dataclass

from eightiesdk_cpu.assembler import ProgramAssembler
from eightiesdk_cpu.backend import (
    Immediate,
    InstructionOrigin,
    LabelReference,
    MemoryAddress,
    RegisterIndirect,
    RegisterOperand,
    SyntheticInstructionSource,
)
from eightiesdk_cpu_m68000.instructions import (
    ADD_ADDRESS_WORD,
    ADD_IMMEDIATE_WORD,
    ADD_QUICK_WORD,
    ADD_WORD,
    AND_IMMEDIATE_WORD,
    BRA_SHORT,
    BRA_WORD,
    COMPARE_IMMEDIATE_BYTE,
    COMPARE_IMMEDIATE_WORD,
    COMPARE_WORD,
    CONDITION_BRANCH_SHORT,
    DBRA,
    LEA,
    LSL_WORD,
    M68000Encoder,
    M68000IndexedAddress,
    MOVE_ADDRESS_LONG,
    MOVE_BYTE,
    MOVE_LONG,
    MOVE_QUICK,
    MOVE_WORD,
    MULTIPLY_UNSIGNED_WORD,
    OR_IMMEDIATE_WORD,
    OR_WORD,
    RTS,
    SWAP,
)
from eightiesdk_platform.runtime_contribution import (
    RuntimeContribution,
    RuntimeExport,
    RuntimeHook,
    RuntimeImport,
    RuntimeRamSection,
    RuntimeRomSection,
)

from eightiesdk_game_text.glyphs import CELL_BYTES
from eightiesdk_game_text.record import (
    DIRECT,
    ESCAPE,
    LINE_BREAK,
    TERMINATOR,
    _layout_of,
    _text_fields,
)

TARGET_ABI = 'm68k-md'
#: the 68000 reads a record's offsets big-endian, and at even
#: addresses: an odd word read is an address error
ENDIAN = 'big'
ALIGN = 2
#: the request byte that asks for nothing
NOTHING = 0xFF
#: VDP register 15: auto-increment by one word after a data write
AUTO_INCREMENT_WORD = 0x8F02
#: a plane row on the crust's 64-cell-wide plane, in bytes
PLANE_ROW_BYTES = 64 * 2
#: a plane A command's address field is 14 bits; a row's advance
#: stays inside it for every row plane A has
ROW_ADVANCE_IN_COMMAND = PLANE_ROW_BYTES << 16
#: the slot table: one word per cell position, four per code
SLOT_WORDS = 4
#: an expansion entry: one 1bpp row byte to four 4bpp bytes
EXPANDED_ROW_BYTES = 4


@dataclass(frozen=True)
class RequestStateEntry:
    name: str
    width: int
    value: int


@dataclass(frozen=True)
class RequestState:
    """The three bytes the game writes to ask for a draw, created by
    this extension and published as its own so the linker can hand
    their addresses to the routine. Duck-typed to the runtime's
    initial-state compiler input, which this package must not
    import."""

    owner: str
    entries: tuple

    __eightiesdk_compiler_input__ = 'initial_state_values'


def request_names(owner):
    return {
        'request': f'{owner}_request',
        'row': f'{owner}_row',
        'column': f'{owner}_column',
    }


def request_state(owner):
    names = request_names(owner)
    return RequestState(
        owner,
        (
            RequestStateEntry(names['request'], 1, NOTHING),
            RequestStateEntry(names['row'], 1, 0),
            RequestStateEntry(names['column'], 1, 0),
        ),
    )


def expansion_table():
    """Row byte -> four bytes of nibbles, colour 1 where a bit is set,
    the left pixel in the high nibble: the console's packed 4bpp."""
    table = bytearray()
    for row in range(256):
        for pair in range(4):
            left = (row >> (7 - pair * 2)) & 1
            right = (row >> (6 - pair * 2)) & 1
            table.append((left << 4) | right)
    return bytes(table)


def cell_bytes(glyphs):
    """Every distinct cell's eight row bytes, in slot order."""
    cells = glyphs.cells
    return b''.join(bytes(cells[slot]) for slot in range(len(cells)))


def slot_table(alphabet, glyphs, first_tile_name, palette_line):
    """Four name-table words per code. A wide glyph's cells read
    top-left, top-right, bottom-left, bottom-right; a narrow one's
    top and bottom take the left positions and the right ones stay
    blank, never written."""
    words = bytearray()
    for character in alphabet:
        slots = list(glyphs.slots_of(character))
        if len(slots) == 2:
            positions = [slots[0], 0, slots[1], 0]
        elif len(slots) == 4:
            positions = slots
        else:
            raise ValueError(
                f'{character!r} draws with {len(slots)} cells; this '
                'console draws one or two columns of two rows'
            )
        for slot in positions:
            name = (first_tile_name + slot) | (palette_line << 13)
            words += name.to_bytes(2, ENDIAN)
    return bytes(words)


def _origin(owner, section, role):
    block = f'text:{owner}:{section}'
    return InstructionOrigin(
        block,
        f'{block}:{role}',
        'TextRuntime',
        SyntheticInstructionSource(
            f'text:{owner}', 'eightiesdk_game_text.megadrive.runtime', role
        ),
        (f'text:{owner}', 'runtime', section),
        0,
    )


def _register(name):
    return RegisterOperand(name)


# THE ENCODER'S PALETTE. The typed 68000 encoder accepts the operand
# forms the fleet has needed and refuses the rest by name: A0 is the
# one address register a label loads into, a byte loads into D0 or
# D1, D1 never moves into D0, a data register stores to a label as a
# word, and a register is pushed and popped only as D0, D1 or A0.
# Both routines below are written inside that palette, the stack
# standing in for the registers it withholds, so nothing here asks
# the CPU package for a form.

D0, D1, D2 = (RegisterOperand(f'D{n}') for n in range(3))
A0 = RegisterOperand('A0')
PUSH = RegisterIndirect('A7', predecrement=True)
POP = RegisterIndirect('A7', postincrement=True)


def expand_routine(owner, configuration, first_tile_name, cell_count):
    """Reset hook: every 1bpp cell into the pattern table, expanded.

    Row byte by row byte: the byte indexes the expansion table, whose
    four bytes are the row at 4bpp, written as two words."""
    asm = ProgramAssembler(0, encoder=M68000Encoder())
    for symbol in ('cells', 'expand'):
        asm.declare_external(symbol, target_kind='data')
    control = MemoryAddress(configuration.control_port, width=4)
    data = MemoryAddress(configuration.data_port, width=4)

    def emit(instruction, role):
        asm.emit(instruction(_origin(owner, 'expand', role)))

    emit(lambda o: MOVE_LONG(A0, PUSH, o), 'save-a0')
    emit(
        lambda o: MOVE_WORD(
            Immediate(AUTO_INCREMENT_WORD, width=2), control, o
        ),
        'auto-increment',
    )
    command = configuration.vram_write_command(
        first_tile_name * configuration.tile_bytes
    )
    emit(
        lambda o: MOVE_LONG(Immediate(command, width=4), control, o),
        'aim-at-reservation',
    )
    emit(lambda o: MOVE_QUICK(Immediate(0, width=1), D0, o), 'first-row')
    emit(
        lambda o: MOVE_WORD(
            Immediate(cell_count * CELL_BYTES - 1, width=2), D2, o
        ),
        'row-count',
    )
    asm.mark('row')
    emit(lambda o: MOVE_LONG(D0, PUSH, o), 'keep-index')
    emit(lambda o: LEA(LabelReference('cells'), A0, o), 'cells')
    emit(
        lambda o: MOVE_BYTE(
            M68000IndexedAddress('A0', 'D0', 'long', 0), D0, o
        ),
        'row-byte',
    )
    emit(lambda o: AND_IMMEDIATE_WORD(Immediate(0xFF, width=2), D0, o), 'byte')
    emit(lambda o: LSL_WORD(Immediate(2, width=1), D0, o), 'times-four')
    emit(lambda o: LEA(LabelReference('expand'), A0, o), 'table')
    emit(
        lambda o: MOVE_WORD(
            M68000IndexedAddress('A0', 'D0', 'long', 0), D1, o
        ),
        'left-half',
    )
    emit(lambda o: MOVE_WORD(D1, data, o), 'write-left')
    emit(lambda o: ADD_IMMEDIATE_WORD(Immediate(2, width=2), D0, o), 'right')
    emit(
        lambda o: MOVE_WORD(
            M68000IndexedAddress('A0', 'D0', 'long', 0), D1, o
        ),
        'right-half',
    )
    emit(lambda o: MOVE_WORD(D1, data, o), 'write-right')
    emit(lambda o: MOVE_LONG(POP, D0, o), 'index')
    emit(lambda o: ADD_QUICK_WORD(Immediate(1, width=1), D0, o), 'next-index')
    emit(lambda o: DBRA(D2, LabelReference('row'), o), 'next-row')
    emit(lambda o: MOVE_ADDRESS_LONG(POP, A0, o), 'restore-a0')
    emit(lambda o: RTS(o), 'return')
    return asm.finish_linkable()


def _emit_pass(emit, mark, data, row_name, displacement, wide_from):
    """One plane row of the text A0 points at: the top cells or the
    bottom cells of every character, left then right when wide."""
    mark(f'{row_name}-next')
    emit(
        lambda o: MOVE_QUICK(Immediate(0, width=1), D2, o), f'{row_name}-clear'
    )
    emit(
        lambda o: MOVE_BYTE(RegisterIndirect('A0', postincrement=True), D2, o),
        f'{row_name}-code',
    )
    emit(lambda o: MOVE_LONG(D2, D0, o), f'{row_name}-code-copy')
    emit(
        lambda o: COMPARE_IMMEDIATE_BYTE(
            Immediate(TERMINATOR, width=1), D0, o
        ),
        f'{row_name}-end?',
    )
    emit(
        lambda o: CONDITION_BRANCH_SHORT(
            'eq', LabelReference(f'{row_name}-done'), o
        ),
        f'{row_name}-end',
    )
    emit(
        lambda o: COMPARE_IMMEDIATE_BYTE(
            Immediate(LINE_BREAK, width=1), D0, o
        ),
        f'{row_name}-break?',
    )
    emit(
        lambda o: CONDITION_BRANCH_SHORT(
            'eq', LabelReference(f'{row_name}-done'), o
        ),
        f'{row_name}-break',
    )
    # THE ESCAPE: a code past the direct range is written as the
    # escape byte and a second byte, and reads back as the escape
    # plus that byte, the way record.py wrote it
    emit(
        lambda o: COMPARE_IMMEDIATE_BYTE(Immediate(ESCAPE, width=1), D0, o),
        f'{row_name}-escape?',
    )
    emit(
        lambda o: CONDITION_BRANCH_SHORT(
            'ne', LabelReference(f'{row_name}-direct'), o
        ),
        f'{row_name}-direct?',
    )
    emit(
        lambda o: MOVE_QUICK(Immediate(0, width=1), D2, o),
        f'{row_name}-clear-2',
    )
    emit(
        lambda o: MOVE_BYTE(RegisterIndirect('A0', postincrement=True), D2, o),
        f'{row_name}-second-byte',
    )
    emit(lambda o: MOVE_LONG(D2, D0, o), f'{row_name}-second-copy')
    emit(
        lambda o: ADD_IMMEDIATE_WORD(Immediate(DIRECT, width=2), D0, o),
        f'{row_name}-escaped-code',
    )
    mark(f'{row_name}-direct')
    emit(lambda o: MOVE_LONG(A0, PUSH, o), f'{row_name}-keep-text')
    emit(lambda o: LEA(LabelReference('slots'), A0, o), f'{row_name}-slots')
    emit(lambda o: LSL_WORD(Immediate(2, width=1), D0, o), f'{row_name}-x4')
    emit(lambda o: ADD_WORD(D0, D0, o), f'{row_name}-x8')
    if displacement:
        emit(
            lambda o: ADD_IMMEDIATE_WORD(
                Immediate(displacement, width=2), D0, o
            ),
            f'{row_name}-row-entry',
        )
    emit(
        lambda o: MOVE_WORD(
            M68000IndexedAddress('A0', 'D0', 'long', 0), D1, o
        ),
        f'{row_name}-left',
    )
    emit(lambda o: MOVE_WORD(D1, data, o), f'{row_name}-write-left')
    # width is the code against the boundary, read off the scaled
    # entry index: one compare, no table
    emit(
        lambda o: COMPARE_IMMEDIATE_WORD(
            Immediate(wide_from * SLOT_WORDS * 2 + displacement, width=2),
            D0,
            o,
        ),
        f'{row_name}-wide?',
    )
    emit(
        lambda o: CONDITION_BRANCH_SHORT(
            'cs', LabelReference(f'{row_name}-narrow'), o
        ),
        f'{row_name}-narrow?',
    )
    emit(
        lambda o: ADD_IMMEDIATE_WORD(Immediate(2, width=2), D0, o),
        f'{row_name}-right-entry',
    )
    emit(
        lambda o: MOVE_WORD(
            M68000IndexedAddress('A0', 'D0', 'long', 0), D1, o
        ),
        f'{row_name}-right',
    )
    emit(lambda o: MOVE_WORD(D1, data, o), f'{row_name}-write-right')
    mark(f'{row_name}-narrow')
    emit(lambda o: MOVE_ADDRESS_LONG(POP, A0, o), f'{row_name}-text')
    emit(
        lambda o: BRA_SHORT(LabelReference(f'{row_name}-next'), o),
        f'{row_name}-loop',
    )
    mark(f'{row_name}-done')


def draw_routine(
    owner, configuration, names, record_size, text_offset, wide_from
):
    """V-int hook: the requested record's first text, two plane rows
    per line, the next line two rows down at the same column."""
    if text_offset:
        raise ValueError(
            'this console draws a record whose first field is the text; '
            f'the text sits {text_offset} bytes in'
        )
    asm = ProgramAssembler(0, encoder=M68000Encoder())
    for symbol in (
        'request',
        'row',
        'column',
        'shadow',
        'scratch',
        'line_row',
    ):
        asm.declare_external(symbol, target_kind='data')
    for symbol in ('pool', 'records', 'slots'):
        asm.declare_external(symbol, target_kind='data')
    control = MemoryAddress(configuration.control_port, width=4)
    data = MemoryAddress(configuration.data_port, width=4)

    def emit(instruction, role):
        asm.emit(instruction(_origin(owner, 'draw', role)))

    emit(lambda o: MOVE_QUICK(Immediate(0, width=1), D0, o), 'clear')
    emit(lambda o: MOVE_BYTE(LabelReference('request'), D0, o), 'request')
    emit(lambda o: MOVE_WORD(LabelReference('shadow'), D1, o), 'shadow')
    emit(lambda o: COMPARE_WORD(D0, D1, o), 'changed?')
    # a held request returns at once: the common frame costs these
    # five instructions; the body is too long for a short branch to
    # clear, so the return sits here and the body is branched into
    emit(
        lambda o: CONDITION_BRANCH_SHORT('ne', LabelReference('changed'), o),
        'held?',
    )
    emit(lambda o: RTS(o), 'held')
    asm.mark('changed')
    emit(lambda o: MOVE_WORD(D0, LabelReference('shadow'), o), 'remember')
    emit(
        lambda o: COMPARE_IMMEDIATE_BYTE(Immediate(NOTHING, width=1), D0, o),
        'nothing?',
    )
    emit(
        lambda o: CONDITION_BRANCH_SHORT('ne', LabelReference('draw'), o),
        'draw?',
    )
    emit(lambda o: RTS(o), 'nothing')
    asm.mark('draw')
    emit(lambda o: MOVE_LONG(A0, PUSH, o), 'save-a0')
    # the text: pool + the record's first offset word
    emit(
        lambda o: MULTIPLY_UNSIGNED_WORD(
            Immediate(record_size, width=2), D0, o
        ),
        'record-offset',
    )
    emit(lambda o: LEA(LabelReference('records'), A0, o), 'records')
    emit(
        lambda o: MOVE_WORD(
            M68000IndexedAddress('A0', 'D0', 'long', 0), D1, o
        ),
        'text-offset',
    )
    emit(lambda o: MOVE_WORD(D1, LabelReference('scratch'), o), 'offset-out')
    emit(lambda o: MOVE_WORD(LabelReference('scratch'), D0, o), 'offset-in')
    emit(lambda o: LEA(LabelReference('pool'), A0, o), 'pool')
    emit(lambda o: ADD_ADDRESS_WORD(D0, A0, o), 'text')
    # the first line's row, kept as a word the line loop advances
    emit(lambda o: MOVE_QUICK(Immediate(0, width=1), D0, o), 'clear-row')
    emit(lambda o: MOVE_BYTE(LabelReference('row'), D0, o), 'row')
    emit(lambda o: MOVE_WORD(D0, LabelReference('line_row'), o), 'first-line')
    asm.mark('line')
    # this line's command: plane A + (row * 64 + column) * 2, then the
    # address field and the write bit into the high word
    emit(lambda o: MOVE_WORD(LabelReference('line_row'), D0, o), 'line-row')
    emit(lambda o: LSL_WORD(Immediate(7, width=1), D0, o), 'row-bytes')
    emit(lambda o: MOVE_QUICK(Immediate(0, width=1), D1, o), 'clear-column')
    emit(lambda o: MOVE_BYTE(LabelReference('column'), D1, o), 'column')
    emit(lambda o: ADD_WORD(D1, D1, o), 'column-bytes')
    emit(lambda o: OR_WORD(D1, D0, o), 'cell-bytes')
    emit(
        lambda o: ADD_IMMEDIATE_WORD(
            Immediate(configuration.plane_a_base, width=2), D0, o
        ),
        'plane-a',
    )
    emit(
        lambda o: AND_IMMEDIATE_WORD(Immediate(0x3FFF, width=2), D0, o),
        'low-bits',
    )
    emit(
        lambda o: OR_IMMEDIATE_WORD(Immediate(0x4000, width=2), D0, o),
        'write-bit',
    )
    emit(lambda o: SWAP(D0, o), 'to-high-word')
    emit(
        lambda o: OR_IMMEDIATE_WORD(
            Immediate(configuration.plane_a_base >> 14, width=2), D0, o
        ),
        'high-bits',
    )
    emit(lambda o: MOVE_LONG(D0, PUSH, o), 'keep-command')
    emit(lambda o: MOVE_LONG(D0, control, o), 'aim-top')
    emit(lambda o: MOVE_LONG(A0, PUSH, o), 'keep-line-start')
    _emit_pass(emit, asm.mark, data, 'top', 0, wide_from)
    emit(lambda o: MOVE_ADDRESS_LONG(POP, A0, o), 'line-start-again')
    emit(lambda o: MOVE_LONG(POP, D0, o), 'command-again')
    emit(lambda o: SWAP(D0, o), 'address-field')
    emit(
        lambda o: ADD_IMMEDIATE_WORD(
            Immediate(PLANE_ROW_BYTES, width=2), D0, o
        ),
        'next-row',
    )
    emit(lambda o: SWAP(D0, o), 'command-field')
    emit(lambda o: MOVE_LONG(D0, control, o), 'aim-bottom')
    _emit_pass(emit, asm.mark, data, 'bottom', SLOT_WORDS, wide_from)
    # the code that ended the bottom pass is still in D0: the
    # terminator finishes, a line break moves two rows down
    emit(
        lambda o: COMPARE_IMMEDIATE_BYTE(
            Immediate(TERMINATOR, width=1), D0, o
        ),
        'last-line?',
    )
    emit(
        lambda o: CONDITION_BRANCH_SHORT('eq', LabelReference('finish'), o),
        'last-line',
    )
    emit(
        lambda o: MOVE_WORD(LabelReference('line_row'), D0, o),
        'line-row-again',
    )
    emit(
        lambda o: ADD_IMMEDIATE_WORD(Immediate(2, width=2), D0, o),
        'two-rows-down',
    )
    emit(lambda o: MOVE_WORD(D0, LabelReference('line_row'), o), 'next-line')
    # the word branch takes a displacement, relative to the word after
    # its opcode; the line loop is past a short branch's reach
    back = asm.labels['line'] - (len(asm.code) + 2)
    emit(lambda o: BRA_WORD(back, o), 'draw-next-line')
    asm.mark('finish')
    emit(lambda o: MOVE_ADDRESS_LONG(POP, A0, o), 'restore-a0')
    emit(lambda o: RTS(o), 'return')
    return asm.finish_linkable()


def text_runtime(
    owner,
    cartridge,
    table,
    record_type,
    glyphs,
    configuration,
    reservation,
    palette_line=0,
):
    """The contribution for one store on this console: `cartridge`
    encoded in this console's byte order, `table` the store's own
    record table in it, `record_type` the dataclass it holds."""
    if len(cartridge.pool) >= 0x8000:
        raise ValueError(
            f'the pool is {len(cartridge.pool)} bytes; this console adds '
            'an offset as a signed word and reaches 32,767'
        )
    layout, _unpadded = _layout_of(record_type)
    record_size = table.record_size
    text_field = next(iter(_text_fields(record_type)))[0]
    names = request_names(owner)
    cells = cell_bytes(glyphs)
    expand = expand_routine(
        owner, configuration, reservation.first_tile_name, len(glyphs.cells)
    )
    draw = draw_routine(
        owner,
        configuration,
        names,
        record_size,
        layout[text_field],
        cartridge.wide_from,
    )

    def code_section(name, linked):
        return RuntimeRomSection(
            name,
            linked.code,
            'runtime_rom',
            target_kind='code',
            alignment=2,
            relocations=linked.relocations,
            instruction_spans=linked.instruction_spans,
        )

    def data_section(name, content):
        return RuntimeRomSection(
            name, content, 'runtime_rom', target_kind='data', alignment=2
        )

    return RuntimeContribution(
        owner=f'text:{owner}',
        target_abi=TARGET_ABI,
        rom_sections=(
            code_section('expand_code', expand),
            code_section('draw', draw),
            data_section('pool', cartridge.pool),
            data_section('records', table.records),
            data_section(
                'slots',
                slot_table(
                    cartridge.alphabet,
                    glyphs,
                    reservation.first_tile_name,
                    palette_line,
                ),
            ),
            data_section('cells', cells),
            data_section('expand', expansion_table()),
        ),
        ram_sections=(
            RuntimeRamSection(
                'shadow', 'work_ram', 2, bytes([0, NOTHING]), alignment=2
            ),
            RuntimeRamSection('scratch', 'work_ram', 2, bytes(2), alignment=2),
            RuntimeRamSection(
                'line_row', 'work_ram', 2, bytes(2), alignment=2
            ),
        ),
        imports=tuple(
            RuntimeImport(symbol, owner, name, 1, 'read')
            for symbol, name in names.items()
        ),
        exports=(
            RuntimeExport('text_expand', 'expand_code'),
            RuntimeExport('text_draw', 'draw'),
        ),
        hooks=(
            RuntimeHook('reset', 'text_expand'),
            RuntimeHook('vblank', 'text_draw'),
        ),
        claims=(),
    )


__all__ = [
    'ENDIAN',
    'NOTHING',
    'TARGET_ABI',
    'RequestState',
    'draw_routine',
    'expand_routine',
    'expansion_table',
    'request_names',
    'request_state',
    'slot_table',
    'text_runtime',
]
