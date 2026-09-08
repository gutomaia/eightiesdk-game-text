"""Compose text stores into extension-neutral build state.

The resolver the runtime discovers under ``eightiesdk.game_extensions``
as ``text``. It receives one declared store at a time, the frozen
target facts, and an opaque build state, and it answers through the
build state's neutral ports. It imports no platform, no runtime and
no product.

WHAT IT KNOWS: the text it stores and what the bytes cost. WHAT IT
DOES NOT KNOW: where the text is drawn. No plane, no window, no page.

ONE POOL PER CARTRIDGE, however many stores declare into it. The
resolver is called once per declaration and cannot see the others
directly, so it reads what earlier calls left behind: the build state
retains every extension contribution by identity, and the last
``TextContribution`` there carries every store so far. This call
encodes them all again with its own store added, claims ONLY THE
BYTES IT ADDS, and leaves a contribution carrying the whole cartridge
for the next store and for whoever renders. The claims of all stores
therefore add up to the cartridge's text exactly once.

BYTE ORDER IS NOT DECIDED HERE. Offsets in the pool are two bytes
whichever way round they are written, so the cost is the same on a
6502 and on a 68000; the bytes themselves are laid by the target
strategy that knows its CPU, in a later slice.
"""

from dataclasses import dataclass

from eightiesdk_resources.resource_plan import (
    MEASURED,
    Evidence,
    ResourceClaim,
)

from eightiesdk_game_text.glyphs import GlyphStore
from eightiesdk_game_text.record import encode_many

#: the resource every extension in this fleet charges cartridge bytes
#: to, so one ledger can add them up
ROM_PAYLOAD = 'rom_payload_bytes'

TARGET_FACTS = ('profile', 'cartridge', 'configuration')


@dataclass(frozen=True)
class TextContribution:
    """Every text store resolved so far, over one encoded cartridge.

    `owners`, `stores` and `glyphs` are parallel, in declaration
    order; `cartridge` is the `CartridgeText` holding them all. A
    store without a typeface has None where its glyphs would be.
    """

    owners: tuple
    stores: tuple
    cartridge: object
    glyphs: tuple = ()
    #: per store, (text bytes, glyph bytes) it added: the split behind
    #: its one claim, as numbers rather than prose
    costs: tuple = ()


def _refuse_target_disagreement(target, build_state):
    disagreements = [
        name
        for name in TARGET_FACTS
        if getattr(target, name, None) is not getattr(build_state, name, None)
    ]
    if disagreements:
        raise ValueError(
            'text target and build_state disagree about '
            + ', '.join(disagreements)
        )


def _port(build_state, name):
    port = getattr(build_state, name, None)
    if not callable(port):
        raise ValueError(
            f'text contribution requires a build state with {name}'
        )
    return port


def _previous(build_state):
    """The last text contribution an earlier store left, or None."""
    retained = [
        item
        for item in getattr(build_state, 'extension_contributions', ())
        if isinstance(item, TextContribution)
    ]
    return retained[-1] if retained else None


def contribute_text(
    request,
    target,
    budget=None,
    entries=None,
    build_state=None,
    declaration_owner=None,
):
    """Resolve one declared text store into a build-state replacement."""
    if build_state is None:
        raise ValueError('text contribution requires build_state')
    if not isinstance(declaration_owner, str) or not declaration_owner:
        raise ValueError('text contribution requires declaration_owner')
    _refuse_target_disagreement(target, build_state)
    _port(build_state, 'with_resource_claims')
    _port(build_state, 'with_extension_contribution')

    previous = _previous(build_state)
    owners = (previous.owners if previous else ()) + (declaration_owner,)
    stores = (previous.stores if previous else ()) + (request,)
    before = previous.cartridge if previous else None
    wide = _wide_rule(request, stores)
    cartridge = encode_many(
        [store.records for store in stores], 'little', wide
    )
    spent = cartridge.size - (before.size if before else 0)
    own = cartridge.stores[-1]
    pool_added = len(cartridge.pool) - (len(before.pool) if before else 0)
    tables_added = len(cartridge.tables) - (
        len(before.tables) if before else 0
    )
    detail = (
        f'{len(own.records)} record bytes, {pool_added} pool bytes, '
        f'{tables_added} table bytes'
    )
    if previous:
        shared = len(set(_texts(previous.stores)) & set(request.texts))
        detail += (
            f'; {shared} string{"" if shared == 1 else "s"} already in the '
            f'pool from {", ".join(previous.owners)}'
        )
    text_spent = spent
    text_detail = (
        f'eightiesdk-game-text encoded {len(request.records)} records: '
        f'{detail}'
    )
    glyph_spent = 0
    glyph_detail = ''
    glyph_stores = list(previous.glyphs) if previous else []
    glyphs = None
    if request.typeface is not None:
        # ONLY THE CHARACTERS THE TEXT USES, and ONE GLYPH STORE PER
        # TYPEFACE: every earlier store that named this same face
        # joins this one, so a digit three language banks share is
        # one glyph and its cells are stored once. The claim is the
        # cells and slots this store adds on top of what those
        # stores already put there. Measured on a real corpus:
        # 7,506 bytes kept apart, 6,178 together.
        earlier = [
            (owner, store)
            for owner, store in zip(
                previous.owners if previous else (),
                previous.stores if previous else (),
            )
            if store.typeface is request.typeface
        ]
        earlier_owners = [owner for owner, _store in earlier]
        before = _glyphs_of(previous, request.typeface)
        used = ''.join(
            text
            for store in [store for _owner, store in earlier] + [request]
            for text in store.texts
        )
        glyphs = GlyphStore(request.typeface.glyphs_for(used), used)
        detail = (
            f'{len(glyphs.characters)} glyphs over {len(glyphs.cells)} '
            f'distinct cells at 1bpp, from {request.typeface!r}'
        )
        if before:
            detail += (
                f'; {len(before.cells)} cells already there from '
                f'{", ".join(earlier_owners)}'
            )
        glyph_spent = glyphs.size - (before.size if before else 0)
        glyph_detail = f'; glyph store: {detail}, {glyph_spent} bytes added'
        # the earlier stores of this face now read from the shared
        # store too, so the tuple stays parallel and truthful
        glyph_stores = [
            glyphs if store.typeface is request.typeface else kept
            for store, kept in zip(
                previous.stores if previous else (), glyph_stores
            )
        ]
    glyph_stores = tuple(glyph_stores) + (glyphs,)
    # A STORE DRAWN AT RUN TIME CLAIMS WHAT ITS RUNTIME PLACES. On a
    # console with a text runtime the store is encoded ALONE, its own
    # cells reserved, and the ledger reads the bytes the linker will
    # lay down: pool and records as text, slot table, cells and the
    # expansion table as glyphs, the two routines named beside them.
    # The shared encoding above still measures what the languages
    # have in common, for the consoles that stream a shared pool.
    drawn = None
    if glyphs is not None:
        build_state, drawn = _drawn_at_runtime(
            build_state, target, declaration_owner, request
        )
    if drawn is not None:
        placed = {
            section.name: len(section.content)
            for section in drawn.rom_sections
        }
        text_spent = placed['pool'] + placed['records']
        glyph_spent = placed['slots'] + placed['cells'] + placed['expand']
        code_spent = placed['expand_code'] + placed['draw']
        text_detail = (
            f'eightiesdk-game-text draws {len(request.records)} records '
            f'on {target.name} at run time: {placed["pool"]} pool bytes, '
            f'{placed["records"]} record bytes'
        )
        glyph_detail = (
            f'; glyphs: {placed["cells"]} cell bytes at 1bpp, '
            f'{placed["slots"]} slot bytes, {placed["expand"]} expansion '
            f'bytes; routines: {code_spent} bytes'
        )
        glyph_spent += code_spent
    # ONE CLAIM PER OWNER PER RESOURCE. The ledger refuses a second
    # claim from the same owner with different evidence, so the text
    # and the glyphs travel together and the split is carried as
    # numbers on the contribution.
    claim = ResourceClaim(
        owner=f'text:{declaration_owner}',
        lifecycle='cartridge',
        resource=ROM_PAYLOAD,
        spent=text_spent + glyph_spent,
        evidence=Evidence(MEASURED, text_detail + glyph_detail),
    )
    costs = (previous.costs if previous else ()) + ((text_spent, glyph_spent),)
    claimed = _port(build_state, 'with_resource_claims')((claim,))
    retain_contribution = _port(claimed, 'with_extension_contribution')
    return retain_contribution(
        TextContribution(owners, stores, cartridge, glyph_stores, costs)
    )


def _wide_rule(request, stores):
    """Wide by the face's own measure over every store's text, so
    the alphabet puts narrow codes first and `wide_from` is one
    number; None when no face is declared."""
    if request.typeface is None:
        return None
    used = ''.join(text for store in stores for text in store.texts)
    font = request.typeface.glyphs_for(used)
    return lambda character: font.glyph(character).columns > 1


#: the consoles this extension draws on at run time, by target name;
#: the module is imported only when its console is the target
RUNTIMES = {'megadrive': 'eightiesdk_game_text.megadrive.runtime'}


def _drawn_at_runtime(build_state, target, owner, request):
    """On a console with a runtime here, the store is drawn at run
    time: encoded ALONE in that console's byte order, its own glyph
    cells reserved in the pattern table, the game given its request
    bytes, and the linker a contribution of code and data. Answers
    (build state, contribution), or (build state, None) on any other
    console, where the store is claim-only as before."""
    module_name = RUNTIMES.get(getattr(target, 'name', None))
    if module_name is None:
        return build_state, None
    from importlib import import_module

    runtime = import_module(module_name)
    configuration = getattr(build_state, 'configuration', None)
    if configuration is None:
        return build_state, None
    used = ''.join(request.texts)
    font = request.typeface.glyphs_for(used)
    cartridge = encode_many(
        [request.records],
        runtime.ENDIAN,
        lambda character: font.glyph(character).columns > 1,
    )
    glyphs = GlyphStore(font, used)
    reservation = configuration.allocate_pattern_reservation(
        owner=f'text:{owner}',
        count=len(glyphs.cells),
        reservations=getattr(build_state, 'pattern_reservations', ()),
    )
    contribution = runtime.text_runtime(
        owner,
        cartridge,
        cartridge.stores[0],
        type(request.records[0]),
        glyphs,
        configuration,
        reservation,
    )
    return (
        _port(build_state, 'with_pattern_reservation')(reservation)
        .with_compiler_inputs((runtime.request_state(owner),))
        .with_runtime_contributions((contribution,)),
        contribution,
    )


def _texts(stores):
    for store in stores:
        yield from store.texts


def _glyphs_of(previous, typeface):
    """The glyph store earlier stores of this typeface built, if any."""
    if previous is None:
        return None
    for store, glyphs in zip(
        reversed(previous.stores), reversed(previous.glyphs)
    ):
        if store.typeface is typeface:
            return glyphs
    return None


__all__ = ['ROM_PAYLOAD', 'TextContribution', 'contribute_text']
