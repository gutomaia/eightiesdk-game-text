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
ROM_PAYLOAD = 'cartridge/rom_payload_bytes'

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
    retain_claims = _port(build_state, 'with_resource_claims')
    _port(build_state, 'with_extension_contribution')

    previous = _previous(build_state)
    owners = (previous.owners if previous else ()) + (declaration_owner,)
    stores = (previous.stores if previous else ()) + (request,)
    before = previous.cartridge if previous else None
    cartridge = encode_many([store.records for store in stores], 'little')
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
    claims = [
        ResourceClaim(
            owner=f'text:{declaration_owner}',
            lifecycle='cartridge',
            resource=ROM_PAYLOAD,
            spent=spent,
            evidence=Evidence(
                MEASURED,
                f'eightiesdk-game-text encoded {len(request.records)} '
                f'records: {detail}',
            ),
        )
    ]
    glyphs = None
    if request.typeface is not None:
        # ONLY THE CHARACTERS THIS STORE'S TEXT USES. The typeface
        # may draw a thousand; the store keeps what its records
        # contain, and a character it cannot draw refuses by name.
        used = ''.join(request.texts)
        glyphs = GlyphStore(request.typeface.glyphs_for(used), used)
        claims.append(
            ResourceClaim(
                owner=f'text:{declaration_owner}',
                lifecycle='cartridge',
                resource=ROM_PAYLOAD,
                spent=glyphs.size,
                evidence=Evidence(
                    MEASURED,
                    f'eightiesdk-game-text glyph store: '
                    f'{len(glyphs.characters)} glyphs over '
                    f'{len(glyphs.cells)} distinct cells at 1bpp, '
                    f'from {request.typeface!r}',
                ),
            )
        )
    glyph_stores = (previous.glyphs if previous else ()) + (glyphs,)
    claimed = retain_claims(tuple(claims))
    retain_contribution = _port(claimed, 'with_extension_contribution')
    return retain_contribution(
        TextContribution(owners, stores, cartridge, glyph_stores)
    )


def _texts(stores):
    for store in stores:
        yield from store.texts


__all__ = ['ROM_PAYLOAD', 'TextContribution', 'contribute_text']
