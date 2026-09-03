"""Compose one text store into extension-neutral build state.

The resolver the runtime discovers under ``eightiesdk.game_extensions``
as ``text``. It receives the declared store, the frozen target facts,
and an opaque build state, and it answers through the build state's
neutral claim port. It imports no platform, no runtime and no product.

WHAT IT KNOWS: the text it stores and what the bytes cost. It encodes
the records once and claims the ROM they take, measured rather than
estimated, under the declaration's own owner. WHAT IT DOES NOT KNOW:
where the text is drawn. No plane, no window, no page.

BYTE ORDER IS NOT DECIDED HERE. Offsets in the pool are two bytes
whichever way round they are written, so the cost is the same on a
6502 and on a 68000; the bytes themselves are laid by the target
strategy that knows its CPU, in a later slice.
"""

from eightiesdk_resources.resource_plan import (
    MEASURED,
    Evidence,
    ResourceClaim,
)

from eightiesdk_game_text.record import encode

#: the resource every extension in this fleet charges cartridge bytes
#: to, so one ledger can add them up
ROM_PAYLOAD = 'cartridge/rom_payload_bytes'

TARGET_FACTS = ('profile', 'cartridge', 'configuration')


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
    retain = getattr(build_state, 'with_resource_claims', None)
    if not callable(retain):
        raise ValueError(
            'text contribution requires a build state with '
            'with_resource_claims'
        )
    table = encode(list(request.records), 'little')
    parts = (
        ('record', len(table.records)),
        ('pool', len(table.pool)),
        ('table', len(table.tables)),
    )
    spent = sum(size for _name, size in parts)
    detail = ', '.join(f'{size} {name} bytes' for name, size in parts)
    claim = ResourceClaim(
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
    return retain((claim,))


__all__ = ['ROM_PAYLOAD', 'contribute_text']
