"""Two stores contributed on the Mega Drive, through a recording
build state: what each claims and what each carries."""

from dataclasses import dataclass, replace
from types import SimpleNamespace
from unittest import TestCase

from eightiesdk_platform_megadrive.configuration import STANDARD

from eightiesdk_game_text.contribution import contribute_text
from eightiesdk_game_text.declarations import TextStore, Typeface
from eightiesdk_game_text.record import encode_many
from eightiesdk_game_text.tests.drawn_store_cost_spec import (
    DrawnStoreCostSpec,
)
from eightiesdk_game_text.tests.font_spec import FontSpec

FACE = Typeface.from_art(
    {
        'A': '\n'.join(FontSpec.NARROW),
        'B': '\n'.join(FontSpec.NARROW),
        'W': '\n'.join(FontSpec.WIDE),
    }
)


@dataclass
class Line:
    ask: str


@dataclass(frozen=True)
class RecordingState:
    configuration: object
    profile: object = None
    cartridge: object = None
    pattern_reservations: tuple = ()
    extension_contributions: tuple = ()
    resource_claims: tuple = ()
    runtime_contributions: tuple = ()
    compiler_inputs: tuple = ()

    def with_resource_claims(self, claims):
        return replace(
            self, resource_claims=self.resource_claims + tuple(claims)
        )

    def with_extension_contribution(self, contribution):
        return replace(
            self,
            extension_contributions=self.extension_contributions
            + (contribution,),
        )

    def with_pattern_reservation(self, reservation):
        return replace(
            self,
            pattern_reservations=self.pattern_reservations + (reservation,),
        )

    def with_compiler_inputs(self, inputs):
        return replace(
            self, compiler_inputs=self.compiler_inputs + tuple(inputs)
        )

    def with_runtime_contributions(self, contributions):
        return replace(
            self,
            runtime_contributions=self.runtime_contributions
            + tuple(contributions),
        )


class DrawnStoreCostOnMegaDriveTest(DrawnStoreCostSpec, TestCase):
    def given_two_stores_on_a_drawing_console(self):
        self.stores = {
            'first': TextStore([Line('AB'), Line('BA')], typeface=FACE),
            'second': TextStore([Line('WA')], typeface=FACE),
        }
        self.target = SimpleNamespace(
            name='megadrive',
            profile=None,
            cartridge=None,
            configuration=STANDARD,
        )
        self.state = RecordingState(configuration=STANDARD)

    def when_both_are_contributed(self):
        for owner, store in self.stores.items():
            self.state = contribute_text(
                store,
                self.target,
                build_state=self.state,
                declaration_owner=owner,
            )

    def _runtime_of(self, owner):
        [runtime] = [
            item
            for item in self.state.runtime_contributions
            if item.owner == f'text:{owner}'
        ]
        return runtime

    def assert_claim_of_equals_its_runtime_bytes(self, owner):
        [claim] = [
            item
            for item in self.state.resource_claims
            if item.owner == f'text:{owner}'
        ]
        placed = sum(
            len(section.content)
            for section in self._runtime_of(owner).rom_sections
        )
        self.assertEqual(placed, claim.spent, owner)

    def assert_runtime_pool_of_holds_its_own_text_only(self, owner):
        [pool] = [
            section
            for section in self._runtime_of(owner).rom_sections
            if section.name == 'pool'
        ]
        alone = encode_many([self.stores[owner].records], 'big')
        self.assertEqual(len(alone.pool), len(pool.content), owner)
